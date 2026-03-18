#!/bin/bash

# AWS Cost Sentinel - Quick Start Script
# This script helps you get started with AWS Cost Sentinel quickly

set -e

echo "=================================="
echo "AWS Cost Sentinel - Quick Start"
echo "=================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Python is installed
echo -e "${YELLOW}Checking prerequisites...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    echo "Please install Python 3.9 or higher"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo -e "${GREEN}✓ Python ${PYTHON_VERSION} found${NC}"

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo -e "${RED}Error: pip3 is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ pip3 found${NC}"

# Check if AWS CLI is installed (optional but recommended)
if command -v aws &> /dev/null; then
    echo -e "${GREEN}✓ AWS CLI found${NC}"
else
    echo -e "${YELLOW}⚠ AWS CLI not found (optional but recommended)${NC}"
fi

echo ""
echo -e "${YELLOW}Step 1: Creating virtual environment...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${GREEN}✓ Virtual environment already exists${NC}"
fi

echo ""
echo -e "${YELLOW}Step 2: Activating virtual environment...${NC}"
source venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}"

echo ""
echo -e "${YELLOW}Step 3: Installing dependencies...${NC}"
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"

echo ""
echo -e "${YELLOW}Step 4: Setting up configuration...${NC}"

# Copy config files if they don't exist
if [ ! -f "config.yaml" ]; then
    cp config.yaml.example config.yaml
    echo -e "${GREEN}✓ Created config.yaml${NC}"
else
    echo -e "${GREEN}✓ config.yaml already exists${NC}"
fi

if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "${GREEN}✓ Created .env${NC}"
else
    echo -e "${GREEN}✓ .env already exists${NC}"
fi

echo ""
echo -e "${GREEN}=================================="
echo "Setup Complete!"
echo -e "==================================${NC}"
echo ""
echo "Next steps:"
echo ""
echo "1. Configure your AWS credentials:"
echo "   ${YELLOW}aws configure${NC}"
echo ""
echo "2. Edit config.yaml to set your budget thresholds:"
echo "   ${YELLOW}nano config.yaml${NC}"
echo ""
echo "3. (Optional) Set up notifications by editing .env:"
echo "   ${YELLOW}nano .env${NC}"
echo "   Add your Teams/Slack/Discord webhook URLs"
echo ""
echo "4. Test the installation:"
echo "   ${YELLOW}python -m src.sentinel${NC}"
echo ""
echo "5. Or use the CLI:"
echo "   ${YELLOW}python sentinel-cli.py status${NC}"
echo "   ${YELLOW}python sentinel-cli.py costs --days 7${NC}"
echo "   ${YELLOW}python sentinel-cli.py monitor${NC}"
echo ""
echo "For more information, see:"
echo "  - README.md - Main documentation"
echo "  - docs/SETUP_GUIDE.md - Detailed setup instructions"
echo "  - CONTRIBUTING.md - How to contribute"
echo ""
echo -e "${GREEN}Happy monitoring! 🚀${NC}"
echo ""

# Ask if user wants to run a test
read -p "Would you like to test the installation now? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo -e "${YELLOW}Running test...${NC}"
    python -c "from src.sentinel import CostSentinel; s = CostSentinel(); print('✓ Import successful'); status = s.get_status(); print('✓ Status check successful')"
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Test passed!${NC}"
    else
        echo -e "${RED}✗ Test failed. Please check your configuration.${NC}"
    fi
fi

echo ""
echo "To activate the virtual environment in the future, run:"
echo "  ${YELLOW}source venv/bin/activate${NC}"
