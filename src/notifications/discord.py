"""Discord notification integration."""

from typing import Dict, List
from discord_webhook import DiscordWebhook, DiscordEmbed

from ..utils.logger import get_logger
from ..utils.config import get_config


logger = get_logger(__name__)


class DiscordNotifier:
    """Send notifications to Discord."""
    
    def __init__(self, config=None):
        """Initialize Discord notifier.
        
        Args:
            config: Configuration object
        """
        self.config = config or get_config()
        self.webhook_url = self.config.get('notifications.discord.webhook_url')
        self.mention_on_critical = self.config.get(
            'notifications.discord.mention_on_critical',
            '@everyone'
        )
        
        if self.webhook_url:
            logger.info("Discord notifier initialized")
        else:
            logger.warning("Discord webhook URL not configured")
    
    def send_message(self, content: str = None, embeds: List[DiscordEmbed] = None) -> bool:
        """Send a message to Discord.
        
        Args:
            content: Plain text content
            embeds: List of Discord embeds
            
        Returns:
            True if successful, False otherwise
        """
        if not self.webhook_url:
            logger.error("Discord webhook URL not configured")
            return False
        
        try:
            webhook = DiscordWebhook(url=self.webhook_url, content=content)
            
            if embeds:
                for embed in embeds:
                    webhook.add_embed(embed)
            
            response = webhook.execute()
            
            if response.status_code in [200, 204]:
                logger.info("Message sent to Discord successfully")
                return True
            else:
                logger.error(f"Failed to send Discord message: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending Discord message: {str(e)}")
            return False
    
    def send_cost_alert(
        self,
        alert_type: str,
        cost: float,
        threshold: float,
        details: Dict
    ) -> bool:
        """Send a cost alert to Discord.
        
        Args:
            alert_type: Type of alert (budget, spike, anomaly)
            cost: Current cost
            threshold: Threshold that was exceeded
            details: Additional details about the alert
            
        Returns:
            True if successful, False otherwise
        """
        severity = details.get('severity', 'medium')
        emoji = self._get_severity_emoji(severity)
        color = self._get_severity_color(severity)
        
        # Create mention for critical alerts
        content = None
        if severity in ['critical', 'high']:
            content = self.mention_on_critical
        
        # Create embed
        embed = DiscordEmbed(
            title=f"{emoji} AWS Cost Alert: {alert_type.title()}",
            color=color
        )
        
        embed.add_embed_field(name="Alert Type", value=alert_type.title(), inline=True)
        embed.add_embed_field(name="Severity", value=severity.upper(), inline=True)
        embed.add_embed_field(name="Current Cost", value=f"${cost:.2f}", inline=True)
        embed.add_embed_field(name="Threshold", value=f"${threshold:.2f}", inline=True)
        
        # Add additional details
        if details:
            for key, value in details.items():
                if key not in ['severity']:
                    embed.add_embed_field(
                        name=key.replace('_', ' ').title(),
                        value=str(value),
                        inline=True
                    )
        
        embed.set_footer(text="AWS Cost Sentinel")
        embed.set_timestamp()
        
        return self.send_message(content=content, embeds=[embed])
    
    def send_daily_summary(self, summary: Dict) -> bool:
        """Send daily cost summary to Discord.
        
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
        
        # Create embed
        embed = DiscordEmbed(
            title="📊 AWS Daily Cost Summary",
            color='03b2f8'  # Blue color
        )
        
        embed.add_embed_field(name="Today", value=f"${today_cost:.2f}", inline=True)
        embed.add_embed_field(name="Yesterday", value=f"${yesterday_cost:.2f}", inline=True)
        embed.add_embed_field(
            name="Daily Change",
            value=f"{trend_emoji} {change:+.1f}%",
            inline=True
        )
        embed.add_embed_field(name="This Week", value=f"${week_cost:.2f}", inline=True)
        embed.add_embed_field(name="This Month", value=f"${month_cost:.2f}", inline=True)
        embed.add_embed_field(
            name="Avg Daily",
            value=f"${summary['avg_daily_cost']:.2f}",
            inline=True
        )
        
        # Add top services
        if summary.get('top_services'):
            services_text = ""
            for i, svc in enumerate(summary['top_services'][:5], 1):
                services_text += f"{i}. {svc['service']}: ${svc['total_cost']:.2f}\n"
            
            embed.add_embed_field(
                name="Top Services (7 days)",
                value=services_text or "No data",
                inline=False
            )
        
        # Add threshold warnings
        warnings = []
        for period, threshold_data in summary.get('thresholds', {}).items():
            if threshold_data.get('exceeded'):
                pct = threshold_data['percent_of_budget']
                warnings.append(
                    f"⚠️ {period.title()}: {pct:.0f}% of budget"
                )
        
        if warnings:
            embed.add_embed_field(
                name="⚠️ Warnings",
                value="\n".join(warnings),
                inline=False
            )
        
        embed.set_footer(text="AWS Cost Sentinel")
        embed.set_timestamp()
        
        return self.send_message(embeds=[embed])
    
    def send_anomaly_alert(self, anomalies: List[Dict]) -> bool:
        """Send anomaly detection alert to Discord.
        
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
        color = self._get_severity_color(most_severe['severity'])
        
        # Create embed
        embed = DiscordEmbed(
            title=f"{emoji} Cost Anomalies Detected",
            description=f"Found **{len(anomalies)}** anomal{'y' if len(anomalies) == 1 else 'ies'} in your AWS costs",
            color=color
        )
        
        # Add top 3 anomalies as fields
        for i, anomaly in enumerate(anomalies[:3], 1):
            severity_emoji = self._get_severity_emoji(anomaly['severity'])
            field_value = (
                f"**Date:** {anomaly['date']}\n"
                f"**Cost:** ${anomaly['cost']:.2f}\n"
                f"**Deviation:** {anomaly['deviation_percent']:+.1f}%\n"
                f"**Severity:** {severity_emoji} {anomaly['severity'].upper()}"
            )
            embed.add_embed_field(
                name=f"Anomaly #{i}",
                value=field_value,
                inline=True
            )
        
        if len(anomalies) > 3:
            embed.set_footer(text=f"...and {len(anomalies) - 3} more anomalies | AWS Cost Sentinel")
        else:
            embed.set_footer(text="AWS Cost Sentinel")
        
        embed.set_timestamp()
        
        # Mention for critical anomalies
        content = None
        if most_severe['severity'] in ['critical', 'high']:
            content = self.mention_on_critical
        
        return self.send_message(content=content, embeds=[embed])
    
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
        """Get color code for severity level.
        
        Args:
            severity: Severity level
            
        Returns:
            Integer color code
        """
        colors = {
            'critical': 'FF0000',
            'high': 'FF6B00',
            'medium': 'FFD700',
            'low': '00AA00'
        }
        return colors.get(severity, 'CCCCCC')
