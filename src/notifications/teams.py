"""Microsoft Teams notification integration."""

import pymsteams
from typing import Dict, List
from ..utils.logger import get_logger
from ..utils.config import get_config

logger = get_logger(__name__)


class TeamsNotifier:
    """Send notifications to Microsoft Teams."""

    def __init__(self, config=None):
        self.config = config or get_config()
        self.webhook_url = self.config.get("notifications.teams.webhook_url")

    def send_cost_alert(
        self, alert_type: str, cost: float, threshold: float, details: Dict
    ) -> bool:
        """Send cost alert to Teams."""
        if not self.webhook_url:
            logger.error("Teams webhook URL not configured")
            return False

        try:
            # Create message card
            card = pymsteams.connectorcard(self.webhook_url)

            severity = details.get("severity", "medium")

            # Title with emoji
            card.title(f"🚨 AWS Cost Alert: {alert_type.title()}")

            # Color based on severity
            colors = {
                "critical": "FF0000",
                "high": "FF6B00",
                "medium": "FFD700",
                "low": "00AA00",
            }
            card.color(colors.get(severity, "0078D4"))

            # Add sections
            section = pymsteams.cardsection()
            section.addFact("Alert Type", alert_type.title())
            section.addFact("Severity", severity.upper())
            section.addFact("Current Cost", f"${cost:.2f}")
            section.addFact("Threshold", f"${threshold:.2f}")
            section.addFact(
                "Percent of Budget", f"{details.get('percent_of_budget', 0):.1f}%"
            )

            card.addSection(section)

            # Send
            card.send()
            logger.info("Cost alert sent to Teams successfully")
            return True

        except Exception as e:
            logger.error(f"Error sending Teams alert: {str(e)}")
            return False

    def send_daily_summary(self, summary: Dict) -> bool:
        """Send daily summary to Teams."""
        if not self.webhook_url:
            return False

        try:
            card = pymsteams.connectorcard(self.webhook_url)
            card.title("📊 AWS Daily Cost Summary")
            card.color("0078D4")

            # Cost summary section
            today = summary["today_cost"]
            yesterday = summary["yesterday_cost"]
            week = summary["week_cost"]
            month = summary["month_cost"]

            change = ((today - yesterday) / yesterday * 100) if yesterday > 0 else 0
            trend = "📈" if change > 0 else "📉"

            summary_section = pymsteams.cardsection()
            summary_section.addFact("Today", f"${today:.2f}")
            summary_section.addFact("Yesterday", f"${yesterday:.2f}")
            summary_section.addFact("This Week", f"${week:.2f}")
            summary_section.addFact("This Month", f"${month:.2f}")
            summary_section.addFact("Daily Change", f"{trend} {change:+.1f}%")
            card.addSection(summary_section)

            # Top services section
            if summary.get("top_services"):
                services_section = pymsteams.cardsection()
                services_section.title("Top Services (7 days)")

                services_text = ""
                for i, svc in enumerate(summary["top_services"][:5], 1):
                    services_text += (
                        f"{i}. {svc['service']}: ${svc['total_cost']:.2f}\n"
                    )

                services_section.text(services_text)
                card.addSection(services_section)

            card.send()
            logger.info("Daily summary sent to Teams successfully")
            return True

        except Exception as e:
            logger.error(f"Error sending Teams summary: {str(e)}")
            return False

    def send_anomaly_alert(self, anomalies: List[Dict]) -> bool:
        """Send anomaly alert to Teams."""
        if not anomalies or not self.webhook_url:
            return False

        try:
            card = pymsteams.connectorcard(self.webhook_url)
            card.title(f"⚠️ {len(anomalies)} Cost Anomalies Detected")
            card.color("FF6B00")

            # Anomalies section
            anomaly_section = pymsteams.cardsection()
            anomaly_section.title("Unusual spending patterns detected")

            anomaly_text = ""
            for i, anomaly in enumerate(anomalies[:5], 1):
                severity_emoji = {
                    "critical": "🚨",
                    "high": "⚠️",
                    "medium": "⚡",
                    "low": "ℹ️",
                }.get(anomaly["severity"], "ℹ️")

                anomaly_text += f"{i}. {severity_emoji} **{anomaly['date']}**: "
                anomaly_text += f"${anomaly['cost']:.2f} "
                anomaly_text += f"({anomaly['severity'].upper()}, {anomaly['deviation_percent']:+.1f}%)\n"

            anomaly_section.text(anomaly_text)
            card.addSection(anomaly_section)

            card.send()
            logger.info("Anomaly alert sent to Teams successfully")
            return True

        except Exception as e:
            logger.error(f"Error sending Teams anomaly alert: {str(e)}")
            return False
