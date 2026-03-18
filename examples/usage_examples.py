#!/usr/bin/env python3
"""
Example Usage Scripts for AWS Cost Sentinel

This file demonstrates various ways to use AWS Cost Sentinel programmatically.
"""

from collections import defaultdict


# Example 1: Basic Monitoring Cycle
def example_basic_monitoring():
    """Run a basic monitoring cycle."""
    from src.sentinel import CostSentinel
    
    sentinel = CostSentinel()
    results = sentinel.run_monitoring_cycle()
    
    print(f"Monitoring complete!")
    print(f"Alerts sent: {len(results['alerts_sent'])}")
    print(f"Anomalies detected: {len(results['anomalies'])}")
    
    return results


# Example 2: Get Cost Summary
def example_cost_summary():
    """Get and display cost summary."""
    from src.core.cost_monitor import AWSCostMonitor
    
    monitor = AWSCostMonitor()
    summary = monitor.get_cost_summary()
    
    print("\n=== Cost Summary ===")
    print(f"Today: ${summary['today_cost']:.2f}")
    print(f"Yesterday: ${summary['yesterday_cost']:.2f}")
    print(f"This Week: ${summary['week_cost']:.2f}")
    print(f"This Month: ${summary['month_cost']:.2f}")
    
    print("\n=== Top Services ===")
    for i, service in enumerate(summary['top_services'][:5], 1):
        print(f"{i}. {service['service']}: ${service['total_cost']:.2f}")
    
    return summary


# Example 3: Detect Anomalies
def example_anomaly_detection():
    """Detect and report cost anomalies."""
    from src.core.cost_monitor import AWSCostMonitor
    from src.ml.anomaly_detector import CostAnomalyDetector
    
    monitor = AWSCostMonitor()
    daily_costs = monitor.get_daily_costs(days=30)
    
    detector = CostAnomalyDetector()
    results = detector.detect_anomalies(daily_costs)
    insights = detector.get_anomaly_insights(results)
    
    print(f"\n=== Anomaly Detection ===")
    print(f"Analyzed {len(daily_costs)} days of data")
    print(f"Found {len(insights)} anomalies")
    
    for anomaly in insights:
        print(f"\nDate: {anomaly['date']}")
        print(f"  Cost: ${anomaly['cost']:.2f}")
        print(f"  Deviation: {anomaly['deviation_percent']:+.1f}%")
        print(f"  Severity: {anomaly['severity']}")
    
    return insights


# Example 4: Send Custom Alert
def example_custom_alert():
    """Send a custom cost alert."""
    from src.notifications.manager import NotificationManager
    
    notifier = NotificationManager()
    
    results = notifier.send_cost_alert(
        alert_type='custom_budget',
        cost=250.00,
        threshold=200.00,
        details={
            'severity': 'high',
            'service': 'EC2',
            'region': 'us-east-1',
            'message': 'EC2 costs exceeded threshold in us-east-1'
        }
    )
    
    print("\n=== Custom Alert ===")
    print(f"Alert sent successfully: {all(results.values())}")
    print(f"Results: {results}")
    
    return results


# Example 5: Service-Level Analysis
def example_service_analysis():
    """Analyze costs by service."""
    from src.core.cost_monitor import AWSCostMonitor
    import statistics
    
    monitor = AWSCostMonitor()
    
    # get_service_costs returns List[Dict] with 'date', 'service', 'cost' keys
    service_data = monitor.get_service_costs(days=30)
    
    if not service_data:
        print("No service cost data available")
        return {}
    
    # Group costs by service
    by_service = defaultdict(list)
    for r in service_data:
        by_service[r['service']].append(r['cost'])
    
    # Calculate statistics per service
    stats = {}
    for service, costs in by_service.items():
        avg = sum(costs) / len(costs)
        std = statistics.stdev(costs) if len(costs) > 1 else 0.0
        stats[service] = {
            'sum': round(sum(costs), 2),
            'mean': round(avg, 2),
            'std': round(std, 2),
            'min': round(min(costs), 2),
            'max': round(max(costs), 2),
        }
    
    # Sort by total cost descending
    sorted_stats = sorted(stats.items(), key=lambda x: x[1]['sum'], reverse=True)
    
    print("\n=== Service Cost Statistics (30 days) ===")
    print(f"{'Service':<30} {'Total':>10} {'Mean':>10} {'Std':>10} {'Min':>10} {'Max':>10}")
    print("-" * 80)
    for service, s in sorted_stats:
        print(f"{service:<30} ${s['sum']:>9.2f} ${s['mean']:>9.2f} ${s['std']:>9.2f} ${s['min']:>9.2f} ${s['max']:>9.2f}")
    
    # Find services with high variance
    high_variance = [
        service for service, s in sorted_stats
        if s['std'] > s['mean'] * 0.5
    ]
    
    if high_variance:
        print("\n=== Services with High Cost Variance ===")
        for service in high_variance:
            print(f"  - {service}")
    
    return stats


# Example 6: Cost Forecasting
def example_forecasting():
    """Get cost forecast."""
    from src.core.cost_monitor import AWSCostMonitor
    
    monitor = AWSCostMonitor()
    forecast = monitor.get_forecast(days_ahead=30)
    
    if forecast:
        print("\n=== Cost Forecast ===")
        print(f"Projected cost (next 30 days): ${forecast['forecast_cost']:.2f}")
        print(f"Period: {forecast['start_date']} to {forecast['end_date']}")
    else:
        print("Forecast not available")
    
    return forecast


# Example 7: Custom Configuration
def example_custom_config():
    """Use custom configuration."""
    from src.utils.config import Config
    from src.sentinel import CostSentinel
    
    config = Config('config.yaml')
    
    config.set('monitoring.budgets.daily_max', 150.0)
    config.set('anomaly_detection.sensitivity', 'high')
    
    sentinel = CostSentinel()
    sentinel.config = config
    
    print("\n=== Custom Configuration ===")
    print(f"Daily budget: ${config.get('monitoring.budgets.daily_max')}")
    print(f"Sensitivity: {config.get('anomaly_detection.sensitivity')}")
    
    return sentinel


# Example 8: Service-Specific Anomalies
def example_service_anomalies():
    """Detect anomalies for specific services."""
    from src.core.cost_monitor import AWSCostMonitor
    from src.ml.anomaly_detector import CostAnomalyDetector
    
    monitor = AWSCostMonitor()
    detector = CostAnomalyDetector()
    
    # get_service_costs returns List[Dict]
    service_data = monitor.get_service_costs(days=30)
    
    service_anomalies = detector.analyze_service_anomalies(service_data)
    
    print("\n=== Service-Level Anomalies ===")
    for service, anomalies in service_anomalies.items():
        print(f"\n{service}: {len(anomalies)} anomalies")
        for anomaly in anomalies[:3]:
            print(f"  - {anomaly['date']}: ${anomaly['cost']:.2f} ({anomaly['severity']})")
    
    return service_anomalies


# Example 9: Scheduled Reporting
def example_scheduled_report():
    """Send scheduled cost report."""
    from src.sentinel import CostSentinel
    
    sentinel = CostSentinel()
    results = sentinel.send_daily_report()
    
    print("\n=== Scheduled Report ===")
    print(f"Success: {results['success']}")
    if results['success']:
        print("Daily report sent to all configured channels")
    else:
        print(f"Error: {results.get('error', 'Unknown error')}")
    
    return results


# Example 10: Multi-Account Monitoring (Advanced)
def example_multi_account():
    """Monitor multiple AWS accounts (requires cross-account role)."""
    from src.core.cost_monitor import AWSCostMonitor
    import boto3
    
    accounts = [
        {'name': 'Production', 'role_arn': 'arn:aws:iam::111111111111:role/CostMonitorRole'},
        {'name': 'Development', 'role_arn': 'arn:aws:iam::222222222222:role/CostMonitorRole'},
    ]
    
    all_costs = {}
    
    for account in accounts:
        print(f"\nMonitoring account: {account['name']}")
        
        sts = boto3.client('sts')
        assumed_role = sts.assume_role(
            RoleArn=account['role_arn'],
            RoleSessionName='CostMonitoring'
        )
        
        # Note: You'd need to modify AWSCostMonitor to accept credentials
        monitor = AWSCostMonitor()
        summary = monitor.get_cost_summary()
        
        all_costs[account['name']] = summary
        print(f"  Today: ${summary['today_cost']:.2f}")
        print(f"  Month: ${summary['month_cost']:.2f}")
    
    total_today = sum(s['today_cost'] for s in all_costs.values())
    total_month = sum(s['month_cost'] for s in all_costs.values())
    
    print(f"\n=== Total Across All Accounts ===")
    print(f"Today: ${total_today:.2f}")
    print(f"Month: ${total_month:.2f}")
    
    return all_costs


if __name__ == "__main__":
    import sys
    
    examples = {
        '1': ('Basic Monitoring', example_basic_monitoring),
        '2': ('Cost Summary', example_cost_summary),
        '3': ('Anomaly Detection', example_anomaly_detection),
        '4': ('Custom Alert', example_custom_alert),
        '5': ('Service Analysis', example_service_analysis),
        '6': ('Cost Forecasting', example_forecasting),
        '7': ('Custom Configuration', example_custom_config),
        '8': ('Service Anomalies', example_service_anomalies),
        '9': ('Scheduled Report', example_scheduled_report),
        # '10': ('Multi-Account', example_multi_account),  # Advanced
    }
    
    if len(sys.argv) > 1:
        example_num = sys.argv[1]
        if example_num in examples:
            name, func = examples[example_num]
            print(f"\nRunning Example {example_num}: {name}")
            print("=" * 50)
            func()
        else:
            print(f"Unknown example: {example_num}")
    else:
        print("\nAWS Cost Sentinel - Example Usage")
        print("=" * 50)
        print("\nAvailable examples:")
        for num, (name, _) in examples.items():
            print(f"  {num}. {name}")
        print("\nUsage: python examples/usage_examples.py <example_number>")
        print("Example: python examples/usage_examples.py 1")