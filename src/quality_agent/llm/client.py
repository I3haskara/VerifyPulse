"""
LLM client for generating diagnostic responses.

This module provides integration with various LLM providers:
- Parallel AI
- OpenAI / Anthropic
- Local models

Replace the stub implementation with your actual LLM integration.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict


def llm_generate(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate LLM-powered diagnostic response.
    
    Args:
        payload: Dictionary with 'log' and 'context' keys
            - log: The failure log with test results
            - context: Retrieved code/docs context
            
    Returns:
        Dictionary with diagnosis fields:
            - FailureCategory: Classification of the failure
            - RootCauseSummary: Plain English explanation
            - ReproductionSteps: List of commands to reproduce
            - SuggestedFix: Code snippet or fix instructions
    """
    # Check if OpenAI is available and configured
    openai_key = os.getenv("OPENAI_API_KEY")
    
    if openai_key:
        try:
            return call_openai_llm(payload)
        except Exception as e:
            print(f"[LLM] OpenAI call failed: {e}, falling back to mock")
    
    # Fallback to smart mock
    log = payload.get("log", {})
    return generate_mock_diagnosis(log)


def call_openai_llm(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call OpenAI API for diagnosis using gpt-4o-mini.
    
    Args:
        payload: Dictionary with 'log' and 'context' keys
        
    Returns:
        Parsed JSON diagnosis
    """
    import openai
    
    openai.api_key = os.getenv("OPENAI_API_KEY")
    
    system = """You are an Agentic AI Quality Coach.
Your output MUST be strictly formatted JSON with keys:
FailureCategory, RootCauseSummary, ReproductionSteps, SuggestedFix.

FailureCategory should be one of: Product Bug, Environment Issue, Automation Flaw, Configuration Error
RootCauseSummary should be a clear, plain-English paragraph explaining why the failure occurred
ReproductionSteps should be an array of terminal-ready commands or API calls
SuggestedFix should be a code snippet or step-by-step fix instructions"""

    user = f"""Analyze this failing log and context. 
Return ONLY the JSON object.

{json.dumps(payload, indent=2)}"""

    completion = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ],
    )

    response_text = completion["choices"][0]["message"]["content"]
    return json.loads(response_text)


def call_parallel_llm(system: str, user: str) -> Dict[str, Any]:
    """
    Call Parallel AI API for diagnosis.
    
    TODO: Implement actual Parallel AI integration
    """
    import httpx
    
    api_key = os.getenv("PARALLEL_API_KEY")
    if not api_key:
        raise ValueError("PARALLEL_API_KEY not set")
    
    # TODO: Replace with actual Parallel AI endpoint and format
    response = httpx.post(
        "https://api.parallelai.xyz/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": "gpt-4",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            "response_format": {"type": "json_object"}
        },
        timeout=30.0
    )
    
    result = response.json()
    return json.loads(result["choices"][0]["message"]["content"])


def call_openai_modern(system: str, user: str) -> Dict[str, Any]:
    """
    Call OpenAI API using modern SDK (v1.0+).
    
    Alternative implementation using the new OpenAI client format.
    """
    try:
        from openai import OpenAI
        
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
    except ImportError:
        raise ImportError("openai package not installed. Run: pip install openai")


def call_anthropic_llm(system: str, user: str) -> Dict[str, Any]:
    """
    Call Anthropic Claude API for diagnosis.
    
    TODO: Implement actual Anthropic integration
    """
    import anthropic
    
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    
    response = client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=1024,
        system=system,
        messages=[
            {"role": "user", "content": user}
        ]
    )
    
    return json.loads(response.content[0].text)


def generate_mock_diagnosis(log: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a smart mock diagnosis based on the log content.
    Used as fallback when no LLM is configured.
    """
    status = log.get("status", "unknown")
    failure_reason = log.get("failure_reason", "Unknown failure")
    test_name = log.get("test_name", "unknown_test")
    
    if status == "passed":
        return {
            "FailureCategory": "Success",
            "RootCauseSummary": "All tests passed successfully.",
            "ReproductionSteps": [],
            "SuggestedFix": "No fixes needed.",
        }
    
    # Analyze failure reason for smart categorization
    if "status_code" in failure_reason.lower() or "401" in failure_reason or "404" in failure_reason:
        category = "Product Bug"
        summary = (
            f"Test '{test_name}' failed due to unexpected HTTP status code. "
            f"{failure_reason}. This indicates the API endpoint may not be "
            "properly handling the request or the endpoint implementation is incorrect."
        )
        fix = """Review the endpoint implementation and ensure:
1. The endpoint is registered in the API router
2. HTTP status codes match the API specification
3. Error handling returns appropriate status codes (401 for auth failures, 404 for not found)

Example fix:
```python
@app.post("/login")
def login(payload: LoginRequest, response: Response):
    if not validate_credentials(payload):
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return {"error": "invalid credentials"}
    return {"token": generate_token(payload.username)}
```"""
    elif "json" in failure_reason.lower():
        category = "Product Bug"
        summary = (
            f"Test '{test_name}' expected a JSON response but received a different format. "
            "The API should consistently return JSON for all endpoints."
        )
        fix = """Ensure all API responses use JSONResponse:
```python
from fastapi.responses import JSONResponse

@app.get("/endpoint")
def handler():
    return {"key": "value"}  # FastAPI auto-converts to JSON
```"""
    elif "exception" in failure_reason.lower() or "error" in failure_reason.lower():
        category = "Environment Issue"
        summary = (
            f"Test '{test_name}' encountered an exception: {failure_reason}. "
            "This may indicate network issues, service unavailability, or configuration problems."
        )
        fix = """Check:
1. The API service is running and accessible
2. Network connectivity between test runner and API
3. Environment variables and configuration
4. Service dependencies (database, Redis, etc.)"""
    else:
        category = "Automation Flaw"
        summary = f"Test '{test_name}' failed: {failure_reason}"
        fix = "Review the test implementation and API specification for discrepancies."
    
    # Build reproduction steps
    request_history = log.get("request_history", [])
    steps = []
    for req in request_history:
        method = req.get("method", "GET")
        url = req.get("url", "")
        if method == "GET":
            steps.append(f"curl -X {method} '{url}'")
        else:
            body = req.get("request_body")
            if body:
                steps.append(f"curl -X {method} '{url}' -H 'Content-Type: application/json' -d '{body}'")
            else:
                steps.append(f"curl -X {method} '{url}'")
    
    return {
        "FailureCategory": category,
        "RootCauseSummary": summary,
        "ReproductionSteps": steps if steps else ["Run the test suite against the API"],
        "SuggestedFix": fix,
    }
