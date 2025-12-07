"""
Base Pattern Miner - Abstract base class for all pattern miners
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List
import anthropic
from github import Github

logger = logging.getLogger(__name__)


class BasePatternMiner(ABC):
    """
    Base class for pattern mining agents.

    Each miner specializes in a specific pattern type (deployment, API clients, etc.)
    """

    def __init__(self, anthropic_client: anthropic.Anthropic, github_client: Github):
        self.anthropic = anthropic_client
        self.github = github_client

    @abstractmethod
    async def mine_patterns(self, repos: List[str]) -> List[Dict]:
        """
        Mine patterns across the given repositories.

        Args:
            repos: List of repository names (e.g., ["owner/repo1", "owner/repo2"])

        Returns:
            List of pattern findings, each containing:
            {
                'pattern_type': str,
                'repos': List[str],
                'similarity_score': float,
                'description': str,
                'recommendation': str,
                'components': str
            }
        """
        pass

    @abstractmethod
    def get_file_patterns(self) -> List[str]:
        """
        Return glob patterns for files to analyze.

        Example: ["deploy*.sh", "cloudbuild.yaml"]
        """
        pass

    async def fetch_files_from_repos(
        self,
        repos: List[str],
        file_patterns: List[str]
    ) -> Dict[str, Dict[str, str]]:
        """
        Fetch matching files from all repositories.

        Args:
            repos: List of repository names
            file_patterns: List of glob patterns

        Returns:
            {
                "owner/repo": {
                    "path/to/file.sh": "file contents...",
                    ...
                },
                ...
            }
        """
        all_files = {}

        for repo_name in repos:
            try:
                repo = self.github.get_repo(repo_name)
                repo_files = {}

                # Search for matching files
                for pattern in file_patterns:
                    try:
                        # GitHub API doesn't support glob, so we search by filename
                        # This is a simplified approach - could be enhanced
                        search_results = self.github.search_code(
                            query=f"filename:{pattern} repo:{repo_name}"
                        )

                        for result in search_results[:10]:  # Limit to 10 files per pattern
                            try:
                                content = result.decoded_content.decode('utf-8')
                                repo_files[result.path] = content
                            except Exception as e:
                                logger.warning(f"Could not decode {result.path}: {e}")

                    except Exception as e:
                        logger.warning(f"Search error for pattern {pattern}: {e}")

                if repo_files:
                    all_files[repo_name] = repo_files
                    logger.info(f"Fetched {len(repo_files)} files from {repo_name}")

            except Exception as e:
                logger.error(f"Error fetching files from {repo_name}: {e}")

        return all_files

    async def analyze_similarity_with_llm(
        self,
        repo_files: Dict[str, Dict[str, str]],
        pattern_type: str
    ) -> List[Dict]:
        """
        Use Claude to analyze similarity across repository files.

        Args:
            repo_files: Files grouped by repository
            pattern_type: Type of pattern being analyzed

        Returns:
            List of similarity findings
        """
        if len(repo_files) < 2:
            logger.info(f"Need at least 2 repos for comparison, got {len(repo_files)}")
            return []

        # Prepare files summary for LLM
        files_summary = {}
        for repo, files in repo_files.items():
            files_summary[repo] = {}
            for path, content in files.items():
                # Truncate content for context limits
                files_summary[repo][path] = content[:3000]

        prompt = f"""You are analyzing {pattern_type} patterns across multiple repositories to identify code reuse opportunities.

**Repositories and Files**:
{self._format_files_for_prompt(files_summary)}

**Your Task**:
Analyze these files to identify:
1. **Common patterns**: What functionality or approaches are duplicated?
2. **Similarity score**: How similar are these implementations (0.0-1.0)?
3. **Reusable components**: What specific code could be extracted?
4. **Extraction recommendation**: How should this be packaged/shared?

**Consider**:
- Are the implementations solving the same problem?
- Is the duplication significant enough to warrant extraction?
- What would a shared library API look like?
- What are the benefits of extraction vs. cost of maintaining shared code?

Respond with JSON in this format:
{{
  "patterns_found": [
    {{
      "repos": ["repo1", "repo2", "repo3"],
      "similarity_score": 0.0-1.0,
      "description": "Brief description of the common pattern",
      "recommendation": "Suggested extraction approach",
      "components": "List of reusable components identified",
      "shared_library_name": "suggested-package-name"
    }}
  ]
}}

Only include patterns with similarity >= 0.70.
"""

        try:
            response = self.anthropic.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                temperature=0.3,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            # Parse response
            content = response.content[0].text

            # Strip markdown code blocks if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            import json
            result = json.loads(content)

            patterns = result.get('patterns_found', [])
            logger.info(f"LLM identified {len(patterns)} similar patterns")

            # Add pattern_type to each finding
            for pattern in patterns:
                pattern['pattern_type'] = pattern_type

            return patterns

        except Exception as e:
            logger.error(f"Error analyzing similarity with LLM: {e}", exc_info=True)
            return []

    def _format_files_for_prompt(self, files_summary: Dict[str, Dict[str, str]]) -> str:
        """Format files for inclusion in LLM prompt"""
        formatted = []
        for repo, files in files_summary.items():
            formatted.append(f"\n**{repo}**:")
            for path, content in files.items():
                formatted.append(f"  File: {path}")
                formatted.append(f"  Content (truncated):\n{content[:1000]}\n")

        return "\n".join(formatted)
