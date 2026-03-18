# AWS Cost Sentinel - Complete Setup Guide

This guide will walk you through setting up AWS Cost Sentinel from scratch.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [AWS Setup](#aws-setup)
3. [Local Installation](#local-installation)
4. [Notification Setup](#notification-setup)
5. [Lambda Deployment](#lambda-deployment)
6. [Testing](#testing)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required

- **AWS Account** with billing access
- **Python 3.9+** installed
- **AWS CLI** configured
- **Git** for cloning the repository

### Optional

- **Docker** for containerized deployment
- **Slack workspace** (for Slack notifications)
- **Discord server** (for Discord notifications)

---

## AWS Setup

### Step 1: Enable Cost Explorer API

1. Log in to AWS Console
2. Go to **Billing and Cost Management**
3. Navigate to **Cost Explorer**
4. Click **Enable Cost Explorer** if not already enabled
5. Wait 24 hours for initial data to populate

### Step 2: Create IAM Role for Lambda

1. Go to **IAM Console**
2. Click **Roles** → **Create Role**
3. Select **Lambda** as the trusted entity
4. Click **Next: Permissions**
5. Create a custom policy with these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ce:GetCostAndUsage",
        "ce:GetCostForecast",
        "ce:GetDimensionValues"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```

6. Name the role `AWSCostSentinelRole`
7. Copy the Role ARN (you'll need it later)

### Step 3: Configure AWS Credentials

**Option A: AWS CLI (Recommended for local testing)**

```bash
aws configure
```

Enter your Access Key, Secret Key, Region, and output format.

**Option B: Environment Variables**

```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_REGION=us-east-1
```

---

## Local Installation

### Step 1: Clone Repository

```bash
git clone https://github.com/ahmad0303/aws-cost-sentinel.git
cd aws-cost-sentinel
```

### Step 2: Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows (Git Bash / MINGW64):
source venv/Scripts/activate
# On Windows (CMD):
venv\Scripts\activate
```

### Step 3: Install Dependencies

This project uses **two requirements files**. You need both for local development:

| File | What's in it | Why separate |
|------|-------------|--------------|
| `requirements.txt` | Runtime deps — notifications (slack-sdk, discord-webhook, pymsteams), config (pyyaml, python-dotenv), date handling | These go into the Lambda deployment package |
| `requirements-dev.txt` | **boto3**, pytest, moto, black, flake8, mypy | `boto3` is pre-installed in Lambda. Keeping it out of `requirements.txt` makes the deployment package smaller. Dev/test tools are never deployed. |

```bash
# Install BOTH files for local development
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

> **⚠️ Important:** If you only install `requirements.txt`, you will get `ModuleNotFoundError: No module named 'boto3'` when running the project locally. Always install both files.

### Step 4: Configure the Application

```bash
# Copy configuration templates
cp config.yaml.example config.yaml
cp .env.example .env
```

**Edit `config.yaml`:**

```yaml
# Set your budget thresholds
monitoring:
  budgets:
    daily_max: 100.0      # Your daily budget
    weekly_max: 500.0     # Your weekly budget
    monthly_max: 2000.0   # Your monthly budget

# Configure anomaly detection
anomaly_detection:
  enabled: true
  sensitivity: medium     # low, medium, or high
```

**Edit `.env`:**

```bash
# AWS Configuration
AWS_REGION=us-east-1

# Slack (optional)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Discord (optional)
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR/WEBHOOK/URL

# Teams (optional)
TEAMS_WEBHOOK_URL=https://your-org.webhook.office.com/webhookb2/YOUR_WEBHOOK_URL
```

### Step 5: Test the Installation

```bash
# Run a test monitoring cycle
python -m src.sentinel

# Check status
python sentinel_cli.py status
```

---

## Notification Setup

### Microsoft Teams Integration

1. Open **Microsoft Teams**
2. Go to the channel where you want to receive alerts
3. Click the **⋯ (More options)** next to the channel name
4. Select **Workflows** or **Connectors** (depending on your Teams version)
5. Choose **Incoming Webhook**
6. Click **Add**
7. Give it a name (e.g., `AWS Cost Alerts`)
8. Copy the generated **Webhook URL**
9. Add the webhook URL to your `.env` file:
    ```bash
    TEAMS_WEBHOOK_URL=https://outlook.office.com/webhook/xxxxxxxxxxxxxxxxxxxxxxxx
    ```
10. Enable Teams notifications in config.yaml:
    ```yaml
   notifications:
     teams:
       enabled: true
   ```

### Slack Integration

1. Go to your Slack workspace
2. Create a new channel (e.g., `#aws-costs`)
3. Add an Incoming Webhook:
   - Go to **Slack Apps** → **Incoming Webhooks**
   - Click **Add to Slack**
   - Select your channel
   - Copy the Webhook URL
4. Add to `.env`:
   ```bash
   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX
   ```
5. Enable in `config.yaml`:
   ```yaml
   notifications:
     slack:
       enabled: true
       channel: "#aws-costs"
   ```

### Discord Integration

1. Open your Discord server
2. Go to **Server Settings** → **Integrations**
3. Click **Webhooks** → **New Webhook**
4. Select a channel and copy the Webhook URL
5. Add to `.env`:
   ```bash
   DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/123456789/XXXXXXXXXXXXXXXXXXXX
   ```
6. Enable in `config.yaml`:
   ```yaml
   notifications:
     discord:
       enabled: true
   ```

### Email via AWS SES

1. Verify your email address in AWS SES:
   - Go to **SES Console**
   - Click **Email Addresses** → **Verify a New Email Address**
   - Enter your email and verify
2. Configure in `config.yaml`:
   ```yaml
   notifications:
     email:
       enabled: true
       sender: alerts@yourcompany.com
       recipients:
         - you@yourcompany.com
   ```

---

## Lambda Deployment

### Step 1: Prepare Environment

```bash
# Set your Lambda role ARN (from Step 2 of AWS Setup)
export LAMBDA_ROLE_ARN=arn:aws:iam::YOUR_ACCOUNT_ID:role/AWSCostSentinelRole

# Optional: Set custom function name
export LAMBDA_FUNCTION_NAME=aws-cost-sentinel

# Set AWS region
export AWS_REGION=us-east-1
```

### Step 2: Deploy

```bash
# Make deployment script executable
chmod +x deployment/deploy.sh

# Run deployment
./deployment/deploy.sh

# Add env vars to Lambda directly:
aws lambda update-function-configuration \
    --function-name aws-cost-sentinel \
    --region eu-west-1 \
    --environment "Variables={DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_ACTUAL_URL_HERE}"
```

The deploy script will:
- Package only `requirements.txt` dependencies (runtime deps)
- Automatically exclude boto3, dev tools, and heavy packages
- Create/update the Lambda function
- Set up daily EventBridge schedule (9 AM UTC)

> **Note:** `boto3` is NOT included in the Lambda package because AWS Lambda already provides it. This keeps the package small and under Lambda's size limits.

### Step 3: Verify Deployment

```bash
# Check function status
aws lambda get-function --function-name aws-cost-sentinel

# View logs
aws logs tail /aws/lambda/aws-cost-sentinel --follow

# Test invoke
aws lambda invoke \
  --function-name aws-cost-sentinel \
  --payload '{"action":"status"}' \
  response.json

cat response.json | python -m json.tool
```

### Step 4: Configure Schedule

By default, the function runs daily at 9 AM UTC. To change:

```bash
# Update EventBridge rule
aws events put-rule \
  --name aws-cost-sentinel-daily \
  --schedule-expression "cron(0 12 * * ? *)"  # 12 PM UTC
```

---

## Testing

### Install Dependencies

```bash
# You need BOTH requirements files for testing
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Run Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=src --cov-report=html

# Lint checks
flake8 src
black --check src
mypy src --ignore-missing-imports
```

### Test Notifications

```bash
# Test Slack
python -c "
from src.notifications.slack import SlackNotifier
notifier = SlackNotifier()
notifier.send_message('Test from AWS Cost Sentinel')
"

# Test Discord
python -c "
from src.notifications.discord import DiscordNotifier
notifier = DiscordNotifier()
notifier.send_message('Test from AWS Cost Sentinel')
"
```

### Test Lambda Function

```bash
# Test monitoring
aws lambda invoke \
  --function-name aws-cost-sentinel \
  --payload '{"action":"monitor"}' \
  response.json

# Test daily report
aws lambda invoke \
  --function-name aws-cost-sentinel \
  --payload '{"action":"daily_report"}' \
  response.json
```

---

## Troubleshooting

### Common Issues

#### "ModuleNotFoundError: No module named 'boto3'"

**Solution:** You only installed `requirements.txt`. For local development you also need:
```bash
pip install -r requirements-dev.txt
```

#### "Cost Explorer API not enabled"

**Solution:** Enable Cost Explorer in AWS Console and wait 24 hours.

#### "Insufficient permissions"

**Solution:** Verify your IAM role has the required permissions (see AWS Setup).

#### "No cost data available"

**Solution:**
- Cost Explorer requires 24 hours after enabling
- Check if your account has any spending
- Verify AWS credentials are correct

#### "Slack/Discord webhook not working"

**Solution:**
- Test webhook URL manually with curl
- Verify URL is correctly set in `.env`
- Check that notifications are enabled in `config.yaml`

#### "Lambda deployment fails"

**Solution:**
- Verify `LAMBDA_ROLE_ARN` is set correctly
- Check AWS CLI is configured with correct credentials
- Ensure you have permissions to create Lambda functions

#### "Package size too large for Lambda"

**Solution:**
- The deployment script removes unnecessary files automatically
- Consider using Lambda layers for heavy dependencies
- Remove unused notification channels

### Debug Mode

Enable debug logging:

```yaml
# In config.yaml
logging:
  level: DEBUG
```

### Get Help

- Check logs: `aws logs tail /aws/lambda/aws-cost-sentinel`
- Review CloudWatch: Go to Lambda → Monitoring → View logs
- Open an issue: [GitHub Issues](https://github.com/ahmad0303/aws-cost-sentinel/issues)

---

## Next Steps

Once deployed:

1. **Monitor for 7 days** to build historical data for anomaly detection
2. **Adjust thresholds** in `config.yaml` based on your actual spending
3. **Customize alerts** for your team's needs
4. **Set up multiple environments** (dev, staging, prod) with different configs

---

## Support

Need help?

- 📖 [Read the full documentation](https://github.com/ahmad0303/aws-cost-sentinel)
- 🐛 [Report issues](https://github.com/ahmad0303/aws-cost-sentinel/issues)