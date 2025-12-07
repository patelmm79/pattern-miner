#!/usr/bin/env python3
"""
Pattern Miner Service - Discovers reusable code patterns across repositories
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import anthropic
from github import Github

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Pattern Miner",
    description="Cross-repository pattern discovery and code reuse analysis",
    version="1.0.0"
)

# Initialize clients
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
DEV_NEXUS_URL = os.environ.get('DEV_NEXUS_URL')

if not ANTHROPIC_API_KEY:
    logger.error("ANTHROPIC_API_KEY environment variable not set")
    raise ValueError("ANTHROPIC_API_KEY is required")

if not GITHUB_TOKEN:
    logger.error("GITHUB_TOKEN environment variable not set")
    raise ValueError("GITHUB_TOKEN is required")

anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
github_client = Github(GITHUB_TOKEN)

# Load configuration
config_path = Path(__file__).parent.parent / "config" / "repositories.json"
try:
    with open(config_path) as f:
        CONFIG = json.load(f)
except FileNotFoundError:
    logger.warning("Configuration file not found, using defaults")
    CONFIG = {
        "repositories": [],
        "pattern_types": {}
    }


class MiningRequest(BaseModel):
    """Request to mine patterns"""
    pattern_type: Optional[str] = None
    repos: Optional[List[str]] = None


class PatternMatch(BaseModel):
    """A discovered pattern match"""
    pattern_type: str
    repos: List[str]
    similarity_score: float
    description: str
    extraction_recommended: bool


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "Pattern Miner",
        "status": "healthy",
        "version": "1.0.0",
        "dev_nexus_enabled": DEV_NEXUS_URL is not None,
        "repositories_configured": len(CONFIG.get("repositories", []))
    }


@app.get("/api/config")
async def get_config():
    """Get current configuration"""
    return CONFIG


@app.post("/api/mine-patterns")
async def mine_patterns(
    request: MiningRequest,
    background_tasks: BackgroundTasks
):
    """
    Trigger pattern mining across configured repositories.

    This runs as a background task and returns immediately.
    Check /api/patterns for results.
    """
    repos_to_scan = request.repos if request.repos else [
        repo["repo"] for repo in CONFIG.get("repositories", [])
    ]

    if not repos_to_scan:
        raise HTTPException(
            status_code=400,
            detail="No repositories configured. Add repos to config/repositories.json"
        )

    logger.info(f"Starting pattern mining for {len(repos_to_scan)} repositories")

    # Schedule mining as background task
    background_tasks.add_task(
        run_pattern_mining,
        repos_to_scan,
        request.pattern_type
    )

    return {
        "status": "mining_started",
        "repositories_scheduled": repos_to_scan,
        "pattern_type": request.pattern_type or "all",
        "timestamp": datetime.now().isoformat()
    }


async def run_pattern_mining(repos: List[str], pattern_type: Optional[str] = None):
    """
    Main pattern mining logic - runs in background.

    1. Fetch files from all repos
    2. Analyze with Claude for pattern detection
    3. Compare patterns across repos
    4. Generate recommendations
    5. Create issues for high-similarity patterns
    6. Post to dev-nexus
    """
    try:
        logger.info(f"Mining patterns across {len(repos)} repositories")

        # Import pattern miners
        from pattern_miner.miners.deployment_miner import DeploymentPatternMiner
        from pattern_miner.miners.api_client_miner import ApiClientPatternMiner

        # Determine which miners to run
        miners = []
        if pattern_type is None or pattern_type == "deployment":
            miners.append(DeploymentPatternMiner(anthropic_client, github_client))
        if pattern_type is None or pattern_type == "api_client":
            miners.append(ApiClientPatternMiner(anthropic_client, github_client))

        all_findings = []

        # Run each miner
        for miner in miners:
            logger.info(f"Running {miner.__class__.__name__}")
            findings = await miner.mine_patterns(repos)
            all_findings.extend(findings)

        logger.info(f"Pattern mining complete. Found {len(all_findings)} patterns")

        # Process findings
        await process_findings(all_findings)

    except Exception as e:
        logger.error(f"Error during pattern mining: {e}", exc_info=True)


async def process_findings(findings: List[Dict]):
    """
    Process pattern mining findings:
    - Filter for high similarity
    - Create GitHub issues with recommendations
    - Post to dev-nexus
    """
    for finding in findings:
        similarity = finding.get('similarity_score', 0.0)

        # Only process high-similarity patterns
        if similarity >= 0.75:
            logger.info(
                f"High similarity pattern found: {finding['pattern_type']} "
                f"({similarity:.0%} across {len(finding['repos'])} repos)"
            )

            # Create issue in the "hub" repo or first repo
            await create_extraction_recommendation_issue(finding)

            # Post to dev-nexus if configured
            if DEV_NEXUS_URL:
                await post_to_dev_nexus(finding)


async def create_extraction_recommendation_issue(finding: Dict):
    """Create GitHub issue recommending code extraction"""
    try:
        # Create issue in first repo (or a dedicated "shared-libs" repo)
        target_repo = finding['repos'][0]
        repo = github_client.get_repo(target_repo)

        similarity_pct = finding['similarity_score'] * 100

        title = f"🔍 Code Reuse Opportunity: {finding['pattern_type'].replace('_', ' ').title()}"

        body = f"""## Pattern Discovery

We've detected similar {finding['pattern_type']} patterns across **{len(finding['repos'])} repositories** that could be extracted into a shared library.

### Similarity Score
**{similarity_pct:.0f}%** - {"High" if similarity_pct >= 85 else "Medium"} confidence for extraction

### Repositories with Similar Patterns
{chr(10).join(f"- {repo}" for repo in finding['repos'])}

### Pattern Description
{finding.get('description', 'Similar code patterns detected')}

### Recommended Action
{finding.get('recommendation', 'Extract common functionality into shared library')}

### Reusable Components Identified
{finding.get('components', 'See pattern analysis for details')}

### Estimated Benefits
- **Time Savings**: Reduce duplication, faster new project setup
- **Consistency**: Standardize approach across projects
- **Maintenance**: Fix bugs/improvements in one place
- **Testing**: Shared test suite for common functionality

### Next Steps
1. Review the pattern across all affected repositories
2. Design shared library API
3. Extract and package common code
4. Update repositories to use shared library
5. Document usage and examples

---
_🤖 Automatically discovered by [Pattern Miner](https://github.com/patelmm79/pattern-miner)_
"""

        issue = repo.create_issue(
            title=title,
            body=body,
            labels=["code-reuse", "pattern-discovery", "enhancement"]
        )

        logger.info(f"Created extraction recommendation issue #{issue.number} in {target_repo}")

    except Exception as e:
        logger.error(f"Error creating issue: {e}", exc_info=True)


async def post_to_dev_nexus(finding: Dict):
    """Post pattern finding to dev-nexus knowledge base"""
    try:
        import httpx

        payload = {
            "pattern_type": finding['pattern_type'],
            "repos": finding['repos'],
            "similarity_score": finding['similarity_score'],
            "description": finding.get('description', ''),
            "timestamp": datetime.now().isoformat()
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{DEV_NEXUS_URL}/api/kb/cross-repo-patterns",
                json=payload
            )

            if response.status_code in [200, 201]:
                logger.info(f"Posted pattern finding to dev-nexus: {finding['pattern_type']}")
            else:
                logger.warning(f"Failed to post to dev-nexus: HTTP {response.status_code}")

    except Exception as e:
        logger.error(f"Error posting to dev-nexus: {e}")


@app.get("/api/patterns")
async def get_patterns():
    """Get all discovered patterns"""
    # TODO: Store patterns in database or file system
    return {
        "message": "Pattern storage not yet implemented",
        "note": "Check GitHub issues for extraction recommendations"
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8081))
    uvicorn.run(app, host="0.0.0.0", port=port)
