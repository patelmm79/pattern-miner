# Secrets Setup Guide

## Important: Secret Name vs Secret Value

**Secret Name**: The identifier in Secret Manager (e.g., `PATTERN_MINER_DB_PASSWORD`)
**Secret Value**: The actual password/token stored in the secret

## Required Secrets

### For Standalone PostgreSQL VM

When `create_postgres_vm = true`, Terraform will **automatically create** these secrets:

1. ✅ `GITHUB_TOKEN` - Created by Terraform
2. ✅ `ANTHROPIC_API_KEY` - Created by Terraform
3. ✅ `PATTERN_MINER_DB_PASSWORD` - Created by Terraform

**You only need to add the secret VALUES after Terraform creates them:**

```bash
# After terraform apply, add secret values:

# GitHub token
echo -n "ghp_your_actual_github_token_here" | gcloud secrets versions add GITHUB_TOKEN --data-file=-

# Anthropic API key
echo -n "sk-ant-your_actual_api_key_here" | gcloud secrets versions add ANTHROPIC_API_KEY --data-file=-

# Database password (use same password as postgres_vm_password in terraform.tfvars)
echo -n "your_actual_database_password" | gcloud secrets versions add PATTERN_MINER_DB_PASSWORD --data-file=-
```

### For Shared PostgreSQL (dev-nexus)

When `create_postgres_vm = false`, secrets must already exist:

```bash
# These should already exist from dev-nexus setup:
gcloud secrets describe POSTGRES_PASSWORD
gcloud secrets describe GITHUB_TOKEN
gcloud secrets describe ANTHROPIC_API_KEY
```

## Deployment Workflow

### Option 1: Create Secrets First (Recommended)

```bash
# 1. Create secrets with values
echo -n "ghp_token" | gcloud secrets create GITHUB_TOKEN --data-file=-
echo -n "sk-ant-key" | gcloud secrets create ANTHROPIC_API_KEY --data-file=-
echo -n "db-password" | gcloud secrets create PATTERN_MINER_DB_PASSWORD --data-file=-

# 2. Deploy with Terraform (uses existing secrets)
terraform apply
```

### Option 2: Let Terraform Create Secrets

```bash
# 1. Set create_secrets=true in terraform.tfvars
create_secrets = true

# 2. Deploy with Terraform (creates empty secrets)
terraform apply

# 3. Add secret values
echo -n "ghp_token" | gcloud secrets versions add GITHUB_TOKEN --data-file=-
echo -n "sk-ant-key" | gcloud secrets versions add ANTHROPIC_API_KEY --data-file=-
echo -n "db-password" | gcloud secrets versions add PATTERN_MINER_DB_PASSWORD --data-file=-

# 4. Restart Cloud Run to pick up secrets
gcloud run services update pattern-miner --region us-central1
```

### If Secrets Already Exist (Default)

```bash
# Terraform will automatically use existing secrets
# Set in terraform.tfvars:
create_secrets = false  # This is the default

# Just deploy
terraform apply
```

## terraform.tfvars Configuration

**Correct**:
```hcl
db_password_secret = "PATTERN_MINER_DB_PASSWORD"  # Secret NAME
postgres_vm_password = "MySecurePassword123!"      # Actual PASSWORD value
```

**Incorrect**:
```hcl
db_password_secret = "MySecurePassword123!"  # ❌ This is the password, not the secret name!
```

## Verifying Secrets

```bash
# List all secrets
gcloud secrets list

# Check if secret has a value
gcloud secrets versions list PATTERN_MINER_DB_PASSWORD

# View secret metadata (not the actual value)
gcloud secrets describe PATTERN_MINER_DB_PASSWORD
```

## Updating Secret Values

```bash
# Add new version (old versions retained)
echo -n "new-password" | gcloud secrets versions add PATTERN_MINER_DB_PASSWORD --data-file=-

# Cloud Run automatically uses "latest" version
```

## Troubleshooting

### Error: "Secret not found"

```bash
# Check if secret exists
gcloud secrets describe PATTERN_MINER_DB_PASSWORD

# If not, create it
gcloud secrets create PATTERN_MINER_DB_PASSWORD --replication-policy=automatic

# Add value
echo -n "password" | gcloud secrets versions add PATTERN_MINER_DB_PASSWORD --data-file=-
```

### Error: "Secret has no versions"

```bash
# Secret exists but has no value
echo -n "password" | gcloud secrets versions add PATTERN_MINER_DB_PASSWORD --data-file=-
```

### Error: "Permission denied accessing secret"

```bash
# Grant access to service account
gcloud secrets add-iam-policy-binding PATTERN_MINER_DB_PASSWORD \
  --member="serviceAccount:pattern-miner-sa@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

## Security Best Practices

1. **Never commit secrets to git**
   - Secrets should only be in Secret Manager
   - Use `.gitignore` for terraform.tfvars

2. **Use strong passwords**
   - Minimum 16 characters
   - Mix of letters, numbers, symbols
   - Use password generator

3. **Rotate secrets regularly**
   - Add new version to Secret Manager
   - Cloud Run automatically uses latest
   - Delete old versions after migration

4. **Limit access**
   - Only grant `secretAccessor` role to necessary service accounts
   - Use separate secrets per environment (dev/prod)

## Example: Complete Setup

```bash
# 1. Set project
gcloud config set project your-project-id

# 2. Create secrets (if not using Terraform to create them)
echo -n "$(openssl rand -base64 32)" | gcloud secrets create PATTERN_MINER_DB_PASSWORD --data-file=-
echo -n "ghp_your_token" | gcloud secrets create GITHUB_TOKEN --data-file=-
echo -n "sk-ant-your_key" | gcloud secrets create ANTHROPIC_API_KEY --data-file=-

# 3. Verify
gcloud secrets list

# 4. Deploy
cd terraform/
terraform apply

# 5. Verify Cloud Run has access
gcloud run services describe pattern-miner --region us-central1 --format="value(spec.template.spec.containers[0].env)"
```

## Summary

✅ **Secret Name**: Identifier in terraform.tfvars (e.g., `PATTERN_MINER_DB_PASSWORD`)
✅ **Secret Value**: Actual password added via `gcloud secrets versions add`
✅ **Terraform creates**: Empty secrets automatically
✅ **You add values**: After `terraform apply`
✅ **Cloud Run uses**: Latest version automatically

**Remember**: The secret name goes in `terraform.tfvars`, the actual password goes in Secret Manager!
