#!/bin/bash

set -e

echo "================================"
echo "AWS Cost Sentinel - Deployment"
echo "================================"

# Configuration
FUNCTION_NAME="${LAMBDA_FUNCTION_NAME:-aws-cost-sentinel}"
RUNTIME="python3.11"
HANDLER="lambda_handler.lambda_handler"
ROLE_ARN="${LAMBDA_ROLE_ARN}"
REGION="${AWS_REGION:-eu-west-1}"
S3_BUCKET="${DEPLOY_S3_BUCKET:-}"  # Set this or we auto-create one

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}✓ $1${NC}"; }
log_warn()  { echo -e "${YELLOW}⚠ $1${NC}"; }
log_err()   { echo -e "${RED}✗ $1${NC}"; }
log_step()  { echo -e "\n${CYAN}▸ $1${NC}"; }

# ─────────────────────────────────────────────
# 1. PREREQUISITES
# ─────────────────────────────────────────────
log_step "Checking prerequisites..."

if [ -z "$ROLE_ARN" ]; then
    log_err "LAMBDA_ROLE_ARN not set"
    echo "  export LAMBDA_ROLE_ARN=arn:aws:iam::YOUR_ACCOUNT:role/YOUR_ROLE"
    exit 1
fi

for cmd in aws python3; do
    if ! command -v $cmd &>/dev/null; then
        log_err "$cmd not installed"
        exit 1
    fi
done

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text --region "$REGION" 2>/dev/null)
if [ -z "$ACCOUNT_ID" ]; then
    log_err "AWS credentials not configured or invalid"
    exit 1
fi

log_info "Prerequisites OK (Account: $ACCOUNT_ID, Region: $REGION)"

# ─────────────────────────────────────────────
# 2. BUILD SLIM DEPLOYMENT PACKAGE
# ─────────────────────────────────────────────
log_step "Building deployment package..."

rm -rf build/ aws-cost-sentinel.zip

mkdir -p build

# Copy only what Lambda needs
cp -r src build/
cp lambda_handler.py build/
cp config.yaml build/ 2>/dev/null || true
cp requirements.txt build/

cd build

log_step "Installing dependencies (slim mode)..."

# ── KEY FIX: Exclude bloated packages Lambda doesn't need ──
# Create a filtered requirements file
python3 << 'PYEOF'
import re

# Everything in Lambda runtime OR dev-only OR not needed at runtime
EXCLUDE = {
    # Already in Lambda runtime
    'boto3', 'botocore', 's3transfer', 'jmespath', 'urllib3',

    # Dev/test tools — NEVER deploy these
    'pytest', '_pytest', 'moto', 'mypy', 'mypyc', 'black',
    'coverage', 'ruff', 'flake8', 'tox', 'pre_commit',
    'responses', 'pytest_cov', 'pytest_asyncio', 'pluggy',
    'iniconfig', 'exceptiongroup', 'tomli', 'pathspec',
    'platformdirs', 'packaging',

    # Heavy data science — not needed for cost monitoring
    'numpy', 'pandas', 'scipy', 'sklearn', 'scikit_learn',
    'matplotlib', 'pyarrow', 'openpyxl',

    # Heavy native libs
    'cryptography', 'grpcio', 'grpcio_tools', 'protobuf',

    # Build tools
    'setuptools', 'pip', 'wheel', 'pkg_resources',

    # Misc not needed
    'docutils', 'pytz', 'werkzeug', 'joblib',
}

filtered = []
with open('requirements.txt', 'r') as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        # Extract package name (before any version specifier)
        pkg = re.split(r'[>=<!\[]', line)[0].strip().lower().replace('-', '_')
        if pkg not in EXCLUDE:
            filtered.append(line)
        else:
            print(f"  Skipping {pkg} (in Lambda runtime or not needed)")

with open('requirements-lambda.txt', 'w') as f:
    f.write('\n'.join(filtered))

print(f"\n  Kept {len(filtered)} packages, excluded {len(EXCLUDE)} bloated ones")
PYEOF

# Install only the filtered deps
pip install -r requirements-lambda.txt -t . \
    --upgrade \
    --quiet \
    --no-cache-dir \
    --platform manylinux2014_x86_64 \
    --implementation cp \
    --python-version 3.11 \
    --only-binary=:all: 2>/dev/null || \
pip install -r requirements-lambda.txt -t . \
    --upgrade \
    --quiet \
    --no-cache-dir

log_step "Stripping unnecessary files..."

# Remove test/doc dirs
find . -type d \( -name "tests" -o -name "test" -o -name "docs" \
    -o -name "examples" -o -name "samples" -o -name "benchmarks" \) \
    -exec rm -rf {} + 2>/dev/null || true

# Remove caches and metadata
find . -type d \( -name "__pycache__" -o -name "*.dist-info" \
    -o -name "*.egg-info" -o -name ".pytest_cache" \) \
    -exec rm -rf {} + 2>/dev/null || true

# Remove compiled/binary cruft
find . \( -name "*.pyc" -o -name "*.pyo" -o -name "*.pyd" \
    -o -name "*.DS_Store" -o -name "*.gitignore" \) -delete 2>/dev/null || true

# Strip debug symbols from .so files (can save 50%+ on native extensions)
find . -name "*.so" -type f -exec strip --strip-unneeded {} \; 2>/dev/null || true

# NUCLEAR: Remove everything that should never be in a Lambda package
# Even if the filter missed them as transitive deps
rm -rf \
    scipy* sklearn* scikit_learn* numpy* \
    moto* _pytest* pytest* mypy* mypyc* \
    coverage* black* ruff* flake8* \
    botocore* boto3* s3transfer* awscli* \
    cryptography* grpcio* protobuf* \
    docutils* werkzeug* joblib* \
    typing_extensions* pytz* \
    responses* pluggy* iniconfig* \
    exceptiongroup* tomli* pathspec* \
    platformdirs* packaging* \
    bin/ \
    2>/dev/null || true

cd ..

# Create zip
log_step "Creating ZIP archive..."

python3 << 'PYEOF'
import zipfile, os

def zipdir(path, ziph):
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in {
            '.git', '__pycache__', '.pytest_cache', 'tests', 'test',
            '*.dist-info', '*.egg-info'
        }]
        for f in files:
            if f.endswith(('.pyc', '.pyo', '.DS_Store')):
                continue
            fp = os.path.join(root, f)
            arcname = os.path.relpath(fp, path)
            ziph.write(fp, arcname, compress_type=zipfile.ZIP_DEFLATED)

with zipfile.ZipFile('aws-cost-sentinel.zip', 'w', zipfile.ZIP_DEFLATED) as z:
    zipdir('build', z)

size_mb = os.path.getsize('aws-cost-sentinel.zip') / (1024 * 1024)
print(f"  Package size: {size_mb:.1f} MB")

if size_mb > 250:
    print("  ERROR: Exceeds Lambda 250MB unzipped limit!")
    exit(1)
PYEOF

PACKAGE_SIZE=$(stat -c%s "aws-cost-sentinel.zip" 2>/dev/null || stat -f%z "aws-cost-sentinel.zip" 2>/dev/null)
PACKAGE_MB=$((PACKAGE_SIZE / 1048576))

log_info "Package built: ${PACKAGE_MB}MB"

# ─────────────────────────────────────────────
# 3. UPLOAD (direct or via S3)
# ─────────────────────────────────────────────
log_step "Deploying to Lambda..."

DIRECT_UPLOAD_LIMIT=52428800  # 50MB

if [ "$PACKAGE_SIZE" -gt "$DIRECT_UPLOAD_LIMIT" ]; then
    log_warn "Package > 50MB — uploading via S3"

    # Auto-create S3 bucket if not provided
    if [ -z "$S3_BUCKET" ]; then
        S3_BUCKET="cost-sentinel-deploy-${ACCOUNT_ID}-${REGION}"
        log_step "Creating S3 bucket: $S3_BUCKET"

        if [ "$REGION" = "us-east-1" ]; then
            aws s3api create-bucket \
                --bucket "$S3_BUCKET" \
                --region "$REGION" 2>/dev/null || true
        else
            aws s3api create-bucket \
                --bucket "$S3_BUCKET" \
                --region "$REGION" \
                --create-bucket-configuration LocationConstraint="$REGION" \
                2>/dev/null || true
        fi
    fi

    S3_KEY="deployments/${FUNCTION_NAME}/$(date +%Y%m%d-%H%M%S).zip"

    log_step "Uploading to s3://${S3_BUCKET}/${S3_KEY}..."
    aws s3 cp aws-cost-sentinel.zip "s3://${S3_BUCKET}/${S3_KEY}" \
        --region "$REGION"

    log_info "Uploaded to S3"

    # Check if function exists
    if aws lambda get-function --function-name "$FUNCTION_NAME" --region "$REGION" &>/dev/null; then
        log_step "Updating existing function..."
        aws lambda update-function-code \
            --function-name "$FUNCTION_NAME" \
            --s3-bucket "$S3_BUCKET" \
            --s3-key "$S3_KEY" \
            --region "$REGION" >/dev/null
    else
        log_step "Creating new function..."
        aws lambda create-function \
            --function-name "$FUNCTION_NAME" \
            --runtime "$RUNTIME" \
            --role "$ROLE_ARN" \
            --handler "$HANDLER" \
            --code S3Bucket="$S3_BUCKET",S3Key="$S3_KEY" \
            --timeout 300 \
            --memory-size 512 \
            --region "$REGION" >/dev/null
    fi

else
    log_info "Package under 50MB — direct upload"

    if aws lambda get-function --function-name "$FUNCTION_NAME" --region "$REGION" &>/dev/null; then
        log_step "Updating existing function..."
        aws lambda update-function-code \
            --function-name "$FUNCTION_NAME" \
            --zip-file fileb://aws-cost-sentinel.zip \
            --region "$REGION" >/dev/null
    else
        log_step "Creating new function..."
        aws lambda create-function \
            --function-name "$FUNCTION_NAME" \
            --runtime "$RUNTIME" \
            --role "$ROLE_ARN" \
            --handler "$HANDLER" \
            --zip-file fileb://aws-cost-sentinel.zip \
            --timeout 300 \
            --memory-size 512 \
            --region "$REGION" >/dev/null
    fi
fi

log_info "Lambda function deployed"

# ─────────────────────────────────────────────
# 4. WAIT FOR FUNCTION TO BE ACTIVE
# ─────────────────────────────────────────────
log_step "Waiting for function to become active..."

for i in $(seq 1 30); do
    STATE=$(aws lambda get-function-configuration \
        --function-name "$FUNCTION_NAME" \
        --region "$REGION" \
        --query 'State' --output text 2>/dev/null)
    if [ "$STATE" = "Active" ]; then
        log_info "Function is active"
        break
    fi
    sleep 2
done

# Update config (separate call, after function is active)
aws lambda update-function-configuration \
    --function-name "$FUNCTION_NAME" \
    --timeout 300 \
    --memory-size 512 \
    --region "$REGION" >/dev/null 2>&1 || true

# ─────────────────────────────────────────────
# 5. EVENTBRIDGE SCHEDULE
# ─────────────────────────────────────────────
log_step "Configuring EventBridge schedule..."

RULE_NAME="${FUNCTION_NAME}-daily"
LAMBDA_ARN="arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:${FUNCTION_NAME}"

aws events put-rule \
    --name "$RULE_NAME" \
    --schedule-expression "cron(0 9 * * ? *)" \
    --description "AWS Cost Sentinel - daily at 9 AM UTC" \
    --region "$REGION" >/dev/null

# Add permission (ignore if already exists)
aws lambda add-permission \
    --function-name "$FUNCTION_NAME" \
    --statement-id "${RULE_NAME}-invoke" \
    --action "lambda:InvokeFunction" \
    --principal events.amazonaws.com \
    --source-arn "arn:aws:events:${REGION}:${ACCOUNT_ID}:rule/${RULE_NAME}" \
    --region "$REGION" >/dev/null 2>&1 || true

# Add target (Windows/Git Bash safe — use local file, not mktemp)
TARGETS_FILE="./eb_targets.json"
echo "[{\"Id\":\"1\",\"Arn\":\"${LAMBDA_ARN}\",\"Input\":\"{\\\"action\\\":\\\"daily_report\\\"}\"}]" > "$TARGETS_FILE"

aws events put-targets \
    --rule "$RULE_NAME" \
    --targets "file://${TARGETS_FILE}" \
    --region "$REGION" >/dev/null

rm -f "$TARGETS_FILE"

log_info "Schedule configured: daily at 9 AM UTC"

# ─────────────────────────────────────────────
# 6. SMOKE TEST
# ─────────────────────────────────────────────
log_step "Running smoke test..."

RESPONSE_FILE="./lambda_response.json"
aws lambda invoke \
    --function-name "$FUNCTION_NAME" \
    --payload '{"action":"status"}' \
    --region "$REGION" \
    "$RESPONSE_FILE" >/dev/null 2>&1 || true

if [ -f "$RESPONSE_FILE" ] && [ -s "$RESPONSE_FILE" ]; then
    log_info "Smoke test response:"
    python3 -m json.tool "$RESPONSE_FILE" 2>/dev/null || cat "$RESPONSE_FILE"
else
    log_warn "No response (function may still be initializing)"
fi
rm -f "$RESPONSE_FILE"

# ─────────────────────────────────────────────
# 7. CLEANUP
# ─────────────────────────────────────────────
rm -rf build/

# ─────────────────────────────────────────────
# DONE
# ─────────────────────────────────────────────
echo ""
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo -e "${GREEN}  Deployment Complete!${NC}"
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo ""
echo "  Function:  $FUNCTION_NAME"
echo "  Region:    $REGION"
echo "  Runtime:   $RUNTIME"
echo "  Package:   ${PACKAGE_MB}MB"
echo "  Schedule:  Daily at 9 AM UTC"
echo ""
echo "  Test:  aws lambda invoke --function-name $FUNCTION_NAME \\"
echo "           --payload '{\"action\":\"monitor\"}' --region $REGION out.json"
echo ""
echo "  Logs:  aws logs tail /aws/lambda/$FUNCTION_NAME --follow --region $REGION"
echo ""