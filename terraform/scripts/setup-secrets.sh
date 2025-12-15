#!/bin/bash
# Setup secrets in Google Secret Manager before Terraform deployment
# Run this script first: ./setup-secrets.sh

set -e

echo "================================"
echo "Pattern Miner - Secret Setup"
echo "================================"
echo

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "Error: gcloud CLI not found. Please install Google Cloud SDK."
    exit 1
fi

# Get project ID
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT_ID" ]; then
    echo "Error: No GCP project set. Run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo "Project: $PROJECT_ID"
echo

# Function to create or update secret
create_or_update_secret() {
    local SECRET_NAME=$1
    local SECRET_DESC=$2

    echo "Checking secret: $SECRET_NAME"

    # Check if secret exists
    if gcloud secrets describe "$SECRET_NAME" --project="$PROJECT_ID" &>/dev/null; then
        echo "  ✓ Secret exists"

        # Check if it has versions
        VERSION_COUNT=$(gcloud secrets versions list "$SECRET_NAME" --project="$PROJECT_ID" --limit=1 --format="value(name)" | wc -l)
        if [ "$VERSION_COUNT" -eq 0 ]; then
            echo "  ⚠ Secret exists but has NO versions!"
            echo "  Please add a value with:"
            echo "  echo -n 'your-value' | gcloud secrets versions add $SECRET_NAME --data-file=-"
            return 1
        else
            echo "  ✓ Has version(s)"
        fi
    else
        echo "  ✗ Secret does NOT exist"
        echo "  Creating secret..."
        gcloud secrets create "$SECRET_NAME" \
            --replication-policy="automatic" \
            --project="$PROJECT_ID"
        echo "  ✓ Secret created (empty)"
        echo "  Please add a value with:"
        echo "  echo -n 'your-value' | gcloud secrets versions add $SECRET_NAME --data-file=-"
        return 1
    fi

    return 0
}

echo "Checking required secrets..."
echo

MISSING_VALUES=0

# Check GITHUB_TOKEN
if ! create_or_update_secret "GITHUB_TOKEN" "GitHub Personal Access Token"; then
    echo "  Add your GitHub token:"
    echo "  echo -n 'ghp_your_token_here' | gcloud secrets versions add GITHUB_TOKEN --data-file=-"
    echo
    MISSING_VALUES=1
fi

# Check ANTHROPIC_API_KEY
if ! create_or_update_secret "ANTHROPIC_API_KEY" "Anthropic API Key for Claude"; then
    echo "  Add your Anthropic API key:"
    echo "  echo -n 'sk-ant-your_key_here' | gcloud secrets versions add ANTHROPIC_API_KEY --data-file=-"
    echo
    MISSING_VALUES=1
fi

# Check PATTERN_MINER_DB_PASSWORD
if ! create_or_update_secret "PATTERN_MINER_DB_PASSWORD" "PostgreSQL database password"; then
    echo "  Add a strong database password:"
    echo "  echo -n 'your_secure_password' | gcloud secrets versions add PATTERN_MINER_DB_PASSWORD --data-file=-"
    echo
    MISSING_VALUES=1
fi

echo "================================"
if [ $MISSING_VALUES -eq 0 ]; then
    echo "✓ All secrets configured!"
    echo "You can now run: terraform apply"
else
    echo "⚠ Some secrets need values!"
    echo ""
    echo "Add the missing values above, then run terraform apply"
fi
echo "================================"

exit $MISSING_VALUES
