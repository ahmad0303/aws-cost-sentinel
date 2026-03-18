"""Pytest configuration and fixtures."""

import pytest
import os
import sys
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture
def sample_cost_data():
    """Sample daily cost data for testing (List[Dict])."""
    base_date = datetime.now() - timedelta(days=30)
    data = []
    for i in range(30):
        dt = base_date + timedelta(days=i)
        cost = 50 + (i % 7) * 10 + (5 if i % 3 == 0 else 0)
        data.append({
            'date': dt.strftime('%Y-%m-%d'),
            'cost': float(cost)
        })
    return data


@pytest.fixture
def sample_service_data():
    """Sample service-level cost data for testing (List[Dict])."""
    services = ['EC2', 'RDS', 'S3', 'Lambda', 'CloudWatch']
    base_date = datetime.now() - timedelta(days=7)
    data = []

    for i in range(7):
        dt = base_date + timedelta(days=i)
        date_str = dt.strftime('%Y-%m-%d')
        day = dt.day

        for service in services:
            cost = {
                'EC2': 100 + (day % 5) * 10,
                'RDS': 75 + (day % 3) * 5,
                'S3': 30 + (day % 2) * 2,
                'Lambda': 15,
                'CloudWatch': 5
            }[service]

            data.append({
                'date': date_str,
                'service': service,
                'cost': float(cost)
            })

    return data


@pytest.fixture
def mock_aws_credentials():
    """Mock AWS credentials."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'