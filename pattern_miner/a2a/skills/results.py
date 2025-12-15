# pattern_miner/a2a/skills/results.py

class GetAnalysisResultsSkill(BaseSkill):
    """Retrieve stored analysis results"""

    def __init__(self, storage):
        self.storage = storage

    @property
    def skill_id(self) -> str:
        return "get_analysis_results"

    @property
    def skill_name(self) -> str:
        return "Get Analysis Results"

    @property
    def skill_description(self) -> str:
        return "Retrieve previously stored pattern analysis results"

    @property
    def tags(self) -> List[str]:
        return ["results", "history"]

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "repository": {
                    "type": "string",
                    "description": "Repository name (optional, returns all if omitted)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return",
                    "default": 10
                }
            }
        }

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get stored analysis results"""
        try:
            repository = input_data.get("repository")
            limit = input_data.get("limit", 10)

            if repository:
                results = await self.storage.get_by_repository(repository, limit)
            else:
                results = await self.storage.get_recent(limit)

            return {
                "success": True,
                "results": results,
                "count": len(results)
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to retrieve results: {str(e)}"
            }