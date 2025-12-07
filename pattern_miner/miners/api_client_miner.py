"""
API Client Pattern Miner - Identifies similar API client implementations
"""

import logging
from typing import Dict, List
from pattern_miner.miners.base_miner import BasePatternMiner

logger = logging.getLogger(__name__)


class ApiClientPatternMiner(BasePatternMiner):
    """
    Mines API client patterns across repositories.

    Looks for:
    - HTTP client wrappers
    - API authentication patterns
    - Rate limiting implementations
    - Retry logic
    - Error handling
    """

    def get_file_patterns(self) -> List[str]:
        """File patterns to search for"""
        return [
            "*client.py",
            "*api*.py",
            "client/*.py",
            "api/*.py"
        ]

    async def mine_patterns(self, repos: List[str]) -> List[Dict]:
        """
        Mine API client patterns across repositories.

        Specifically looks for:
        1. HTTP client patterns (requests, httpx, aiohttp)
        2. Authentication handling (API keys, OAuth, JWT)
        3. Rate limiting logic
        4. Retry strategies
        5. Error handling patterns
        """
        logger.info(f"Mining API client patterns across {len(repos)} repos")

        # Fetch API client files from all repos
        repo_files = await self.fetch_files_from_repos(repos, self.get_file_patterns())

        if not repo_files:
            logger.warning("No API client files found in any repository")
            return []

        # Analyze with LLM
        findings = await self.analyze_similarity_with_llm(
            repo_files,
            pattern_type="api_client"
        )

        # Enrich findings with API client-specific recommendations
        for finding in findings:
            finding['recommendation'] = self._generate_api_client_recommendation(finding)
            finding['components'] = self._identify_reusable_components(finding)

        return findings

    def _generate_api_client_recommendation(self, finding: Dict) -> str:
        """Generate API client-specific recommendations"""
        similarity = finding['similarity_score']
        repos = finding['repos']

        if similarity >= 0.85:
            return f"""**High Priority**: Extract into shared API client library

Create package: `common-api-client` (or similar)

**Benefits**:
- Standardize HTTP client usage across {len(repos)} projects
- Centralize authentication patterns
- Shared rate limiting and retry logic
- Consistent error handling
- Reduce ~200 lines of duplicate client code per project

**Suggested Structure**:
```python
from common_api_client import BaseApiClient

class MyServiceClient(BaseApiClient):
    def __init__(self, api_key: str, base_url: str):
        super().__init__(
            base_url=base_url,
            auth=ApiKeyAuth(api_key),
            rate_limit=RateLimit(requests_per_minute=60),
            retry_strategy=ExponentialBackoff(max_retries=3)
        )

    async def get_resource(self, resource_id: str):
        return await self.get(f"/resources/{resource_id}")
```
"""
        elif similarity >= 0.70:
            return f"""**Medium Priority**: Consider shared client base class

While client patterns are similar across {len(repos)} repos, APIs differ.
Options:
1. Extract common base class with auth/retry/rate-limiting
2. Create client interface/protocol for consistency
3. Document API client best practices
"""
        else:
            return "Similarity score below extraction threshold"

    def _identify_reusable_components(self, finding: Dict) -> str:
        """Identify specific reusable components"""
        components = [
            "**Authentication**",
            "- API key handling",
            "- Token refresh logic",
            "- OAuth flow implementation",
            "",
            "**Request Management**",
            "- HTTP client configuration",
            "- Request/response logging",
            "- Timeout handling",
            "- Connection pooling",
            "",
            "**Resilience**",
            "- Retry with exponential backoff",
            "- Rate limiting",
            "- Circuit breaker pattern",
            "- Fallback strategies",
            "",
            "**Error Handling**",
            "- HTTP status code mapping",
            "- Custom exception hierarchy",
            "- Error message formatting",
            "- Debug logging"
        ]

        return "\n".join(components)
