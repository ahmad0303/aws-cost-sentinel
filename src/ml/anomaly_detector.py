"""
Cost Anomaly Detection using Modified Z-Score (MAD-based).

Drop-in replacement for the sklearn/numpy/pandas version.
Uses only Python stdlib — saves ~180MB from the Lambda package.

The approach is statistically robust:
  - Median + MAD is resistant to outliers (unlike mean + std)
  - Day-of-week seasonality is handled via per-weekday baselines
  - No training step needed — works from day 1 with enough history
"""

from __future__ import annotations

import math
import statistics
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from ..utils.logger import get_logger
from ..utils.config import get_config


logger = get_logger(__name__)


class CostAnomalyDetector:
    """Detect cost anomalies using statistical methods.

    Same interface as the sklearn version — all public methods
    have identical signatures and return formats.
    """

    SENSITIVITY_PARAMS = {
        "low": {"z_threshold": 3.0, "deviation_floor": 30},
        "medium": {"z_threshold": 2.0, "deviation_floor": 20},
        "high": {"z_threshold": 1.5, "deviation_floor": 10},
    }

    def __init__(self, config=None):
        """Initialize anomaly detector.

        Args:
            config: Configuration object
        """
        self.config = config or get_config()
        self.is_fitted = False

        self.sensitivity = self.config.get("anomaly_detection.sensitivity", "medium")
        self.min_history_days = self.config.get("anomaly_detection.min_history_days", 7)

        self.params = self.SENSITIVITY_PARAMS.get(
            self.sensitivity,
            self.SENSITIVITY_PARAMS["medium"],
        )

        # Internal state (populated by fit)
        self._median: float = 0.0
        self._mad_std: float = 1.0
        self._weekday_medians: dict[int, float] = {}
        self._history: list[dict] = []

        logger.info(
            f"Initialized anomaly detector with sensitivity: {self.sensitivity}"
        )

    # ──────────────────────────────────────────────
    # Core math helpers (pure Python)
    # ──────────────────────────────────────────────

    @staticmethod
    def _median(values: list[float]) -> float:
        return statistics.median(values) if values else 0.0

    @staticmethod
    def _mad(values: list[float], median: float) -> float:
        """Median Absolute Deviation."""
        if not values:
            return 0.0
        deviations = [abs(v - median) for v in values]
        return statistics.median(deviations)

    @staticmethod
    def _mad_to_std(mad: float) -> float:
        """Convert MAD to std-deviation equivalent (for normal distribution)."""
        return mad * 1.4826

    @staticmethod
    def _rolling_mean(values: list[float], window: int) -> list[float]:
        """Simple rolling mean."""
        result = []
        for i in range(len(values)):
            start = max(0, i - window + 1)
            chunk = values[start : i + 1]
            result.append(sum(chunk) / len(chunk))
        return result

    @staticmethod
    def _rolling_std(values: list[float], window: int) -> list[float]:
        """Simple rolling standard deviation."""
        result = []
        for i in range(len(values)):
            start = max(0, i - window + 1)
            chunk = values[start : i + 1]
            if len(chunk) < 2:
                result.append(0.0)
            else:
                avg = sum(chunk) / len(chunk)
                var = sum((x - avg) ** 2 for x in chunk) / len(chunk)
                result.append(math.sqrt(var))
        return result

    # ──────────────────────────────────────────────
    # Public API (matches original signatures)
    # ──────────────────────────────────────────────

    def fit(self, df: list[dict] | Any) -> None:
        """Train on historical cost data.

        Args:
            df: List of dicts with 'date' and 'cost' keys,
                OR a pandas DataFrame (for backward compat).
        """
        records = self._to_records(df)

        if len(records) < self.min_history_days:
            logger.warning(
                f"Insufficient historical data: {len(records)} days "
                f"(minimum: {self.min_history_days})"
            )
            return

        costs = [r["cost"] for r in records]

        # Global baseline
        self._median = self._median_val(costs)
        mad = self._mad(costs, self._median)
        self._mad_std = self._mad_to_std(mad)
        if self._mad_std < 0.01:
            self._mad_std = self._median * 0.1 if self._median > 0 else 1.0

        # Per-weekday baselines (captures weekly seasonality)
        from collections import defaultdict

        weekday_costs: dict[int, list[float]] = defaultdict(list)
        for r in records:
            dt = self._parse_date(r["date"])
            weekday_costs[dt.weekday()].append(r["cost"])

        self._weekday_medians = {
            wd: self._median_val(vals) for wd, vals in weekday_costs.items()
        }

        self._history = records
        self.is_fitted = True

        logger.info(f"Trained anomaly detection model on {len(records)} data points")

    def detect_anomalies(self, df: list[dict] | Any) -> list[dict]:
        """Detect anomalies in cost data.

        Args:
            df: List of dicts with 'date' and 'cost' keys,
                OR a pandas DataFrame.

        Returns:
            List of dicts, each with original fields plus
            'anomaly' (bool) and 'anomaly_score' (float).
        """
        records = self._to_records(df)

        if not self.is_fitted:
            logger.warning("Model not fitted. Training on provided data...")
            self.fit(records)

        if not self.is_fitted:
            logger.error("Could not train model. Insufficient data.")
            for r in records:
                r["anomaly"] = False
                r["anomaly_score"] = 0.0
            return records

        costs = [r["cost"] for r in records]
        rolling_means = self._rolling_mean(costs, 7)
        rolling_stds = self._rolling_std(costs, 7)

        results = []
        for i, r in enumerate(records):
            cost = r["cost"]
            dt = self._parse_date(r["date"])

            # Z-score against global baseline
            global_z = (cost - self._median) / self._mad_std

            # Z-score against weekday baseline (if available)
            wd_median = self._weekday_medians.get(dt.weekday(), self._median)
            wd_z = (cost - wd_median) / self._mad_std if self._mad_std > 0 else 0

            # Z-score against rolling window
            roll_std = rolling_stds[i] if rolling_stds[i] > 0.01 else self._mad_std
            rolling_z = (cost - rolling_means[i]) / roll_std

            # Combined score: weighted average of all three signals
            combined_score = (
                abs(global_z) * 0.4 + abs(wd_z) * 0.3 + abs(rolling_z) * 0.3
            )

            # Anomaly if score exceeds threshold
            is_anomaly = combined_score > self.params["z_threshold"]

            record = dict(r)
            record["anomaly"] = is_anomaly
            record["anomaly_score"] = round(combined_score, 3)
            record["_global_z"] = round(global_z, 2)
            record["_weekday_z"] = round(wd_z, 2)
            record["_rolling_z"] = round(rolling_z, 2)
            results.append(record)

        num_anomalies = sum(1 for r in results if r["anomaly"])
        logger.info(
            f"Detected {num_anomalies} anomalies out of {len(results)} data points"
        )

        return results

    def get_anomaly_insights(self, results: list[dict] | Any) -> List[Dict]:
        """Get detailed insights about detected anomalies.

        Args:
            results: Output from detect_anomalies()

        Returns:
            List of anomaly insight dicts.
        """
        records = self._to_records(results)
        anomalies = [r for r in records if r.get("anomaly")]

        if not anomalies:
            return []

        insights = []
        all_records = records

        for row in anomalies:
            date = row["date"]
            cost = row["cost"]
            score = row.get("anomaly_score", 0)

            # Previous week average for context
            date_dt = self._parse_date(date)
            week_before = [
                r["cost"] for r in all_records if self._parse_date(r["date"]) < date_dt
            ][-7:]

            avg_before = sum(week_before) / len(week_before) if week_before else cost
            deviation = (
                ((cost - avg_before) / avg_before * 100) if avg_before > 0 else 0
            )

            insight = {
                "date": date if isinstance(date, str) else date.strftime("%Y-%m-%d"),
                "cost": float(cost),
                "anomaly_score": float(score),
                "previous_week_avg": round(float(avg_before), 2),
                "deviation_percent": round(float(deviation), 1),
                "severity": self._get_severity(score, deviation),
            }
            insights.append(insight)

        severity_order = {"critical": 3, "high": 2, "medium": 1, "low": 0}
        insights.sort(key=lambda x: severity_order.get(x["severity"], 0), reverse=True)

        return insights

    def analyze_service_anomalies(
        self, service_data: list[dict] | Any
    ) -> Dict[str, List[Dict]]:
        """Detect anomalies per service.

        Args:
            service_data: List of dicts with 'service', 'date', 'cost' keys,
                          OR a pandas DataFrame.

        Returns:
            Dict mapping service names to their anomaly insights.
        """
        records = self._to_records(service_data)

        # Group by service
        from collections import defaultdict

        by_service: dict[str, list[dict]] = defaultdict(list)
        for r in records:
            by_service[r["service"]].append(r)

        service_anomalies: Dict[str, List[Dict]] = {}

        for service, svc_records in by_service.items():
            if len(svc_records) < self.min_history_days:
                continue

            detector = CostAnomalyDetector(self.config)
            clean = [{"date": r["date"], "cost": r["cost"]} for r in svc_records]

            results = detector.detect_anomalies(clean)
            insights = detector.get_anomaly_insights(results)

            if insights:
                service_anomalies[service] = insights

        logger.info(f"Analyzed {len(service_anomalies)} services with anomalies")
        return service_anomalies

    # ──────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────

    def _get_severity(self, score: float, deviation: float) -> str:
        if score > self.params["z_threshold"] * 2.5 or abs(deviation) > 100:
            return "critical"
        elif score > self.params["z_threshold"] * 1.75 or abs(deviation) > 50:
            return "high"
        elif score > self.params["z_threshold"] * 1.25 or abs(deviation) > 25:
            return "medium"
        else:
            return "low"

    @staticmethod
    def _median_val(values: list[float]) -> float:
        """Named differently to avoid clash with the staticmethod _median."""
        return statistics.median(values) if values else 0.0

    @staticmethod
    def _parse_date(d) -> datetime:
        if isinstance(d, datetime):
            return d
        if isinstance(d, str):
            return datetime.fromisoformat(d)
        # Handle date objects
        return datetime(d.year, d.month, d.day)

    @staticmethod
    def _to_records(df) -> list[dict]:
        """Convert pandas DataFrame or list of dicts to list of dicts.

        This lets the code work with OR without pandas installed.
        """
        if isinstance(df, list):
            return df

        # If it's a pandas DataFrame, convert
        try:
            return df.to_dict("records")
        except AttributeError:
            pass

        # If it's some other iterable
        return list(df)
