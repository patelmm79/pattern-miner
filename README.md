# Pattern Miner

> AI-powered cross-repository pattern discovery service that identifies reusable code, common patterns, and extraction opportunities across your entire codebase ecosystem.

## What This Does

The Pattern Miner periodically scans all your repositories to discover:
- **Duplicate code** that could be extracted into shared libraries
- **Similar deployment patterns** (GCP scripts, Docker configs, CI/CD workflows)
- **Common API clients** and integration patterns
- **Configuration patterns** that could be standardized
- **Reusable components** hidden in individual projects

When similar patterns are found, it:
1. Posts findings to dev-nexus knowledge base
2. Creates GitHub issues with extraction recommendations
3. Suggests shared library names and structures
4. Tracks extraction opportunities over time

## Quick Start

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export ANTHROPIC_API_KEY="sk-ant-xxxxx"
export GITHUB_TOKEN="ghp_xxxxx"
export DEV_NEXUS_URL="https://dev-nexus-xxxxx.run.app"  # optional but recommended

# Run the service
uvicorn pattern_miner.app:app --reload --port 8081

# Trigger a pattern mining run
curl -X POST http://localhost:8081/api/mine-patterns
```

### Deployment

Deploy to GCP Cloud Run:

```bash
export GCP_PROJECT_ID="your-project-id"
export ANTHROPIC_API_KEY="sk-ant-xxxxx"
export GITHUB_TOKEN="ghp_xxxxx"
export DEV_NEXUS_URL="https://dev-nexus-xxxxx.run.app"

./deploy-gcp.sh
```

## How It Works

1. **Scheduled Scan**: Runs daily/weekly or on-demand via API
2. **Repository Analysis**: Fetches configured files from all repos
3. **Pattern Detection**: Uses Claude to identify similar code patterns
4. **Similarity Scoring**: Compares patterns across repositories
5. **Recommendation Generation**: Suggests extraction opportunities
6. **Issue Creation**: Creates GitHub issues with detailed recommendations
7. **Knowledge Update**: Posts findings to dev-nexus

## Configuration

Edit `config/repositories.json` to define repos and pattern types to scan:

```json
{
  "repositories": [
    {
      "repo": "patelmm79/vllm-container-ngc",
      "scan_patterns": ["deployment", "docker", "github_actions"]
    },
    {
      "repo": "patelmm79/agentic-log-attacker",
      "scan_patterns": ["deployment", "api_client", "configuration"]
    }
  ],
  "pattern_types": {
    "deployment": {
      "file_patterns": ["deploy*.sh", "cloudbuild.yaml", "Dockerfile"],
      "similarity_threshold": 0.75
    },
    "github_actions": {
      "file_patterns": [".github/workflows/*.yml"],
      "similarity_threshold": 0.70
    }
  }
}
```

## Pattern Types

### Deployment Patterns
- GCP deployment scripts
- Cloud Run configurations
- Docker configurations
- Terraform modules

### API Client Patterns
- HTTP client wrappers
- Authentication handling
- Rate limiting logic
- Error handling patterns

### Configuration Patterns
- Environment variable management
- Config file structures
- Secret management
- Feature flags

### GitHub Actions Patterns
- Reusable workflows
- Common CI/CD steps
- Deployment workflows
- Testing patterns

## API Reference

### `POST /api/mine-patterns`
Trigger a pattern mining run across all configured repositories.

**Query Parameters**:
- `pattern_type` (optional): Specific pattern type to mine (e.g., "deployment")
- `repos` (optional): Comma-separated list of repos to scan

**Response**:
```json
{
  "status": "mining_started",
  "repositories_scanned": 5,
  "patterns_found": 12,
  "extraction_opportunities": 3
}
```

### `GET /api/patterns`
Get all discovered patterns and their similarity scores.

### `GET /api/patterns/{pattern_type}`
Get patterns of a specific type.

## Integration with Dev-Nexus

When `DEV_NEXUS_URL` is configured:
- Queries existing patterns before analysis
- Compares new findings with historical data
- Posts pattern discoveries for future reference
- Tracks extraction recommendations over time

## Example Output

When similar patterns are found, creates issues like:

```markdown
## 🔍 Code Reuse Opportunity: GCP Deployment Pattern

We've detected similar deployment scripts across 3 repositories that could be
extracted into a shared library.

### Pattern Found
GCP Cloud Run deployment with Secret Manager integration

### Repositories
- patelmm79/vllm-container-ngc (deploy-gcp-cloudbuild.sh)
- patelmm79/agentic-log-attacker (deploy-gcp.sh)
- patelmm79/synthetic-log-generator (deploy.sh)

### Similarity Score
87% - High confidence for extraction

### Recommended Action
Create shared library: `gcp-deployment-toolkit`

**Reusable components**:
1. Secret validation and creation
2. Cloud Run deployment with standard config
3. Service URL output and logging

**Implementation**:
```bash
# Install shared library
pip install gcp-deployment-toolkit

# Use in deploy script
from gcp_deployment import CloudRunDeployer
deployer = CloudRunDeployer(project_id, service_name)
deployer.deploy()
```

**Estimated Time Savings**: 30 minutes per new service deployment
```

## Cost Estimation

- **GCP Cloud Run**: ~$1-2/month (scheduled runs)
- **Anthropic API**: ~$5-10/month (depends on repo count)
- **Total**: ~$6-12/month

## Next Steps

1. Configure repositories in `config/repositories.json`
2. Deploy to Cloud Run
3. Schedule weekly pattern mining runs
4. Review extraction recommendations
5. Create shared libraries for high-similarity patterns

---

**Part of the multi-agent development ecosystem**:
- [dev-nexus](https://github.com/patelmm79/dev-nexus) - Central knowledge base
- [dependency-orchestrator](https://github.com/patelmm79/dependency-orchestrator) - Dependency impact analysis
