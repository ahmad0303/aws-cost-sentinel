"""Tests for AWS Cost Monitor."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from src.core.cost_monitor import AWSCostMonitor


class TestAWSCostMonitor:
    """Test cases for AWSCostMonitor."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration."""
        config = Mock()
        config.get.side_effect = lambda key, default=None: {
            'aws.region': 'us-east-1',
            'monitoring.lookback_days': 30,
            'monitoring.budgets.daily_max': 100.0,
            'monitoring.budgets.weekly_max': 500.0,
            'monitoring.budgets.monthly_max': 2000.0,
            'monitoring.alerts.daily_increase_percent': 50.0,
        }.get(key, default)
        return config
    
    @pytest.fixture
    def mock_ce_client(self):
        """Mock Cost Explorer client."""
        client = Mock()
        return client
    
    @pytest.fixture
    def cost_monitor(self, mock_config, mock_ce_client):
        """Create cost monitor with mocked dependencies."""
        with patch('boto3.client', return_value=mock_ce_client):
            monitor = AWSCostMonitor(mock_config)
            return monitor
    
    def test_initialization(self, cost_monitor, mock_config):
        """Test monitor initialization."""
        assert cost_monitor.config == mock_config
        assert cost_monitor.ce_client is not None
    
    def test_get_daily_costs(self, cost_monitor, mock_ce_client):
        """Test getting daily costs."""
        # Mock response
        mock_response = {
            'ResultsByTime': [
                {
                    'TimePeriod': {'Start': '2024-03-01'},
                    'Total': {'UnblendedCost': {'Amount': '50.00'}}
                },
                {
                    'TimePeriod': {'Start': '2024-03-02'},
                    'Total': {'UnblendedCost': {'Amount': '75.00'}}
                }
            ]
        }
        mock_ce_client.get_cost_and_usage.return_value = mock_response

        data = cost_monitor.get_daily_costs(days=2)

        assert len(data) == 2
        assert 'date' in data[0]
        assert 'cost' in data[0]
        assert data[0]['cost'] == 50.00
        assert data[1]['cost'] == 75.00
    
    def test_check_budget_thresholds_exceeded(self, cost_monitor):
        """Test budget threshold check when exceeded."""
        result = cost_monitor.check_budget_thresholds(150.0, 'daily')
        
        assert result['exceeded'] is True
        assert result['current_cost'] == 150.0
        assert result['threshold'] == 100.0
        assert result['percent_of_budget'] == 150.0
    
    def test_check_budget_thresholds_not_exceeded(self, cost_monitor):
        """Test budget threshold check when not exceeded."""
        result = cost_monitor.check_budget_thresholds(50.0, 'daily')
        
        assert result['exceeded'] is False
        assert result['current_cost'] == 50.0
        assert result['threshold'] == 100.0
        assert result['percent_of_budget'] == 50.0
    
    def test_detect_cost_spikes(self, cost_monitor):
        """Test cost spike detection."""
        # Create test data with a spike
        data = [
            {'date': '2024-03-01', 'cost': 50.0},
            {'date': '2024-03-02', 'cost': 55.0},
            {'date': '2024-03-03', 'cost': 150.0},
            {'date': '2024-03-04', 'cost': 60.0},
            {'date': '2024-03-05', 'cost': 58.0},
        ]

        spikes = cost_monitor.detect_cost_spikes(data)

        assert len(spikes) > 0
        spike = spikes[0]
        assert spike['cost'] == 150.0
        assert spike['percent_change'] > 50
    
    def test_get_top_services(self, cost_monitor, mock_ce_client):
        """Test getting top services."""
        # Mock response
        mock_response = {
            'ResultsByTime': [
                {
                    'TimePeriod': {'Start': '2024-03-01'},
                    'Groups': [
                        {
                            'Keys': ['EC2'],
                            'Metrics': {'UnblendedCost': {'Amount': '100.00'}}
                        },
                        {
                            'Keys': ['S3'],
                            'Metrics': {'UnblendedCost': {'Amount': '50.00'}}
                        }
                    ]
                }
            ]
        }
        mock_ce_client.get_cost_and_usage.return_value = mock_response
        
        top_services = cost_monitor.get_top_services(days=7, top_n=5)
        
        assert len(top_services) == 2
        assert top_services[0]['service'] == 'EC2'
        assert top_services[0]['total_cost'] == 100.0
        assert top_services[1]['service'] == 'S3'
        assert top_services[1]['total_cost'] == 50.0
