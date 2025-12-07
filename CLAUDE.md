# CLAUDE.md

This file provides guidance to Claude Code when working with the pattern-miner service.

## Project Overview

The Pattern Miner is an AI-powered service that discovers reusable code patterns across multiple repositories. It periodically scans configured repos, uses Claude AI to identify similar code patterns, and creates GitHub issues recommending code extraction into shared libraries.

## Development Commands

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Set required environment variables
export ANTHROPIC_API_KEY="sk-ant-xxxxx"
export GITHUB_TOKEN="ghp_xxxxx"

# Optional - Dev-nexus integration
export DEV_NEXUS_URL="https://dev-nexus-xxxxx-uc.a.run.app"
```

### Running Locally
```bash
# Start the service
uvicorn pattern_miner.app:app --reload --port 8081

# Or use Python directly
python -m pattern_miner.app
```

### Testing
```bash
# Health check
curl http://localhost:8081/

# View configuration
curl http://localhost:8081/api/config

# Trigger pattern mining (all repos, all pattern types)
curl -X POST http://localhost:8081/api/mine-patterns

# Mine specific pattern type
curl -X POST "http://localhost:8081/api/mine-patterns?pattern_type=deployment"

# Mine specific repos
curl -X POST http://localhost:8081/api/mine-patterns \
  -H "Content-Type: application/json" \
  -d '{"repos": ["patelmm79/repo1", "patelmm79/repo2"]}'
```

### Deployment
```bash
# Set environment variables
export GCP_PROJECT_ID="your-project-id"
export ANTHROPIC_API_KEY="sk-ant-xxxxx"
export GITHUB_TOKEN="ghp_xxxxx"
export DEV_NEXUS_URL="https://dev-nexus-xxxxx.run.app"

# Deploy to Cloud Run
chmod +x deploy-gcp.sh
./deploy-gcp.sh
```

## Architecture

### High-Level Flow
```
Manual/Scheduled Trigger
  → POST /api/mine-patterns
  → Load config/repositories.json
  → For each pattern type:
      → Fetch matching files from all repos
      → Analyze similarity with Claude
      → Generate extraction recommendations
  → Create GitHub issues for high-similarity patterns
  → Post findings to dev-nexus
```

### Core Components

**pattern_miner/app.py** - FastAPI service that:
- Provides API endpoints for triggering pattern mining
- Loads repository configuration
- Orchestrates pattern mining agents
- Creates GitHub issues with recommendations
- Posts findings to dev-nexus

**pattern_miner/miners/base_miner.py** - Base class for pattern miners:
- Fetches files from repositories
- Uses Claude to analyze code similarity
- Generates structured findings

**pattern_miner/miners/deployment_miner.py** - Deployment pattern specialist:
- Analyzes GCP deployment scripts
- Identifies Cloud Run configuration patterns
- Detects Secret Manager integration patterns
- Recommends shared deployment toolkits

**pattern_miner/miners/api_client_miner.py** - API client pattern specialist:
- Analyzes HTTP client implementations
- Identifies authentication patterns
- Detects rate limiting and retry logic
- Recommends shared client base classes

**config/repositories.json** - Configuration:
- Lists repositories to scan
- Defines pattern types to look for
- Sets similarity thresholds
- Configures extraction priorities

## Pattern Mining Process

### 1. File Fetching
- Searches each repo for files matching configured patterns
- Example: deployment miner looks for `deploy*.sh`, `cloudbuild.yaml`, `Dockerfile`
- Limits to 10 files per pattern per repo to avoid rate limits

### 2. Similarity Analysis
- Groups files by repository
- Sends to Claude with specialized prompts
- Claude analyzes code structure, functionality, and approach
- Returns similarity scores (0.0-1.0) and identifies reusable components

### 3. Recommendation Generation
- Filters for high-similarity patterns (>= 0.70)
- Generates extraction recommendations
- Suggests shared library names and structures
- Estimates time savings and benefits

### 4. Issue Creation
- Creates GitHub issues in relevant repositories
- Includes similarity score, affected repos, and recommendations
- Labels with `code-reuse`, `pattern-discovery`, `enhancement`
- Links to all repos with the pattern

### 5. Dev-Nexus Integration (Optional)
- Posts findings to dev-nexus knowledge base
- Tracks patterns over time
- Enables cross-repo pattern queries
- Supports continuous learning

## Configuration

### Adding Repositories

Edit `config/repositories.json`:

```json
{
  "repositories": [
    {
      "repo": "owner/repo-name",
      "scan_patterns": ["deployment", "api_client", "github_actions"]
    }
  ]
}
```

### Defining Pattern Types

```json
{
  "pattern_types": {
    "your_pattern_type": {
      "description": "What this pattern represents",
      "file_patterns": ["pattern1*.py", "pattern2.yaml"],
      "similarity_threshold": 0.75,
      "extraction_priority": "high"
    }
  }
}
```

### Similarity Thresholds
- **0.85+**: High similarity - immediate extraction recommended
- **0.70-0.84**: Medium similarity - consider extraction
- **0.50-0.69**: Low similarity - document pattern only

## Pattern Types Supported

### Deployment Patterns
**What it finds**:
- GCP Cloud Run deployment scripts
- Secret Manager integration
- Docker build configurations
- Terraform infrastructure

**Example finding**: "3 repos have nearly identical `deploy-gcp-cloudbuild.sh` scripts"

### API Client Patterns
**What it finds**:
- HTTP client wrappers
- Authentication handling (API keys, OAuth, JWT)
- Rate limiting implementations
- Retry strategies with exponential backoff

**Example finding**: "4 repos implement similar Anthropic API clients with retry logic"

### GitHub Actions Patterns
**What it finds**:
- Reusable workflow patterns
- Common CI/CD steps
- Deployment workflows
- Testing strategies

**Example finding**: "5 repos use similar pattern-monitoring workflows"

### Configuration Patterns
**What it finds**:
- Environment variable management
- Config file structures
- Secret handling patterns
- Feature flag implementations

**Example finding**: "3 repos have similar .env.example structures"

## Important Implementation Notes

### GitHub API Rate Limits
- Limits file fetches to 10 files per pattern per repo
- Uses GitHub Code Search API (has different rate limits than REST API)
- Implements basic rate limit handling

### LLM Context Limits
- Truncates file content to 3000 characters per file
- Summarizes multiple files in prompts
- Uses Claude Sonnet 4 for analysis (128K context window)

### Background Processing
- Pattern mining runs as FastAPI background task
- API returns immediately after scheduling
- Check GitHub issues for results

### Error Handling
- Logs errors but continues processing other repos
- Failed file fetches don't stop the mining run
- LLM analysis failures logged but don't crash service

## Extending Pattern Miners

To add a new pattern type:

1. Create new miner in `pattern_miner/miners/`:
```python
from pattern_miner.miners.base_miner import BasePatternMiner

class YourPatternMiner(BasePatternMiner):
    def get_file_patterns(self) -> List[str]:
        return ["your*.pattern", "files/*.here"]

    async def mine_patterns(self, repos: List[str]) -> List[Dict]:
        # Your mining logic
        pass
```

2. Register in `pattern_miner/app.py`:
```python
from pattern_miner.miners.your_miner import YourPatternMiner

# In run_pattern_mining():
if pattern_type is None or pattern_type == "your_type":
    miners.append(YourPatternMiner(anthropic_client, github_client))
```

3. Add configuration in `config/repositories.json`

## Debugging Tips

- Check service logs for mining progress and errors
- GitHub API search can be flaky - retry if searches fail
- Use `/api/config` to verify configuration loaded correctly
- Test with small number of repos first
- Claude analysis can take 10-30 seconds per comparison

## Cost Estimation

**Per mining run** (5 repos, 2 pattern types):
- GitHub API: Free (within rate limits)
- Claude API: ~$0.10-0.30 per run
- GCP Cloud Run: ~$0.01 per run

**Monthly** (weekly scheduled runs):
- Anthropic API: ~$1-2/month
- GCP Cloud Run: ~$1/month
- **Total**: ~$2-3/month

## Integration with Multi-Agent Ecosystem

**With dev-nexus**:
- Posts pattern findings to knowledge base
- Queries for existing patterns before analysis
- Enables historical pattern tracking

**With dependency-orchestrator**:
- Discoveries can inform dependency analysis
- Shared patterns indicate tight coupling
- Extraction reduces dependency complexity

**Future integrations**:
- A2A protocol for agent-to-agent communication
- Scheduled triggers via Cloud Scheduler
- Slack/Discord notifications for new discoveries
