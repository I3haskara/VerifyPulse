from __future__ import annotations

from typing import Any, Dict

from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from verifypulse.planner import execute_pipeline
from verifypulse.integrations.redis_client import VerifyPulseRedis
from verifypulse.agent_pipeline import run_full_agent_pipeline


app = FastAPI(
    title="VerifyPulse API",
    version="0.1.0",
    description="VerifyPulse – autonomous API validation agent",
)

# Allow Swagger UI + any local tool to call it
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # for hackathon it's fine
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for dashboard and reports
app.mount("/static", StaticFiles(directory="../"), name="static")


class RunRequest(BaseModel):
    requirement: str
    meta: Dict[str, Any] | None = None


class AgentRunRequest(BaseModel):
    requirement: str
    api_url: str
    collection_id: str
    commit_hash: str = "4a8e2d"


@app.get("/health")
def health_check() -> Dict[str, str]:
    """Health check endpoint for monitoring and testing."""
    return {"status": "healthy", "service": "VerifyPulse"}


class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/login")
def login_endpoint(payload: LoginRequest, response: Response) -> Dict[str, Any]:
    """
    Mock login endpoint for testing purposes.
    
    Returns 401 for wrong credentials, 200 with token for valid ones.
    """
    # Mock authentication logic
    if payload.username == "demo" and payload.password == "hackathon2025":
        return {
            "success": True,
            "token": "mock-jwt-token-abc123",
            "user": {"username": payload.username, "role": "tester"}
        }
    else:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return {
            "success": False,
            "error": "invalid credentials",
            "message": "Username or password is incorrect"
        }


@app.post("/run")
def run_endpoint(payload: RunRequest) -> Dict[str, Any]:
    """
    Accept a natural language requirement and run the full VerifyPulse pipeline.

    - Generates tests & Postman collection
    - Uses Parallel for web context
    - Uses Skyflow to protect PII
    - Persists full run in Redis
    """
    result = execute_pipeline(payload.requirement)
    
    # Save to Redis if we have a collection_id
    if isinstance(result, dict) and "collection_id" in result:
        try:
            redis_client = VerifyPulseRedis()
            redis_client.save_run_result(result["collection_id"], result)
        except Exception as exc:
            print(f"[API] Failed to save run result: {exc!s}")
    
    return result


@app.post("/agent/run")
async def agent_run_endpoint(payload: AgentRunRequest) -> Dict[str, Any]:
    """
    Execute the full Agentic Quality Coach workflow:
    1. Execute Postman collection tests
    2. Generate raw failure logs (with Skyflow tokenization)
    3. RAG-based semantic diagnosis
    4. HTML report generation
    
    Returns diagnostic report with HTML content.
    """
    import asyncio
    
    result = await run_full_agent_pipeline(
        requirement=payload.requirement,
        api_url=payload.api_url,
        collection_id=payload.collection_id,
        commit_hash=payload.commit_hash
    )
    
    return result


@app.get("/history")
def history_endpoint() -> Dict[str, Any]:
    """
    Expose all previous runs from Redis.

    This is great for demo:
    - Shows agent memory
    - Lets judges see that runs persist across calls
    """
    try:
        redis_client = VerifyPulseRedis()
        runs = redis_client.list_run_history()
    except Exception as exc:
        print(f"[API] Failed to read history: {exc!s}")
        runs = []
    
    return {
        "count": len(runs),
        "runs": runs,
    }
