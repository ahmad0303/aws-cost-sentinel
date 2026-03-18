"""AWS Cost Monitoring Engine.

Drop-in replacement — returns lists of dicts instead of DataFrames.
Zero dependency on pandas/numpy.
"""

import boto3
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict

from ..utils.logger import get_logger
from ..utils.config import get_config


logger = get_logger(__name__)


class AWSCostMonitor:
    """Monitor AWS costs using Cost Explorer API."""

    def __init__(self, config=None):
        """Initialize AWS Cost Monitor.

        Args:
            config: Configuration object (optional, will load default if not provided)
        """
        self.config = config or get_config()

        region = self.config.get('aws.region', 'us-east-1')
        self.ce_client = boto3.client('ce', region_name=region)

        logger.info(f"Initialized AWS Cost Monitor in region: {region}")

    def get_cost_and_usage(
        self,
        start_date: datetime,
        end_date: datetime,
        granularity: str = "DAILY",
        metrics: List[str] = None,
        group_by: List[Dict] = None
    ) -> Dict:
        """Get cost and usage data from AWS Cost Explorer.

        Args:
            start_date: Start date for the query
            end_date: End date for the query
            granularity: DAILY, MONTHLY, or HOURLY
            metrics: List of metrics to retrieve (default: ['UnblendedCost'])
            group_by: List of dimension groupings

        Returns:
            Cost and usage data from AWS
        """
        if metrics is None:
            metrics = ['UnblendedCost']

        params = {
            'TimePeriod': {
                'Start': start_date.strftime('%Y-%m-%d'),
                'End': end_date.strftime('%Y-%m-%d')
            },
            'Granularity': granularity,
            'Metrics': metrics
        }

        if group_by:
            params['GroupBy'] = group_by

        try:
            response = self.ce_client.get_cost_and_usage(**params)
            logger.debug(f"Retrieved cost data from {start_date} to {end_date}")
            return response
        except Exception as e:
            logger.error(f"Error retrieving cost data: {str(e)}")
            raise

    def get_daily_costs(self, days: int = 30) -> List[Dict]:
        """Get daily costs for the specified number of days.

        Args:
            days: Number of days to look back

        Returns:
            List of dicts with 'date' (str) and 'cost' (float) keys,
            sorted by date ascending.
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        response = self.get_cost_and_usage(
            start_date=start_date,
            end_date=end_date,
            granularity='DAILY'
        )

        data = []
        for result in response.get('ResultsByTime', []):
            date = result['TimePeriod']['Start']
            cost = float(result['Total']['UnblendedCost']['Amount'])
            data.append({'date': date, 'cost': round(cost, 4)})

        data.sort(key=lambda r: r['date'])

        logger.info(f"Retrieved {len(data)} days of cost data")
        return data

    def get_service_costs(self, days: int = 30) -> List[Dict]:
        """Get costs broken down by service.

        Args:
            days: Number of days to look back

        Returns:
            List of dicts with 'date', 'service', 'cost' keys,
            sorted by date then service.
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        response = self.get_cost_and_usage(
            start_date=start_date,
            end_date=end_date,
            granularity='DAILY',
            group_by=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
        )

        data = []
        for result in response.get('ResultsByTime', []):
            date = result['TimePeriod']['Start']
            for group in result.get('Groups', []):
                service = group['Keys'][0]
                cost = float(group['Metrics']['UnblendedCost']['Amount'])
                if cost > 0.001:  # skip negligible
                    data.append({
                        'date': date,
                        'service': service,
                        'cost': round(cost, 4)
                    })

        data.sort(key=lambda r: (r['date'], r['service']))

        unique_services = len(set(r['service'] for r in data))
        logger.info(f"Retrieved service-level costs for {unique_services} services")
        return data

    def get_current_month_cost(self) -> float:
        """Get total cost for the current month.

        Returns:
            Total cost for current month
        """
        now = datetime.now()
        start_date = datetime(now.year, now.month, 1)
        end_date = now

        response = self.get_cost_and_usage(
            start_date=start_date,
            end_date=end_date,
            granularity='MONTHLY'
        )

        if response.get('ResultsByTime'):
            cost = float(response['ResultsByTime'][0]['Total']['UnblendedCost']['Amount'])
            logger.info(f"Current month cost: ${cost:.2f}")
            return cost

        return 0.0

    def get_forecast(self, days_ahead: int = 30) -> Optional[Dict]:
        """Get AWS cost forecast.

        Args:
            days_ahead: Number of days to forecast

        Returns:
            Dictionary with forecast data, or None on failure
        """
        start_date = datetime.now()
        end_date = start_date + timedelta(days=days_ahead)

        try:
            response = self.ce_client.get_cost_forecast(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Metric='UNBLENDED_COST',
                Granularity='MONTHLY'
            )

            forecast_cost = float(response['Total']['Amount'])
            logger.info(f"Forecast for next {days_ahead} days: ${forecast_cost:.2f}")

            return {
                'forecast_cost': forecast_cost,
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d')
            }
        except Exception as e:
            logger.warning(f"Could not get forecast: {str(e)}")
            return None

    def check_budget_thresholds(self, current_cost: float, period: str = 'daily') -> Dict:
        """Check if current cost exceeds configured thresholds.

        Args:
            current_cost: Current cost to check
            period: 'daily', 'weekly', or 'monthly'

        Returns:
            Dictionary with threshold check results
        """
        threshold_key = f'monitoring.budgets.{period}_max'
        threshold = self.config.get(threshold_key, float('inf'))

        exceeded = current_cost > threshold
        percent_of_budget = (current_cost / threshold * 100) if threshold > 0 else 0

        result = {
            'exceeded': exceeded,
            'current_cost': current_cost,
            'threshold': threshold,
            'percent_of_budget': round(percent_of_budget, 1),
            'period': period
        }

        if exceeded:
            logger.warning(
                f"{period.capitalize()} cost ${current_cost:.2f} exceeds "
                f"threshold ${threshold:.2f} ({percent_of_budget:.1f}%)"
            )

        return result

    def detect_cost_spikes(self, data: List[Dict]) -> List[Dict]:
        """Detect cost spikes based on percentage increases.

        Args:
            data: List of dicts with 'date' and 'cost' keys (sorted by date)

        Returns:
            List of detected spikes
        """
        if len(data) < 2:
            return []

        daily_threshold = self.config.get('monitoring.alerts.daily_increase_percent', 50)
        spikes = []

        sorted_data = sorted(data, key=lambda r: r['date'])

        for i in range(1, len(sorted_data)):
            prev_cost = sorted_data[i - 1]['cost']
            curr_cost = sorted_data[i]['cost']
            curr_date = sorted_data[i]['date']

            if prev_cost > 0:
                pct_change = ((curr_cost - prev_cost) / prev_cost) * 100
            else:
                pct_change = 0

            if pct_change > daily_threshold:
                spikes.append({
                    'date': curr_date,
                    'cost': curr_cost,
                    'previous_cost': prev_cost,
                    'percent_change': round(pct_change, 1),
                    'threshold': daily_threshold,
                    'type': 'daily_spike'
                })

        return spikes

    def get_top_services(self, days: int = 7, top_n: int = 10) -> List[Dict]:
        """Get top N services by cost.

        Args:
            days: Number of days to analyze
            top_n: Number of top services to return

        Returns:
            List of top services with their costs
        """
        data = self.get_service_costs(days=days)

        if not data:
            return []

        # Sum costs per service
        totals: Dict[str, float] = defaultdict(float)
        for r in data:
            totals[r['service']] += r['cost']

        # Sort descending and take top N
        sorted_services = sorted(totals.items(), key=lambda x: x[1], reverse=True)

        return [
            {
                'service': service,
                'total_cost': round(cost, 2),
                'period_days': days
            }
            for service, cost in sorted_services[:top_n]
        ]

    def get_cost_summary(self) -> Dict:
        """Get a comprehensive cost summary.

        Returns:
            Dictionary with cost summary data
        """
        # Get daily costs
        daily_data = self.get_daily_costs(days=30)

        # Calculate metrics
        today_cost = daily_data[-1]['cost'] if daily_data else 0
        yesterday_cost = daily_data[-2]['cost'] if len(daily_data) > 1 else 0

        last_7 = daily_data[-7:] if len(daily_data) >= 7 else daily_data
        week_cost = sum(r['cost'] for r in last_7)

        all_costs = [r['cost'] for r in daily_data]
        month_cost_sum = sum(all_costs)
        avg_daily = month_cost_sum / len(all_costs) if all_costs else 0

        # Get current month actual cost
        current_month_actual = self.get_current_month_cost()

        # Get top services
        top_services = self.get_top_services(days=7)

        # Check thresholds
        daily_threshold = self.check_budget_thresholds(today_cost, 'daily')
        weekly_threshold = self.check_budget_thresholds(week_cost, 'weekly')
        monthly_threshold = self.check_budget_thresholds(current_month_actual, 'monthly')

        # Detect spikes
        spikes = self.detect_cost_spikes(daily_data)

        summary = {
            'today_cost': today_cost,
            'yesterday_cost': yesterday_cost,
            'week_cost': round(week_cost, 2),
            'month_cost': current_month_actual,
            'avg_daily_cost': round(avg_daily, 2),
            'top_services': top_services,
            'thresholds': {
                'daily': daily_threshold,
                'weekly': weekly_threshold,
                'monthly': monthly_threshold
            },
            'spikes': spikes,
            'timestamp': datetime.now().isoformat()
        }

        logger.info("Generated cost summary")
        return summary