# Contributing to AWS Cost Sentinel

Thank you for your interest in contributing to AWS Cost Sentinel! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for all contributors.

## How to Contribute

### Reporting Bugs

If you find a bug, please create an issue with:

- **Clear title** describing the bug
- **Steps to reproduce** the issue
- **Expected behavior** vs actual behavior
- **Environment details** (OS, Python version, AWS region)
- **Logs or error messages** if applicable

### Suggesting Features

Feature requests are welcome! Please create an issue with:

- **Clear description** of the feature
- **Use case** explaining why it's needed
- **Proposed implementation** (if you have ideas)

### Pull Requests

1. **Fork the repository**
   ```bash
   git clone https://github.com/ahmad0303/aws-cost-sentinel.git
   cd aws-cost-sentinel
   ```

2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make your changes**
   - Write clean, readable code
   - Follow PEP 8 style guidelines
   - Add tests for new features
   - Update documentation as needed

4. **Run tests**
   ```bash
   # Install dev dependencies
   pip install pytest pytest-cov black flake8 mypy
   
   # Run tests
   pytest tests/ -v
   
   # Check code formatting
   black --check src
   
   # Run linter
   flake8 src
   ```

5. **Commit your changes**
   ```bash
   git add .
   git commit -m "Add feature: your feature description"
   ```

6. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

7. **Create a Pull Request**
   - Go to the original repository
   - Click "New Pull Request"
   - Select your fork and branch
   - Describe your changes clearly

## Development Setup

### Local Development

```bash
# Clone your fork
git clone https://github.com/ahmad0303/aws-cost-sentinel.git
cd aws-cost-sentinel

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # If available

# Copy configuration
cp config.yaml.example config.yaml
cp .env.example .env

# Edit configurations
nano config.yaml
nano .env
```

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/test_cost_monitor.py -v

# Run specific test
pytest tests/test_cost_monitor.py::TestAWSCostMonitor::test_initialization -v
```

### Code Style

We follow PEP 8 with some modifications:

- **Line length**: 100 characters (not 79)
- **String quotes**: Use double quotes for strings
- **Imports**: Organize in groups (standard library, third-party, local)
- **Docstrings**: Use Google-style docstrings

Example:
```python
"""Module description.

This module does X, Y, and Z.
"""

import os
from typing import Dict, List

import boto3
import pandas as pd

from src.utils.logger import get_logger


class MyClass:
    """Short description.
    
    Longer description explaining what this class does and how to use it.
    
    Attributes:
        attr1: Description of attr1
        attr2: Description of attr2
    """
    
    def my_method(self, param1: str, param2: int = 10) -> Dict:
        """Short description of the method.
        
        Args:
            param1: Description of param1
            param2: Description of param2 (default: 10)
            
        Returns:
            Description of return value
            
        Raises:
            ValueError: When param2 is negative
        """
        pass
```

### Type Hints

Use type hints for all function parameters and return values:

```python
from typing import Dict, List, Optional

def process_costs(
    costs: List[float],
    threshold: float,
    config: Optional[Dict] = None
) -> Dict[str, float]:
    """Process cost data."""
    pass
```

## Project Structure

```
aws-cost-sentinel/
├── src/                    # Source code
│   ├── core/              # Core monitoring logic
│   ├── ml/                # Machine learning models
│   ├── notifications/     # Notification channels
│   └── utils/             # Utility functions
├── tests/                 # Test files
├── deployment/            # Deployment scripts
├── docs/                  # Documentation
├── examples/              # Example scripts
└── config.yaml           # Configuration file
```

## Adding New Features

### Adding a New Notification Channel

1. Create a new file in `src/notifications/`
2. Implement the notifier class with standard methods:
   - `send_message()`
   - `send_cost_alert()`
   - `send_daily_summary()`
   - `send_anomaly_alert()`
3. Register in `NotificationManager`
4. Add configuration options to `config.yaml`
5. Write tests
6. Update documentation

### Adding a New Cost Analysis Feature

1. Add method to `AWSCostMonitor` class
2. Write comprehensive docstrings
3. Add unit tests
4. Update CLI if needed
5. Document in README

## Testing Guidelines

- **Write tests for all new features**
- **Aim for >80% code coverage**
- **Use mocks for AWS API calls**
- **Test edge cases and error conditions**
- **Keep tests fast and independent**

Example test:
```python
import pytest
from unittest.mock import Mock, patch

def test_my_feature():
    """Test that my feature works correctly."""
    # Arrange
    monitor = AWSCostMonitor()
    
    # Act
    result = monitor.my_feature()
    
    # Assert
    assert result['success'] is True
    assert 'data' in result
```

## Documentation

- Update README.md for user-facing changes
- Update docstrings for code changes
- Add examples for new features
- Keep CHANGELOG.md updated

## Release Process

1. Update version in `setup.py`
2. Update CHANGELOG.md
3. Create a pull request to main
4. After merge, create a GitHub release
5. CI/CD will automatically deploy

## Questions?

- Open an issue for questions
- Join discussions on GitHub Discussions
- Check existing issues and PRs first

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to AWS Cost Sentinel! 🎉
