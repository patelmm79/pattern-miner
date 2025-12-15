# pattern_miner/a2a/server.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import logging

from pattern_miner.a2a.registry import get_registry
from pattern_miner.a2a.skills.analysis import (
    AnalyzeRepositorySkill,
    CompareImplementationsSkill,
    GetPatternRecommendationsSkill
)
from pattern_miner.a2a.skills.results import GetAnalysisResultsSkill
from pattern_miner.analyzer import PatternAnalyzer
from pattern_miner.storage import Storage
from pattern_miner.config import load_config

# Load configuration
config = load_config()

# Initialize services
analyzer = PatternAnalyzer(config)
storage = Storage(config)

# Initialize skill registry
registry = get_registry()

# Register all skills
registry.register(AnalyzeRepositorySkill(analyzer))
registry.register(CompareImplementationsSkill(analyzer))
registry.register(GetPatternRecommendationsSkill(analyzer))
registry.register(GetAnalysisResultsSkill(storage))

# Create FastAPI app
app = FastAPI(
    title="Pattern Miner A2A Agent",
    description="Deep pattern analysis and comparison across GitHub repositories",
    version="2.0.0"
)

logger = logging.getLogger("pattern_miner")


# Startup event to initialize database connection
@app.on_event("startup")
async def startup_event():
    await storage.initialize()
    logger.info("Pattern Miner A2A Agent started")


# Shutdown event to close database connection
@app.on_event("shutdown")
async def shutdown_event():
    await storage.close()
    logger.info("Pattern Miner A2A Agent shutdown")


@app.get("/.well-known/agent.json")
async def get_agent_card():
    """Publish AgentCard at well-known location"""
    agent_card = {
        "name": "pattern_miner",
        "description": "Deep pattern analysis and comparison across GitHub repositories using Claude AI",
        "version": "2.0.0",
        "url": config.agent_url,
        "capabilities": {
            "streaming": False,
            "multimodal": False,
            "authentication": "optional"
        },
        "skills": registry.to_agent_card_skills(),
        "metadata": {
            "repository": "patelmm79/pattern-miner",
            "focus_areas": [
                "deployment_patterns",
                "api_clients",
                "configuration_management",
                "github_actions",
                "error_handling",
                "retry_logic"
            ],
            "supported_languages": ["python", "javascript", "typescript", "go"],
            "integration_partners": {
                "dev-nexus": "Coordinates with Pattern Discovery Agent for knowledge base updates"
            }
        }
    }

    return JSONResponse(content=agent_card)


@app.post("/a2a/execute")
async def execute_task(request: Request):
    """Handle A2A task execution"""
    try:
        body = await request.json()
        skill_id = body.get("skill_id")
        input_data = body.get("input", {})

        if not skill_id:
            return JSONResponse(
                status_code=400,
                content={"error": "Missing required field: skill_id"}
            )

        # Get skill from registry
        skill = registry.get_skill(skill_id)
        if not skill:
            return JSONResponse(
                status_code=404,
                content={"error": f"Skill not found: {skill_id}"}
            )

        # Execute skill
        result = await skill.execute(input_data)

        return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"Execution failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Execution failed: {str(e)}"}
        )


@app.post("/a2a/cancel")
async def cancel_task(request: Request):
    """Handle A2A task cancellation"""
    try:
        body = await request.json()
        task_id = body.get("task_id")

        if not task_id:
            return JSONResponse(
                status_code=400,
                content={"error": "Missing required field: task_id"}
            )

        # Pattern-miner doesn't support long-running tasks yet
        return JSONResponse(
            content={
                "success": False,
                "message": "Task cancellation not supported"
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Cancellation failed: {str(e)}"}
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "pattern-miner",
        "version": "2.0.0",
        "skills_registered": len(registry.get_skill_ids()),
        "skills": registry.get_skill_ids()
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Pattern Miner A2A Agent",
        "version": "2.0.0",
        "agent_card": f"{config.agent_url}/.well-known/agent.json",
        "health": f"{config.agent_url}/health",
        "endpoints": {
            "execute": "/a2a/execute",
            "cancel": "/a2a/cancel",
            "agent_card": "/.well-known/agent.json",
            "health": "/health"
        },
        "skills_registered": len(registry.get_skill_ids()),
        "skills": registry.get_skill_ids()
    }


if __name__ == "__main__":
    import uvicorn
    port = config.port
    print(f"Starting Pattern Miner A2A Agent on port {port}")
    print(f"AgentCard: http://localhost:{port}/.well-known/agent.json")
    print(f"Skills: {', '.join(registry.get_skill_ids())}")
    uvicorn.run(app, host="0.0.0.0", port=port)