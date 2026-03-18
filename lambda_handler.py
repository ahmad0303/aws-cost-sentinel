"""AWS Lambda handler for Cost Sentinel."""

import json
import os
import sys

# Add src directory to path for Lambda
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.sentinel import CostSentinel
from src.utils.logger import get_logger


logger = get_logger(__name__)


def lambda_handler(event, context):
    """AWS Lambda handler function.
    
    Args:
        event: Lambda event object
        context: Lambda context object
        
    Returns:
        Response dictionary
    """
    logger.info(f"Lambda invoked with event: {json.dumps(event)}")
    
    try:
        # Initialize sentinel
        sentinel = CostSentinel(config_path='/var/task/config.yaml')
        
        # Determine action from event
        action = event.get('action', 'monitor')
        
        if action == 'monitor':
            # Run monitoring cycle
            results = sentinel.run_monitoring_cycle()
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'success': True,
                    'message': 'Monitoring cycle completed',
                    'results': results
                })
            }
        
        elif action == 'daily_report':
            # Send daily report
            results = sentinel.send_daily_report()
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'success': results['success'],
                    'message': 'Daily report sent',
                    'results': results
                })
            }
        
        elif action == 'status':
            # Get status
            status = sentinel.get_status()
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'success': True,
                    'status': status
                })
            }
        
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'success': False,
                    'message': f'Unknown action: {action}'
                })
            }
    
    except Exception as e:
        logger.error(f"Lambda execution error: {str(e)}", exc_info=True)
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'message': f'Error: {str(e)}'
            })
        }


# For testing locally
if __name__ == "__main__":
    # Test event
    test_event = {
        'action': 'monitor'
    }
    
    response = lambda_handler(test_event, None)
    print(json.dumps(response, indent=2))
