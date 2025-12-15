# Cloud Build Integration

## Overview

Pattern-miner uses **Cloud Build** to automatically build Docker images as part of the Terraform deployment, following the dev-nexus pattern. This provides:

- ✅ **Automated builds**: Terraform triggers Cloud Build automatically
- ✅ **No local Docker needed**: Builds happen in GCP
- ✅ **Consistent environment**: Same build environment every time
- ✅ **Faster CI/CD**: Parallel builds, caching, and high-speed networks
- ✅ **Git SHA tagging**: Images tagged with commit SHA for traceability

## How It Works

```
Terraform Apply
    ↓
Cloud Build Submit (via null_resource)
    ↓
Cloud Build reads cloudbuild.yaml
    ↓
Builds Docker image
    ↓
Pushes to GCR with tags:
  - gcr.io/PROJECT/pattern-miner:latest
  - gcr.io/PROJECT/pattern-miner:SHORT_SHA
    ↓
Cloud Run deploys with latest tag
```

## Configuration Files

### 1. `cloudbuild.yaml`

Defines the build steps:

```yaml
steps:
  # Build Docker image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/pattern-miner:latest', '.']

  # Push to GCR
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/pattern-miner:latest']

images:
  - 'gcr.io/$PROJECT_ID/pattern-miner:latest'
```

### 2. `terraform/build.tf`

Terraform resource that triggers Cloud Build:

```hcl
resource "null_resource" "build_image" {
  provisioner "local-exec" {
    command = "gcloud builds submit --config=cloudbuild.yaml"
  }
}
```

## Deployment Workflow

### Standard Deployment

```bash
cd terraform/

# Configure
cp terraform.tfvars.example terraform.tfvars
nano terraform.tfvars

# Set auto_build_image = true (default)
auto_build_image = true

# Deploy (builds image automatically)
terraform init
terraform apply
```

### What Happens

1. `terraform apply` starts
2. Cloud Build API is enabled
3. `null_resource.build_image` runs
4. Cloud Build:
   - Reads `cloudbuild.yaml`
   - Builds Docker image
   - Pushes to `gcr.io/PROJECT_ID/pattern-miner:latest`
5. Cloud Run service deploys with built image
6. Done! ✅

## Image Tags

Cloud Build creates two tags for every build:

1. **`:latest`** - Always points to most recent build
   ```
   gcr.io/your-project/pattern-miner:latest
   ```

2. **`:SHORT_SHA`** - Git commit SHA (first 7 chars)
   ```
   gcr.io/your-project/pattern-miner:a1b2c3d
   ```

This allows rollback to specific commits:

```bash
# Rollback to specific version
gcloud run services update pattern-miner \
  --image gcr.io/PROJECT_ID/pattern-miner:a1b2c3d \
  --region us-central1
```

## Manual Cloud Build

### Trigger Build Manually

```bash
# From project root
gcloud builds submit --config=cloudbuild.yaml
```

### With Custom Tag

```bash
gcloud builds submit \
  --config=cloudbuild.yaml \
  --substitutions=SHORT_SHA=v1.0.0
```

### View Build Logs

```bash
# List recent builds
gcloud builds list --limit=10

# View specific build
gcloud builds log BUILD_ID

# Stream logs in real-time
gcloud builds log BUILD_ID --stream
```

## CI/CD Integration

### GitHub Actions

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to GCP

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - uses: google-github-actions/auth@v1
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}

      - name: Deploy with Terraform
        run: |
          cd terraform/
          terraform init
          terraform apply -auto-approve
```

Terraform will automatically trigger Cloud Build as part of the deployment.

### Cloud Build Triggers (Automatic)

Create a trigger for automatic builds on git push:

```bash
gcloud builds triggers create github \
  --name=pattern-miner-trigger \
  --repo-name=pattern-miner \
  --repo-owner=patelmm79 \
  --branch-pattern=^main$ \
  --build-config=cloudbuild.yaml
```

Now every push to `main` automatically:
1. Triggers Cloud Build
2. Builds new image
3. Pushes to GCR
4. (Optional) Deploys to Cloud Run

## Build Configuration

### Machine Type

Default: `E2_HIGHCPU_8` (8 vCPU, 8GB RAM)

For faster builds:
```yaml
options:
  machineType: 'E2_HIGHCPU_32'  # 32 vCPU, 32GB RAM
```

For slower/cheaper builds:
```yaml
options:
  machineType: 'E2_HIGHCPU_2'  # 2 vCPU, 2GB RAM
```

### Timeout

Default: 600s (10 minutes)

Increase if needed:
```yaml
timeout: '1200s'  # 20 minutes
```

### Build Caching

Cloud Build automatically caches Docker layers between builds for faster rebuilds.

### Substitutions

Pass custom variables:

```yaml
substitutions:
  _SERVICE_NAME: pattern-miner
  _REGION: us-central1

steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/${_SERVICE_NAME}:latest', '.']
```

Use in command:
```bash
gcloud builds submit \
  --substitutions=_SERVICE_NAME=pattern-miner-dev
```

## Costs

Cloud Build free tier:
- **120 build-minutes/day** free
- E2_HIGHCPU_8 machine: ~$0.04/minute
- Typical build: 2-5 minutes = $0.08-0.20

Monthly estimate:
- 30 deployments/month × 3 min × $0.04 = **~$3.60/month**
- First 120 min/day free = **~$0-1/month** for light usage

## Comparison: Local vs Cloud Build

| Feature | Local Build | Cloud Build |
|---------|-------------|-------------|
| **Speed** | Depends on laptop | Fast (high CPU/network) |
| **Consistency** | Varies by machine | Always same environment |
| **CI/CD** | Manual | Automatic |
| **Caching** | Local only | Shared across team |
| **Cost** | Free | ~$0.04/min |
| **Terraform Integration** | Manual steps | Automatic |

## Troubleshooting

### Build Fails

```bash
# View logs
gcloud builds list --limit=5
gcloud builds log BUILD_ID

# Common issues:
# - Dockerfile syntax error
# - Missing dependencies in requirements.txt
# - Insufficient permissions
```

### Permission Denied

Grant Cloud Build service account permissions:

```bash
# Get service account
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
CLOUDBUILD_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"

# Grant Cloud Run Admin (to deploy)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${CLOUDBUILD_SA}" \
  --role="roles/run.admin"

# Grant Service Account User
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${CLOUDBUILD_SA}" \
  --role="roles/iam.serviceAccountUser"
```

### Image Not Found

```bash
# List images in GCR
gcloud container images list --repository=gcr.io/$PROJECT_ID

# List tags for pattern-miner
gcloud container images list-tags gcr.io/$PROJECT_ID/pattern-miner
```

### Slow Builds

1. Use larger machine type (`E2_HIGHCPU_32`)
2. Optimize Dockerfile (multi-stage, layer caching)
3. Use `.dockerignore` to exclude unnecessary files

## Advanced: Multi-stage Builds

Optimize build time and image size:

```dockerfile
# Build stage
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# Runtime stage
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY pattern_miner/ pattern_miner/
COPY config/ config/
ENV PATH=/root/.local/bin:$PATH
CMD ["python", "-m", "uvicorn", "pattern_miner.a2a.skills.server:app", "--host", "0.0.0.0", "--port", "8080"]
```

Benefits:
- Smaller final image (no build tools)
- Faster deployments
- Better layer caching

## Summary

✅ **Automated**: Terraform triggers builds automatically
✅ **Consistent**: Same environment every time
✅ **Fast**: High-CPU machines and caching
✅ **Traceable**: Git SHA tagging
✅ **Integrated**: Works seamlessly with Terraform

No need to manually run `docker build` anymore - Terraform handles everything!
