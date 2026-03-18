"""Slack notification integration."""

import json
from typing import Dict, List, Optional
from slack_sdk.webhook import WebhookClient
from slack_sdk.errors import SlackApiError

from ..utils.logger import get_logger
from ..utils.config import get_config


logger = get_logger(__name__)


class SlackNotifier:
    """Send notifications to Slack."""
    
    def __init__(self, config=None):
        """Initialize Slack notifier.
        
        Args:
            config: Configuration object
        """
        self.config = config or get_config()
        self.webhook_url = self.config.get('notifications.slack.webhook_url')
        self.channel = self.config.get('notifications.slack.channel', '#aws-costs')
        self.mention_on_critical = self.config.get(
            'notifications.slack.mention_on_critical',
            '@channel'
        )
        
        if self.webhook_url:
            self.client = WebhookClient(self.webhook_url)
            logger.info("Slack notifier initialized")
        else:
            self.client = None
            logger.warning("Slack webhook URL not configured")
    
    def send_message(self, text: str, blocks: Optional[List[Dict]] = None) -> bool:
        """Send a message to Slack.
        
        Args:
            text: Plain text message (fallback)
            blocks: Slack Block Kit blocks for rich formatting
            
        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            logger.error("Slack client not configured")
            return False
        
        try:
            response = self.client.send(
                text=text,
                blocks=blocks
            )
            
            if response.status_code == 200:
                logger.info("Message sent to Slack successfully")
                return True
            else:
                logger.error(f"Failed to send Slack message: {response.status_code}")
                return False
                
        except SlackApiError as e:
            logger.error(f"Slack API error: {e.response['error']}")
            return False
        except Exception as e:
            logger.error(f"Error sending Slack message: {str(e)}")
            return False
    
    def send_cost_alert(
        self,
        alert_type: str,
        cost: float,
        threshold: float,
        details: Dict
    ) -> bool:
        """Send a cost alert to Slack.
        
        Args:
            alert_type: Type of alert (budget, spike, anomaly)
            cost: Current cost
            threshold: Threshold that was exceeded
            details: Additional details about the alert
            
        Returns:
            True if successful, False otherwise
        """
        # Determine severity
        severity = details.get('severity', 'medium')
        emoji = self._get_severity_emoji(severity)
        color = self._get_severity_color(severity)
        
        # Create message
        mention = ""
        if severity in ['critical', 'high']:
            mention = f"{self.mention_on_critical} "
        
        text = f"{mention}{emoji} AWS Cost Alert: {alert_type.upper()}"
        
        # Create blocks
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} AWS Cost Alert"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Alert Type:*\n{alert_type.title()}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Severity:*\n{severity.upper()}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Current Cost:*\n${cost:.2f}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Threshold:*\n${threshold:.2f}"
                    }
                ]
            }
        ]
        
        # Add details
        if details:
            detail_text = ""
            for key, value in details.items():
                if key not in ['severity']:
                    detail_text += f"• *{key.replace('_', ' ').title()}:* {value}\n"
            
            if detail_text:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": detail_text
                    }
                })
        
        # Add divider
        blocks.append({"type": "divider"})
        
        return self.send_message(text=text, blocks=blocks)
    
    def send_daily_summary(self, summary: Dict) -> bool:
        """Send daily cost summary to Slack.
        
        Args:
            summary: Cost summary data
            
        Returns:
            True if successful, False otherwise
        """
        today_cost = summary['today_cost']
        yesterday_cost = summary['yesterday_cost']
        week_cost = summary['week_cost']
        month_cost = summary['month_cost']
        
        # Calculate change
        change = ((today_cost - yesterday_cost) / yesterday_cost * 100) if yesterday_cost > 0 else 0
        trend_emoji = "📈" if change > 0 else "📉" if change < 0 else "➡️"
        
        text = f"📊 AWS Daily Cost Summary - ${today_cost:.2f}"
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "📊 AWS Daily Cost Summary"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Today:*\n${today_cost:.2f}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Yesterday:*\n${yesterday_cost:.2f}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*This Week:*\n${week_cost:.2f}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*This Month:*\n${month_cost:.2f}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Daily Change:*\n{trend_emoji} {change:+.1f}%"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Avg Daily:*\n${summary['avg_daily_cost']:.2f}"
                    }
                ]
            }
        ]
        
        # Add top services
        if summary.get('top_services'):
            services_text = ""
            for i, svc in enumerate(summary['top_services'][:5], 1):
                services_text += f"{i}. {svc['service']}: ${svc['total_cost']:.2f}\n"
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Top Services (7 days):*\n{services_text}"
                }
            })
        
        # Add threshold warnings
        warnings = []
        for period, threshold_data in summary.get('thresholds', {}).items():
            if threshold_data.get('exceeded'):
                pct = threshold_data['percent_of_budget']
                warnings.append(
                    f"⚠️ {period.title()} budget exceeded: {pct:.0f}% of threshold"
                )
        
        if warnings:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Warnings:*\n" + "\n".join(warnings)
                }
            })
        
        blocks.append({"type": "divider"})
        
        return self.send_message(text=text, blocks=blocks)
    
    def send_anomaly_alert(self, anomalies: List[Dict]) -> bool:
        """Send anomaly detection alert to Slack.
        
        Args:
            anomalies: List of detected anomalies
            
        Returns:
            True if successful, False otherwise
        """
        if not anomalies:
            return True
        
        # Get most severe anomaly
        severity_order = {'critical': 3, 'high': 2, 'medium': 1, 'low': 0}
        most_severe = max(anomalies, key=lambda x: severity_order.get(x['severity'], 0))
        
        emoji = self._get_severity_emoji(most_severe['severity'])
        
        text = f"{emoji} {len(anomalies)} cost anomal{'y' if len(anomalies) == 1 else 'ies'} detected"
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} Cost Anomalies Detected"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"Found *{len(anomalies)}* anomal{'y' if len(anomalies) == 1 else 'ies'} in your AWS costs"
                }
            }
        ]
        
        # Add top 5 anomalies
        for anomaly in anomalies[:5]:
            severity_emoji = self._get_severity_emoji(anomaly['severity'])
            blocks.append({
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Date:*\n{anomaly['date']}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Severity:*\n{severity_emoji} {anomaly['severity'].upper()}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Cost:*\n${anomaly['cost']:.2f}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Deviation:*\n{anomaly['deviation_percent']:+.1f}%"
                    }
                ]
            })
        
        if len(anomalies) > 5:
            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"_...and {len(anomalies) - 5} more anomalies_"
                    }
                ]
            })
        
        blocks.append({"type": "divider"})
        
        return self.send_message(text=text, blocks=blocks)
    
    def _get_severity_emoji(self, severity: str) -> str:
        """Get emoji for severity level.
        
        Args:
            severity: Severity level
            
        Returns:
            Emoji string
        """
        emojis = {
            'critical': '🚨',
            'high': '⚠️',
            'medium': '⚡',
            'low': 'ℹ️'
        }
        return emojis.get(severity, 'ℹ️')
    
    def _get_severity_color(self, severity: str) -> str:
        """Get color for severity level.
        
        Args:
            severity: Severity level
            
        Returns:
            Color hex code
        """
        colors = {
            'critical': '#FF0000',
            'high': '#FF6B00',
            'medium': '#FFD700',
            'low': '#00AA00'
        }
        return colors.get(severity, '#CCCCCC')
