#!/usr/bin/env python3
"""Command-line interface for AWS Cost Sentinel."""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime

from src.sentinel import CostSentinel
from src.core.cost_monitor import AWSCostMonitor
from src.ml.anomaly_detector import CostAnomalyDetector
from src.utils.logger import setup_logger


def cmd_monitor(args):
    """Run monitoring cycle."""
    sentinel = CostSentinel(args.config)
    results = sentinel.run_monitoring_cycle()
    
    print("\n" + "=" * 60)
    print("MONITORING RESULTS")
    print("=" * 60)
    
    if results['summary']:
        summary = results['summary']
        print(f"\nCost Summary:")
        print(f"  Today:     ${summary['today_cost']:>10.2f}")
        print(f"  Yesterday: ${summary['yesterday_cost']:>10.2f}")
        print(f"  This Week: ${summary['week_cost']:>10.2f}")
        print(f"  This Month: ${summary['month_cost']:>10.2f}")
        
        # Calculate change
        if summary['yesterday_cost'] > 0:
            change_pct = ((summary['today_cost'] - summary['yesterday_cost']) / 
                         summary['yesterday_cost'] * 100)
            print(f"  Change:    {change_pct:>+10.1f}%")
    
    print(f"\nAlerts Sent: {len(results['alerts_sent'])}")
    print(f"Anomalies: {len(results['anomalies'])}")
    print(f"Errors: {len(results['errors'])}")
    
    if results['errors']:
        print("\nErrors:")
        for error in results['errors']:
            print(f"  - {error}")
    
    print("=" * 60 + "\n")
    
    return 0 if not results['errors'] else 1


def cmd_report(args):
    """Send daily report."""
    sentinel = CostSentinel(args.config)
    results = sentinel.send_daily_report()
    
    if results['success']:
        print("Daily report sent successfully")
        return 0
    else:
        print(f"Failed to send report: {results.get('error', 'Unknown error')}")
        return 1


def cmd_costs(args):
    """Show cost information."""
    monitor = AWSCostMonitor()
    
    if args.service:
        # Show service-level costs (returns List[Dict])
        data = monitor.get_service_costs(days=args.days)
        if not data:
            print("No cost data available")
            return 1
        
        # Group by service and sum costs
        totals = defaultdict(float)
        for r in data:
            totals[r['service']] += r['cost']
        
        # Sort descending by cost
        sorted_services = sorted(totals.items(), key=lambda x: x[1], reverse=True)
        
        print(f"\nTop Services (Last {args.days} days)")
        print("=" * 60)
        
        for i, (service, cost) in enumerate(sorted_services[:args.top], 1):
            print(f"{i:2d}. {service:<40} ${cost:>10.2f}")
        
        total = sum(totals.values())
        print("-" * 60)
        print(f"{'TOTAL':<44} ${total:>10.2f}")
        print("=" * 60 + "\n")
    else:
        # Show daily costs (returns List[Dict])
        data = monitor.get_daily_costs(days=args.days)
        if not data:
            print("No cost data available")
            return 1
        
        # Show last N days (max 14)
        display_data = data[-min(args.days, 14):]
        
        print(f"\nDaily Costs (Last {len(display_data)} days)")
        print("=" * 60)
        
        for row in display_data:
            date_str = row['date'] if isinstance(row['date'], str) else row['date'].strftime('%Y-%m-%d')
            print(f"{date_str}  ${row['cost']:>10.2f}")
        
        all_costs = [r['cost'] for r in data]
        avg_cost = sum(all_costs) / len(all_costs) if all_costs else 0
        total_cost = sum(all_costs)
        
        print("-" * 60)
        print(f"{'Average':<12} ${avg_cost:>10.2f}")
        print(f"{'Total':<12} ${total_cost:>10.2f}")
        print("=" * 60 + "\n")
    
    return 0


def cmd_anomalies(args):
    """Detect and show anomalies."""
    monitor = AWSCostMonitor()
    detector = CostAnomalyDetector()
    
    print(f"\nDetecting anomalies (last {args.days} days)...")
    
    data = monitor.get_daily_costs(days=args.days)
    if len(data) < 7:
        print("Insufficient data for anomaly detection (need at least 7 days)")
        return 1
    
    results = detector.detect_anomalies(data)
    insights = detector.get_anomaly_insights(results)
    
    if not insights:
        print("No anomalies detected")
        return 0
    
    print(f"\nFound {len(insights)} anomalies:\n")
    print("=" * 80)
    
    for i, anomaly in enumerate(insights, 1):
        severity_emoji = {
            'critical': '🚨',
            'high': '⚠️',
            'medium': '⚡',
            'low': 'ℹ️'
        }.get(anomaly['severity'], 'ℹ️')
        
        print(f"{i}. {severity_emoji} {anomaly['date']}")
        print(f"   Cost: ${anomaly['cost']:.2f}")
        print(f"   Deviation: {anomaly['deviation_percent']:+.1f}% from previous week")
        print(f"   Severity: {anomaly['severity'].upper()}")
        print(f"   Score: {anomaly['anomaly_score']:.2f}")
        print()
    
    print("=" * 80 + "\n")
    return 0


def cmd_status(args):
    """Show sentinel status."""
    sentinel = CostSentinel(args.config)
    status = sentinel.get_status()
    
    print("\n" + "=" * 60)
    print("AWS COST SENTINEL STATUS")
    print("=" * 60)
    print(f"\nStatus: {status['status'].upper()}")
    print(f"Timestamp: {status['timestamp']}")
    
    print("\nComponents:")
    for component, state in status['components'].items():
        if isinstance(state, dict):
            print(f"  {component}:")
            for sub, sub_state in state.items():
                icon = "✅" if sub_state == 'active' else "❌"
                print(f"    {icon} {sub}: {sub_state}")
        else:
            icon = "✅" if state == 'active' else "❌"
            print(f"  {icon} {component}: {state}")
    
    print("\nConfiguration:")
    for key, value in status['config'].items():
        print(f"  {key}: {value}")
    
    print("=" * 60 + "\n")
    return 0


def cmd_forecast(args):
    """Show cost forecast."""
    monitor = AWSCostMonitor()
    
    print(f"\n🔮 Forecasting costs for next {args.days} days...")
    
    forecast = monitor.get_forecast(days_ahead=args.days)
    
    if forecast:
        print("\n" + "=" * 60)
        print(f"Projected Cost: ${forecast['forecast_cost']:.2f}")
        print(f"Period: {forecast['start_date']} to {forecast['end_date']}")
        print("=" * 60 + "\n")
        return 0
    else:
        print("Could not get forecast data")
        return 1


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='AWS Cost Sentinel - Monitor and alert on AWS costs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s monitor                    # Run monitoring cycle
  %(prog)s report                     # Send daily report
  %(prog)s costs --days 30            # Show daily costs
  %(prog)s costs --service --top 10   # Show top services
  %(prog)s anomalies                  # Detect anomalies
  %(prog)s status                     # Show status
  %(prog)s forecast --days 30         # Show forecast
        """
    )
    
    parser.add_argument(
        '--config',
        default='config.yaml',
        help='Path to configuration file (default: config.yaml)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Monitor command
    parser_monitor = subparsers.add_parser('monitor', help='Run monitoring cycle')
    parser_monitor.set_defaults(func=cmd_monitor)
    
    # Report command
    parser_report = subparsers.add_parser('report', help='Send daily report')
    parser_report.set_defaults(func=cmd_report)
    
    # Costs command
    parser_costs = subparsers.add_parser('costs', help='Show cost information')
    parser_costs.add_argument(
        '--days',
        type=int,
        default=30,
        help='Number of days to show (default: 30)'
    )
    parser_costs.add_argument(
        '--service',
        action='store_true',
        help='Show service-level breakdown'
    )
    parser_costs.add_argument(
        '--top',
        type=int,
        default=10,
        help='Number of top services to show (default: 10)'
    )
    parser_costs.set_defaults(func=cmd_costs)
    
    # Anomalies command
    parser_anomalies = subparsers.add_parser('anomalies', help='Detect anomalies')
    parser_anomalies.add_argument(
        '--days',
        type=int,
        default=30,
        help='Number of days to analyze (default: 30)'
    )
    parser_anomalies.set_defaults(func=cmd_anomalies)
    
    # Status command
    parser_status = subparsers.add_parser('status', help='Show sentinel status')
    parser_status.set_defaults(func=cmd_status)
    
    # Forecast command
    parser_forecast = subparsers.add_parser('forecast', help='Show cost forecast')
    parser_forecast.add_argument(
        '--days',
        type=int,
        default=30,
        help='Number of days to forecast (default: 30)'
    )
    parser_forecast.set_defaults(func=cmd_forecast)
    
    # Parse arguments
    args = parser.parse_args()
    
    # Setup logging
    if args.verbose:
        setup_logger(level='DEBUG')
    else:
        setup_logger(level='INFO')
    
    # Run command
    if hasattr(args, 'func'):
        return args.func(args)
    else:
        parser.print_help()
        return 0


if __name__ == '__main__':
    sys.exit(main())