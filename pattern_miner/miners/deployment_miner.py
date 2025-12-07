"""
Deployment Pattern Miner - Identifies similar deployment scripts and configurations
"""

import logging
from typing import Dict, List
from pattern_miner.miners.base_miner import BasePatternMiner

logger = logging.getLogger(__name__)


class DeploymentPatternMiner(BasePatternMiner):
    """
    Mines deployment patterns across repositories.

    Looks for:
    - GCP deployment scripts (deploy-gcp.sh, deploy-gcp-cloudbuild.sh)
    - Cloud Build configurations (cloudbuild.yaml)
    - Dockerfiles
    - Terraform configurations
    """

    def get_file_patterns(self) -> List[str]:
        """File patterns to search for"""
        return [
            "deploy*.sh",
            "cloudbuild.yaml",
            "Dockerfile",
            "*.tf",  # Terraform
            "docker-compose.yml"
        ]

    async def mine_patterns(self, repos: List[str]) -> List[Dict]:
        """
        Mine deployment patterns across repositories.

        Specifically looks for:
        1. GCP Cloud Run deployment patterns
        2. Secret Manager integration patterns
        3. Docker build patterns
        4. Terraform infrastructure patterns
        """
        logger.info(f"Mining deployment patterns across {len(repos)} repos")

        # Fetch deployment-related files from all repos
        repo_files = await self.fetch_files_from_repos(repos, self.get_file_patterns())

        if not repo_files:
            logger.warning("No deployment files found in any repository")
            return []

        # Analyze with LLM
        findings = await self.analyze_similarity_with_llm(
            repo_files,
            pattern_type="deployment"
        )

        # Enrich findings with deployment-specific recommendations
        for finding in findings:
            finding['recommendation'] = self._generate_deployment_recommendation(finding)
            finding['components'] = self._identify_reusable_components(finding)

        return findings

    def _generate_deployment_recommendation(self, finding: Dict) -> str:
        """Generate deployment-specific recommendations"""
        similarity = finding['similarity_score']
        repos = finding['repos']

        if similarity >= 0.85:
            return f"""**High Priority**: Extract into shared deployment toolkit

Create package: `gcp-deployment-toolkit` (or similar)

**Benefits**:
- Standardize deployment across {len(repos)} projects
- Reduce ~100 lines of duplicate bash code per project
- Centralize Secret Manager integration
- Single source of truth for Cloud Run configuration

**Suggested Structure**:
```python
from gcp_deployment import CloudRunDeployer

deployer = CloudRunDeployer(
    project_id="your-project",
    service_name="your-service"
)
deployer.deploy()
```
"""
        elif similarity >= 0.70:
            return f"""**Medium Priority**: Consider shared deployment library

While patterns are similar across {len(repos)} repos, minor differences exist.
Options:
1. Extract common core and support configuration for differences
2. Create deployment template repo for copy/customize approach
3. Document best practices and standardize incrementally
"""
        else:
            return "Similarity score below extraction threshold"

    def _identify_reusable_components(self, finding: Dict) -> str:
        """Identify specific reusable components"""
        components = [
            "**Secret Management**",
            "- Secret existence validation",
            "- Secret creation with proper IAM",
            "- Secret version management",
            "",
            "**Cloud Run Deployment**",
            "- Docker image build and push",
            "- Cloud Run service configuration",
            "- Environment variable injection",
            "- Secret Manager integration",
            "- Service URL retrieval",
            "",
            "**Error Handling**",
            "- GCP authentication checks",
            "- Project ID validation",
            "- Deployment verification",
            "- Rollback capability"
        ]

        return "\n".join(components)
