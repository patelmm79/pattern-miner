# pattern_miner/a2a/skills/analysis.py
from typing import Dict, Any, List
from pattern_miner.a2a.base import BaseSkill
from pattern_miner.analyzer import PatternAnalyzer  # Existing logic

class AnalyzeRepositorySkill(BaseSkill):
    """Deep pattern analysis of a repository"""

    def __init__(self, analyzer: PatternAnalyzer):
        self.analyzer = analyzer

    @property
    def skill_id(self) -> str:
        return "analyze_repository"

    @property
    def skill_name(self) -> str:
        return "Analyze Repository Patterns"

    @property
    def skill_description(self) -> str:
        return "Perform deep pattern analysis on a GitHub repository to identify reusable code, common patterns, and architectural decisions"

    @property
    def tags(self) -> List[str]:
        return ["analysis", "patterns", "deep-dive"]

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "repository": {
                    "type": "string",
                    "description": "Repository name in format 'owner/repo'"
                },
                "file_paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific file paths to analyze (optional)"
                },
                "focus_areas": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Areas to focus on: deployment, api_clients, config, github_actions"
                },
                "create_github_issue": {
                    "type": "boolean",
                    "description": "Create GitHub issue with findings (default: false)"
                }
            },
            "required": ["repository"]
        }

    @property
    def examples(self) -> List[Dict[str, Any]]:
        return [
            {
                "input": {
                    "repository": "patelmm79/web-scraper",
                    "focus_areas": ["deployment", "api_clients"]
                },
                "description": "Analyze deployment and API client patterns"
            }
        ]

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute pattern analysis"""
        try:
            repository = input_data.get("repository")
            file_paths = input_data.get("file_paths", [])
            focus_areas = input_data.get("focus_areas", [])
            create_issue = input_data.get("create_github_issue", False)

            if not repository:
                return {
                    "success": False,
                    "error": "Missing required field: repository"
                }

            # Use existing analyzer logic
            results = await self.analyzer.analyze(
                repository=repository,
                file_paths=file_paths,
                focus_areas=focus_areas
            )

            # Optionally create GitHub issue
            issue_url = None
            if create_issue and results.get("patterns"):
                issue_url = await self.analyzer.create_extraction_issue(
                    repository=repository,
                    patterns=results["patterns"]
                )

            return {
                "success": True,
                "repository": repository,
                "patterns": results.get("patterns", []),
                "extraction_opportunities": results.get("extraction_opportunities", []),
                "analysis_metadata": {
                    "files_analyzed": results.get("files_analyzed", 0),
                    "patterns_found": len(results.get("patterns", [])),
                    "timestamp": results.get("timestamp")
                },
                "github_issue": issue_url
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Analysis failed: {str(e)}"   }
# pattern_miner/a2a/skills/analysis.py (continued)

class CompareImplementationsSkill(BaseSkill):
    """Compare how different repositories implement a pattern"""

    def __init__(self, analyzer: PatternAnalyzer):
        self.analyzer = analyzer

    @property
    def skill_id(self) -> str:
        return "compare_implementations"

    @property
    def skill_name(self) -> str:
        return "Compare Pattern Implementations"

    @property
    def skill_description(self) -> str:
        return "Compare how multiple repositories implement the same pattern to identify best practices and differences"

    @property
    def tags(self) -> List[str]:
        return ["comparison", "patterns", "best-practices"]

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "repositories": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of repositories to compare"
                },
                "pattern_type": {
                    "type": "string",
                    "description": "Type of pattern to compare (e.g., 'retry_logic', 'error_handling', 'authentication')"
                }
            },
            "required": ["repositories", "pattern_type"]
        }

    @property
    def examples(self) -> List[Dict[str, Any]]:
        return [
            {
                "input": {
                    "repositories": ["patelmm79/web-scraper", "patelmm79/api-client"],
                    "pattern_type": "retry_logic"
                },
                "description": "Compare retry logic implementations across two repos"
            }
        ]

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Compare pattern implementations"""
        try:
            repositories = input_data.get("repositories", [])
            pattern_type = input_data.get("pattern_type")

            if not repositories or len(repositories) < 2:
                return {
                    "success": False,
                    "error": "At least 2 repositories required for comparison"
                }

            if not pattern_type:
                return {
                    "success": False,
                    "error": "Missing required field: pattern_type"
                }

            # Analyze each repository for the specific pattern
            implementations = []
            for repo in repositories:
                analysis = await self.analyzer.analyze(
                    repository=repo,
                    focus_areas=[pattern_type]
                )
                implementations.append({
                    "repository": repo,
                    "patterns": analysis.get("patterns", []),
                    "implementation_details": analysis.get("implementation_details", {})
                })

            # Compare implementations
            comparison = await self.analyzer.compare_patterns(
                implementations=implementations,
                pattern_type=pattern_type
            )

            return {
                "success": True,
                "pattern_type": pattern_type,
                "repositories": repositories,
                "implementations": implementations,
                "comparison": comparison,
                "recommendations": comparison.get("recommendations", [])
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Comparison failed: {str(e)}"
            }

# pattern_miner/a2a/skills/analysis.py (continued)

class GetPatternRecommendationsSkill(BaseSkill):
    """Get pattern recommendations for a repository"""

    def __init__(self, analyzer: PatternAnalyzer):
        self.analyzer = analyzer

    @property
    def skill_id(self) -> str:
        return "get_recommendations"

    @property
    def skill_name(self) -> str:
        return "Get Pattern Recommendations"

    @property
    def skill_description(self) -> str:
        return "Get recommendations for patterns to adopt based on repository context and existing patterns"

    @property
    def tags(self) -> List[str]:
        return ["recommendations", "best-practices"]

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "repository": {
                    "type": "string",
                    "description": "Repository name in format 'owner/repo'"
                },
                "context": {
                    "type": "object",
                    "description": "Context about the repository",
                    "properties": {
                        "primary_language": {"type": "string"},
                        "frameworks": {"type": "array", "items": {"type": "string"}},
                        "deployment_target": {"type": "string"}
                    }
                }
            },
            "required": ["repository", "context"]
        }

    @property
    def examples(self) -> List[Dict[str, Any]]:
        return [
            {
                "input": {
                    "repository": "patelmm79/new-service",
                    "context": {
                        "primary_language": "python",
                        "frameworks": ["fastapi"],
                        "deployment_target": "cloud_run"
                    }
                },
                "description": "Get pattern recommendations for a new Python FastAPI service"
            }
        ]

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get pattern recommendations"""
        try:
            repository = input_data.get("repository")
            context = input_data.get("context", {})

            if not repository:
                return {
                    "success": False,
                    "error": "Missing required field: repository"
                }

            # Get recommendations based on context
            recommendations = await self.analyzer.get_recommendations(
                repository=repository,
                context=context
            )

            return {
                "success": True,
                "repository": repository,
                "recommendations": recommendations,
                "context": context
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to get recommendations: {str(e)}"
            }