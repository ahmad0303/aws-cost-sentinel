"""Notification manager to orchestrate all notification channels."""

from typing import Dict, List

from .teams import TeamsNotifier
from .slack import SlackNotifier
from .discord import DiscordNotifier
from ..utils.logger import get_logger
from ..utils.config import get_config


logger = get_logger(__name__)


class NotificationManager:
    """Manage and send notifications across multiple channels."""
    
    def __init__(self, config=None):
        """Initialize notification manager.
        
        Args:
            config: Configuration object
        """
        self.config = config or get_config()
        
        # Initialize notifiers based on configuration
        self.notifiers = []
        
        if self.config.get('notifications.teams.enabled', False):
            self.notifiers.append(TeamsNotifier(self.config))
            logger.info("Teams notifier enabled")
        
        if self.config.get('notifications.slack.enabled', False):
            self.notifiers.append(SlackNotifier(self.config))
            logger.info("Slack notifier enabled")
        
        if self.config.get('notifications.discord.enabled', False):
            self.notifiers.append(DiscordNotifier(self.config))
            logger.info("Discord notifier enabled")
        
        if not self.notifiers:
            logger.warning("No notification channels enabled")
    
    def send_cost_alert(
        self,
        alert_type: str,
        cost: float,
        threshold: float,
        details: Dict
    ) -> Dict[str, bool]:
        """Send cost alert to all enabled channels.
        
        Args:
            alert_type: Type of alert
            cost: Current cost
            threshold: Threshold exceeded
            details: Additional details
            
        Returns:
            Dictionary with results per notifier
        """
        results = {}
        
        for notifier in self.notifiers:
            notifier_name = notifier.__class__.__name__
            try:
                success = notifier.send_cost_alert(alert_type, cost, threshold, details)
                results[notifier_name] = success
            except Exception as e:
                logger.error(f"Error sending alert via {notifier_name}: {str(e)}")
                results[notifier_name] = False
        
        return results
    
    def send_daily_summary(self, summary: Dict) -> Dict[str, bool]:
        """Send daily summary to all enabled channels.
        
        Args:
            summary: Cost summary data
            
        Returns:
            Dictionary with results per notifier
        """
        results = {}
        
        for notifier in self.notifiers:
            notifier_name = notifier.__class__.__name__
            try:
                success = notifier.send_daily_summary(summary)
                results[notifier_name] = success
            except Exception as e:
                logger.error(f"Error sending summary via {notifier_name}: {str(e)}")
                results[notifier_name] = False
        
        return results
    
    def send_anomaly_alert(self, anomalies: List[Dict]) -> Dict[str, bool]:
        """Send anomaly alert to all enabled channels.
        
        Args:
            anomalies: List of detected anomalies
            
        Returns:
            Dictionary with results per notifier
        """
        results = {}
        
        for notifier in self.notifiers:
            notifier_name = notifier.__class__.__name__
            try:
                success = notifier.send_anomaly_alert(anomalies)
                results[notifier_name] = success
            except Exception as e:
                logger.error(f"Error sending anomaly alert via {notifier_name}: {str(e)}")
                results[notifier_name] = False
        
        return results
