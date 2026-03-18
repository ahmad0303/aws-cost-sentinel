.PHONY: help install test lint format clean deploy docker run

# Default target
help:
	@echo "AWS Cost Sentinel - Development Commands"
	@echo ""
	@echo "Available targets:"
	@echo "  make install    - Install dependencies"
	@echo "  make test       - Run tests"
	@echo "  make lint       - Run linters"
	@echo "  make format     - Format code"
	@echo "  make clean      - Clean build artifacts"
	@echo "  make deploy     - Deploy to AWS Lambda"
	@echo "  make docker     - Build Docker image"
	@echo "  make run        - Run locally"
	@echo "  make coverage   - Run tests with coverage"
	@echo "  make docs       - Build documentation"

# Install dependencies
install:
	pip install --upgrade pip
	pip install -r requirements.txt
	@echo "✓ Dependencies installed"

# Install dev dependencies
install-dev: install
	pip install pytest pytest-cov black flake8 mypy
	@echo "✓ Dev dependencies installed"

# Run tests
test:
	pytest tests/ -v

# Run tests with coverage
coverage:
	pytest tests/ --cov=src --cov-report=html --cov-report=term
	@echo "✓ Coverage report generated in htmlcov/"

# Lint code
lint:
	@echo "Running flake8..."
	flake8 src --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 src --count --exit-zero --max-complexity=10 --max-line-length=100 --statistics
	@echo "Running mypy..."
	mypy src --ignore-missing-imports || true

# Format code
format:
	@echo "Formatting with black..."
	black src tests
	@echo "✓ Code formatted"

# Clean build artifacts
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name .coverage -delete
	rm -rf build/ dist/ *.egg-info
	rm -f aws-cost-sentinel.zip
	@echo "✓ Cleaned build artifacts"

# Deploy to Lambda
deploy:
	@if [ -z "$$LAMBDA_ROLE_ARN" ]; then \
		echo "Error: LAMBDA_ROLE_ARN environment variable not set"; \
		exit 1; \
	fi
	chmod +x deployment/deploy.sh
	./deployment/deploy.sh

# Build Docker image
docker:
	docker build -t aws-cost-sentinel:latest .
	@echo "✓ Docker image built: aws-cost-sentinel:latest"

# Run Docker container
docker-run:
	docker-compose up

# Run locally
run:
	python -m src.sentinel

# Run CLI
cli:
	python sentinel-cli.py status

# Monitor costs
monitor:
	python sentinel-cli.py monitor

# Show costs
costs:
	python sentinel-cli.py costs --days 30

# Detect anomalies
anomalies:
	python sentinel-cli.py anomalies

# Send report
report:
	python sentinel-cli.py report

# Build documentation
docs:
	@echo "Documentation available in docs/ and README.md"

# Quick start
quick-start:
	chmod +x quick-start.sh
	./quick-start.sh

# Check everything before commit
check: format lint test
	@echo "✓ All checks passed!"
