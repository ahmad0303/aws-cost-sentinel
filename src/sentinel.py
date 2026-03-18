"""Main AWS Cost Sentinel orchestrator."""

from typing import Dict
from datetime import datetime

from .core.cost_monitor import AWSCostMonitor
from .ml.anomaly_detector import CostAnomalyDetector
from .notifications.manager import NotificationManager
from .utils.logger import get_logger, setup_logger
from .utils.config import get_config


logger = get_logger(__name__)


class CostSentinel:
    """Main AWS Cost Sentinel orchestrator."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize Cost Sentinel.
        
        Args:
            config_path: Path to configuration file
        """
        # Load configuration
        self.config = get_config(config_path)
        
        # Setup logging
        log_level = self.config.get('logging.level', 'INFO')
        log_format = self.config.get('logging.format')
        setup_logger(level=log_level, format_string=log_format)
        
        logger.info("=" * 50)
        logger.info("AWS Cost Sentinel Starting")
        logger.info("=" * 50)
        
        # Initialize components
        self.cost_monitor = AWSCostMonitor(self.config)
        self.anomaly_detector = CostAnomalyDetector(self.config)
        self.notification_manager = NotificationManager(self.config)
        
        logger.info("All components initialized successfully")
    
    def run_monitoring_cycle(self) -> Dict:
        """Run a complete monitoring cycle.
        
        Returns:
            Dictionary with monitoring results
        """
        logger.info("Starting monitoring cycle")
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'summary': None,
            'anomalies': [],
            'alerts_sent': [],
            'errors': []
        }
        
        try:
            # Get cost summary
            logger.info("Fetching cost summary...")
            summary = self.cost_monitor.get_cost_summary()
            results['summary'] = summary
            
            # Check for threshold violations
            self._check_thresholds(summary, results)
            
            # Run anomaly detection if enabled
            if self.config.get('anomaly_detection.enabled', True):
                logger.info("Running anomaly detection...")
                self._detect_anomalies(summary, results)
            
            logger.info("Monitoring cycle completed successfully")
            
        except Exception as e:
            error_msg = f"Error during monitoring cycle: {str(e)}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
        
        return results
    
    def send_daily_report(self) -> Dict:
        """Send daily cost report.
        
        Returns:
            Dictionary with report send results
        """
        logger.info("Sending daily report...")
        
        try:
            summary = self.cost_monitor.get_cost_summary()
            results = self.notification_manager.send_daily_summary(summary)
            
            logger.info(f"Daily report sent: {results}")
            return {
                'success': all(results.values()),
                'results': results,
                'summary': summary
            }
            
        except Exception as e:
            logger.error(f"Error sending daily report: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _check_thresholds(self, summary: Dict, results: Dict) -> None:
        """Check budget thresholds and send alerts if exceeded.
        
        Args:
            summary: Cost summary data
            results: Results dictionary to update
        """
        thresholds = summary.get('thresholds', {})
        
        for period, threshold_data in thresholds.items():
            if threshold_data.get('exceeded'):
                logger.warning(f"Budget threshold exceeded for {period}")
                
                # Send alert
                alert_details = {
                    'period': period,
                    'percent_of_budget': threshold_data['percent_of_budget'],
                    'severity': self._get_threshold_severity(
                        threshold_data['percent_of_budget']
                    )
                }
                
                notification_results = self.notification_manager.send_cost_alert(
                    alert_type='budget_threshold',
                    cost=threshold_data['current_cost'],
                    threshold=threshold_data['threshold'],
                    details=alert_details
                )
                
                results['alerts_sent'].append({
                    'type': 'budget_threshold',
                    'period': period,
                    'results': notification_results
                })
        
        # Check for cost spikes
        spikes = summary.get('spikes', [])
        for spike in spikes:
            logger.warning(f"Cost spike detected on {spike['date']}")
            
            alert_details = {
                'date': spike['date'],
                'previous_cost': spike['previous_cost'],
                'percent_change': spike['percent_change'],
                'severity': 'high' if spike['percent_change'] > 100 else 'medium'
            }
            
            notification_results = self.notification_manager.send_cost_alert(
                alert_type='cost_spike',
                cost=spike['cost'],
                threshold=spike['threshold'],
                details=alert_details
            )
            
            results['alerts_sent'].append({
                'type': 'cost_spike',
                'date': spike['date'],
                'results': notification_results
            })
    
    def _detect_anomalies(self, summary: Dict, results: Dict) -> None:
        """Detect cost anomalies and send alerts.
        
        Args:
            summary: Cost summary data
            results: Results dictionary to update
        """
        try:
            # Get historical cost data
            lookback_days = self.config.get('monitoring.lookback_days', 30)
            daily_costs = self.cost_monitor.get_daily_costs(days=lookback_days)
            
            # Detect anomalies
            anomaly_results = self.anomaly_detector.detect_anomalies(daily_costs)
            insights = self.anomaly_detector.get_anomaly_insights(anomaly_results)
            
            results['anomalies'] = insights
            
            # Send alert if anomalies detected
            if insights:
                logger.info(f"Detected {len(insights)} anomalies")
                
                notification_results = self.notification_manager.send_anomaly_alert(
                    insights
                )
                
                results['alerts_sent'].append({
                    'type': 'anomaly_detection',
                    'count': len(insights),
                    'results': notification_results
                })
            else:
                logger.info("No anomalies detected")
                
        except Exception as e:
            error_msg = f"Error during anomaly detection: {str(e)}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
    
    def _get_threshold_severity(self, percent_of_budget: float) -> str:
        """Get severity level based on budget percentage.
        
        Args:
            percent_of_budget: Percentage of budget used
            
        Returns:
            Severity level
        """
        if percent_of_budget >= 150:
            return 'critical'
        elif percent_of_budget >= 125:
            return 'high'
        elif percent_of_budget >= 100:
            return 'medium'
        else:
            return 'low'
    
    def get_status(self) -> Dict:
        """Get current sentinel status.
        
        Returns:
            Status dictionary
        """
        return {
            'timestamp': datetime.now().isoformat(),
            'status': 'operational',
            'components': {
                'cost_monitor': 'active',
                'anomaly_detector': 'active' if self.config.get('anomaly_detection.enabled') else 'disabled',
                'notifications': {
                    'teams': 'active' if self.config.get('notifications.teams.enabled') else 'disabled',
                    'slack': 'active' if self.config.get('notifications.slack.enabled') else 'disabled',
                    'discord': 'active' if self.config.get('notifications.discord.enabled') else 'disabled',
                }
            },
            'config': {
                'lookback_days': self.config.get('monitoring.lookback_days'),
                'anomaly_sensitivity': self.config.get('anomaly_detection.sensitivity')
            }
        }


def main():
    """Main entry point for AWS Cost Sentinel."""
    import sys
    
    # Get config path from command line or use default
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    
    # Initialize sentinel
    sentinel = CostSentinel(config_path)
    
    # Run monitoring cycle
    results = sentinel.run_monitoring_cycle()
    
    # Print summary
    print("\n" + "=" * 50)
    print("MONITORING CYCLE COMPLETE")
    print("=" * 50)
    print(f"Timestamp: {results['timestamp']}")
    print(f"Alerts Sent: {len(results['alerts_sent'])}")
    print(f"Anomalies Detected: {len(results['anomalies'])}")
    print(f"Errors: {len(results['errors'])}")
    
    if results['summary']:
        print(f"\nToday's Cost: ${results['summary']['today_cost']:.2f}")
        print(f"Month-to-Date: ${results['summary']['month_cost']:.2f}")
    
    print("=" * 50)
    
    return 0 if not results['errors'] else 1


if __name__ == "__main__":
    exit(main())
