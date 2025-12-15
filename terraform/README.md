# Pattern Miner - Terraform Deployment

This directory contains Terraform configuration for deploying the Pattern Miner service to Google Cloud Platform (GCP) Cloud Run.

## Important: Shared PostgreSQL with dev-nexus

Pattern-miner uses the **same PostgreSQL VM** deployed by dev-nexus, not Cloud SQL. This provides:

- ✅ **Cost savings**: $1/month total (vs $7-10/month for separate Cloud SQL)
- ✅ **Shared knowledge base**: Both services can query each other's data
- ✅ **Simplified infrastructure**: One database to manage

**Prerequisites for database integration**:
- dev-nexus must be deployed first with PostgreSQL VM
- VPC Connector `devnexus-connector` must exist
- `POSTGRES_PASSWORD` secret must exist in Secret Manager

See `docs/POSTGRESQL_SHARED_SETUP.md` for detailed setup instructions.

## Prerequisites

1. **Terraform installed** (>= 1.0)
   ```bash
   # macOS
   brew install terraform

   # Windows
   choco install terraform

   # Linux
   wget https://releases.hashicorp.com/terraform/1.6.0/terraform_1.6.0_linux_amd64.zip
   unzip terraform_1.6.0_linux_amd64.zip
   sudo mv terraform /usr/local/bin/
   ```

2. **Google Cloud SDK installed and authenticated**
   ```bash
   # Install gcloud
   curl https://sdk.cloud.google.com | bash

   # Authenticate
   gcloud auth login
   gcloud auth application-default login
   ```

3. **Docker installed** (for building and pushing images)

4. **GCP Project with billing enabled**

## Quick Start

### 1. Build and Push Docker Image

First, build and push your Docker image to Google Container Registry (GCR):

```bash
# Set your project ID
export PROJECT_ID="your-gcp-project-id"

# Build the Docker image
cd ..  # Go to project root
docker build -t gcr.io/${PROJECT_ID}/pattern-miner:latest .

# Configure Docker to use gcloud as credential helper
gcloud auth configure-docker

# Push to GCR
docker push gcr.io/${PROJECT_ID}/pattern-miner:latest
```

**Alternative: Using Artifact Registry**
```bash
# Create Artifact Registry repository (one time)
gcloud artifacts repositories create pattern-miner \
  --repository-format=docker \
  --location=us-central1 \
  --description="Pattern Miner Docker images"

# Configure Docker
gcloud auth configure-docker us-docker.pkg.dev

# Build and push
docker build -t us-docker.pkg.dev/${PROJECT_ID}/pattern-miner/app:latest .
docker push us-docker.pkg.dev/${PROJECT_ID}/pattern-miner/app:latest
```

### 2. Configure Terraform Variables

```bash
cd terraform/

# Copy the example variables file
cp terraform.tfvars.example terraform.tfvars

# Edit terraform.tfvars with your values
nano terraform.tfvars  # or use your favorite editor
```

**Required variables:**
- `project_id`: Your GCP project ID
- `container_image`: Full image URL from step 1

### 3. Verify dev-nexus Prerequisites

Before deploying pattern-miner, ensure dev-nexus is set up:

```bash
# Verify PostgreSQL VM exists
gcloud compute instances describe devnexus-postgres --zone=us-central1-a

# Verify VPC Connector exists
gcloud compute networks vpc-access connectors describe devnexus-connector --region=us-central1

# Verify POSTGRES_PASSWORD secret exists (shared with dev-nexus)
gcloud secrets describe POSTGRES_PASSWORD
```

### 4. Add Pattern-miner Secrets to Secret Manager

```bash
# Add GitHub token (pattern-miner specific)
echo -n "ghp_your_github_token_here" | gcloud secrets create GITHUB_TOKEN --data-file=-

# Add Anthropic API key (pattern-miner specific)
echo -n "sk-ant-your_anthropic_key_here" | gcloud secrets create ANTHROPIC_API_KEY --data-file=-
```

**Note:** POSTGRES_PASSWORD is shared with dev-nexus and should already exist.

If secrets already exist, use `versions add` instead:
```bash
echo -n "your_new_token" | gcloud secrets versions add GITHUB_TOKEN --data-file=-
echo -n "your_new_key" | gcloud secrets versions add ANTHROPIC_API_KEY --data-file=-
```

### 4. Deploy with Terraform

```bash
# Initialize Terraform
terraform init

# Review the deployment plan
terraform plan

# Apply the configuration
terraform apply
```

Type `yes` when prompted to confirm deployment.

### 5. Test the Deployment

After deployment completes, Terraform will output the service URL and test commands:

```bash
# Get the service URL
SERVICE_URL=$(terraform output -raw service_url)

# Health check
curl $SERVICE_URL/

# View configuration
curl $SERVICE_URL/api/config

# Trigger pattern mining
curl -X POST $SERVICE_URL/api/mine-patterns
```

## Configuration Options

### Resource Allocation

Adjust CPU and memory in `terraform.tfvars`:

```hcl
cpu    = "2"      # Number of CPUs
memory = "4Gi"    # Memory allocation
```

### Auto-scaling

Configure instance scaling:

```hcl
min_instances = 0   # Scale to zero when idle (cost-effective)
max_instances = 10  # Maximum concurrent instances
```

### Public vs Private Access

```hcl
# Allow public access (default)
allow_public_access = true

# Require authentication
allow_public_access = false
```

If `allow_public_access = false`, you'll need to authenticate requests:
```bash
# Get an identity token
TOKEN=$(gcloud auth print-identity-token)

# Make authenticated request
curl -H "Authorization: Bearer $TOKEN" $SERVICE_URL/api/mine-patterns
```

### Scheduled Pattern Mining

Enable automatic pattern mining on a schedule:

```hcl
enable_scheduled_mining = true
mining_schedule         = "0 9 * * 1"  # Every Monday at 9 AM
```

**Schedule formats:**
- `0 9 * * 1` - Every Monday at 9 AM
- `0 0 * * 0` - Every Sunday at midnight
- `0 */6 * * *` - Every 6 hours
- `0 9 1 * *` - First day of every month at 9 AM

### Dev-Nexus Integration

To enable dev-nexus integration:

```hcl
dev_nexus_url = "https://dev-nexus-xxxxx-uc.a.run.app"
```

## Terraform Files

- **main.tf** - Main infrastructure configuration (Cloud Run, Secret Manager, IAM)
- **variables.tf** - Variable definitions and defaults
- **outputs.tf** - Output values after deployment
- **terraform.tfvars** - Your customized values (git-ignored)
- **terraform.tfvars.example** - Example configuration template

## What Gets Created

This Terraform configuration creates:

1. **Cloud Run Service**: Containerized pattern-miner service
   - Connected to private VPC via VPC Connector (shared with dev-nexus)
   - Egress set to `PRIVATE_RANGES_ONLY` for secure database access
2. **Service Account**: Dedicated service account with minimal permissions
3. **Secret Manager Secrets** (pattern-miner specific):
   - `GITHUB_TOKEN` - For GitHub API access
   - `ANTHROPIC_API_KEY` - For Claude AI access
4. **IAM Bindings**: Grants service account access to secrets (including shared POSTGRES_PASSWORD)
5. **API Enablement**: Enables required GCP APIs
6. **Cloud Scheduler Job** (optional): Automated pattern mining triggers

**Shared Resources (from dev-nexus, not created by this Terraform)**:
- VPC Connector (`devnexus-connector`)
- PostgreSQL VM (`devnexus-postgres`)
- Secret (`POSTGRES_PASSWORD`)

## Cost Estimation

**Monthly costs with default settings (approximate):**
- Cloud Run: $0-5/month (pay per request, scales to zero)
- Secret Manager: $0.06/month (2 pattern-miner specific secrets)
- Cloud Scheduler: $0.10/month (if enabled)
- **Shared costs with dev-nexus**:
  - PostgreSQL e2-micro VM: $0 (free tier)
  - VPC Connector: $0.10-0.30/month (shared)
- **Total (pattern-miner only): ~$0.16-5/month** (depends on usage)
- **Total (shared infrastructure): ~$1-6/month**

Pattern mining runs typically cost $0.10-0.30 in Claude API calls.

**Cost savings vs separate Cloud SQL**: ~$70-100/year

## Updating the Deployment

When you make code changes:

```bash
# 1. Rebuild and push Docker image
docker build -t gcr.io/${PROJECT_ID}/pattern-miner:latest .
docker push gcr.io/${PROJECT_ID}/pattern-miner:latest

# 2. Update Cloud Run (no need to run terraform apply)
# Cloud Run will automatically pull the latest image on next cold start
# Or force update:
gcloud run deploy pattern-miner \
  --image gcr.io/${PROJECT_ID}/pattern-miner:latest \
  --region us-central1
```

**To update infrastructure:**
```bash
# Modify terraform.tfvars or *.tf files
# Then apply changes
terraform apply
```

## Viewing Logs

```bash
# View recent logs
gcloud run services logs read pattern-miner --region us-central1

# Follow logs in real-time
gcloud run services logs tail pattern-miner --region us-central1

# View in Cloud Console
echo "https://console.cloud.google.com/run/detail/${REGION}/pattern-miner/logs?project=${PROJECT_ID}"
```

## Troubleshooting

### Issue: "Permission denied" when accessing secrets

**Solution:** Ensure secrets exist and have proper IAM bindings:
```bash
# Check secrets exist
gcloud secrets list

# Grant access (Terraform should do this automatically)
gcloud secrets add-iam-policy-binding GITHUB_TOKEN \
  --member="serviceAccount:pattern-miner-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### Issue: "Service not found" or 404 errors

**Solution:** Verify deployment status:
```bash
gcloud run services describe pattern-miner --region us-central1
```

### Issue: Container fails to start

**Solution:** Check logs for startup errors:
```bash
gcloud run services logs read pattern-miner --region us-central1 --limit 50
```

Common causes:
- Missing or invalid secrets
- Wrong PORT environment variable
- Python dependencies missing

### Issue: Pattern mining times out

**Solution:** Cloud Run has a 3600s (1 hour) timeout configured. If mining takes longer:
1. Reduce number of repositories in `config/repositories.json`
2. Mine specific pattern types instead of all
3. Increase timeout in `main.tf` (max is 3600s)

## Destroying the Infrastructure

To completely remove all created resources:

```bash
terraform destroy
```

**Warning:** This will delete:
- Cloud Run service
- Service account
- IAM bindings
- Cloud Scheduler jobs

It will **NOT** delete:
- Secret Manager secrets (manual deletion required)
- Docker images in GCR
- Cloud Run revision history

To delete secrets manually:
```bash
gcloud secrets delete GITHUB_TOKEN
gcloud secrets delete ANTHROPIC_API_KEY
```

## CI/CD Integration

### GitHub Actions Example

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Cloud Run

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

      - name: Build and push Docker image
        run: |
          gcloud auth configure-docker
          docker build -t gcr.io/${{ secrets.GCP_PROJECT_ID }}/pattern-miner:${{ github.sha }} .
          docker push gcr.io/${{ secrets.GCP_PROJECT_ID }}/pattern-miner:${{ github.sha }}
          docker tag gcr.io/${{ secrets.GCP_PROJECT_ID }}/pattern-miner:${{ github.sha }} \
                     gcr.io/${{ secrets.GCP_PROJECT_ID }}/pattern-miner:latest
          docker push gcr.io/${{ secrets.GCP_PROJECT_ID }}/pattern-miner:latest

      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy pattern-miner \
            --image gcr.io/${{ secrets.GCP_PROJECT_ID }}/pattern-miner:latest \
            --region us-central1
```

## Additional Resources

- [GCP Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Terraform GCP Provider](https://registry.terraform.io/providers/hashicorp/google/latest/docs)
- [Secret Manager Best Practices](https://cloud.google.com/secret-manager/docs/best-practices)
- [Cloud Scheduler Documentation](https://cloud.google.com/scheduler/docs)

## Support

For issues specific to:
- **Pattern Miner**: See main project README
- **Terraform**: Check [Terraform documentation](https://www.terraform.io/docs)
- **GCP**: Visit [GCP support](https://cloud.google.com/support)
