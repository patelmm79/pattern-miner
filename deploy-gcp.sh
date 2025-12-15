#!/bin/bash
# Deploy pattern-miner service to GCP Cloud Run

set -e

# Configuration
PROJECT_ID="${GCP_PROJECT_ID}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="pattern-miner"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

if [ -z "$PROJECT_ID" ]; then
  echo "❌ Error: GCP_PROJECT_ID not set"
  echo "Usage: export GCP_PROJECT_ID=\"your-project-id\""
  exit 1
fi

echo "🚀 Deploying Pattern Miner to GCP Cloud Run"
echo "   Project: $PROJECT_ID"
echo "   Region: $REGION"
echo ""

# Authenticate with GCP
echo "📋 Checking GCP authentication..."
gcloud config set project $PROJECT_ID

# Build Docker image
echo "🐋 Building Docker image..."
docker build -t $IMAGE_NAME .

# Push to GCR
echo "📤 Pushing image to Google Container Registry..."
docker push $IMAGE_NAME

# Deploy to Cloud Run
echo "☁️  Deploying to Cloud Run..."
gcloud run deploy pattern-miner \
  --image gcr.io/${PROJECT_ID}/pattern-miner:latest \
  --region ${REGION} \
  --platform managed \
  --port 8080 \
  --memory 2Gi \
  --cpu 1 \
  --allow-unauthenticated \
  --set-env-vars="AGENT_URL=https://pattern-miner-${PROJECT_ID}.a.run.app" \
  --set-secrets="GITHUB_TOKEN=GITHUB_TOKEN:latest,ANTHROPIC_API_KEY=ANTHROPIC_API_KEY:latest"


# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format="value(status.url)")

echo ""
echo "✅ Deployment complete!"
echo "🌐 Service URL: $SERVICE_URL"
echo ""
echo "Test the service:"
echo "  curl $SERVICE_URL/"
echo ""
echo "Trigger pattern mining:"
echo "  curl -X POST $SERVICE_URL/api/mine-patterns"
