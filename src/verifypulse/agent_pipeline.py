"""
Agentic Failure Analysis Pipeline for VerifyPulse

This module implements the full Agentic Quality Coach workflow:
1. Execute Postman collection tests
2. Generate raw failure logs (with Skyflow tokenization)
3. RAG-based semantic diagnosis
4. HTML report generation
"""
import json
import time
from typing import Dict, Any, Optional
from verifypulse.integrations.postman_client import PostmanClient
from verifypulse.integrations.skyflow_client import SkyflowClient
from verifypulse.integrations.redis_client import VerifyPulseRedis


class PostmanTestRunner:
    """Executes Postman collection tests and returns structured results."""
    
    def __init__(self, postman_client: PostmanClient):
        """
        Initialize test runner
        
        Args:
            postman_client: PostmanClient instance
        """
        self.postman_client = postman_client
    
    def run_collection(self, api_url: str, collection_id: str) -> Dict[str, Any]:
        """
        Execute a Postman collection against a target API.
        
        In a real implementation, this would use Newman or Postman API's run endpoint.
        For now, this is a mock that simulates test execution.
        
        Args:
            api_url: Base URL of the API to test
            collection_id: Postman collection ID
        
        Returns:
            Structured test result with status, test counts, and failure details
        """
        print(f"[Postman] Executing Collection ID {collection_id} against {api_url}...")
        
        # TODO: Replace with real Postman collection execution via Newman or API
        # For now, simulate a controlled failure for demo scenarios
        if "ssn" in collection_id.lower() or "grades" in collection_id.lower():
            return {
                "status": "FAILED",
                "test_ran": 5,
                "test_failed": 1,
                "failure_details": {
                    "endpoint": "/api/v1/grades",
                    "method": "GET",
                    "error_type": "AssertionError: SSN field is present in response",
                    "full_response": json.dumps({"user_id": 123, "ssn": "123-45-6789"}),
                    "request_headers": {"Authorization": "Bearer token"}
                }
            }
        
        # Default success case
        return {"status": "PASSED", "test_ran": 5, "test_failed": 0}


class LLMAnalyzer:
    """RAG/LLM-based failure diagnosis analyzer."""
    
    def __init__(self, parallel_client=None):
        """
        Initialize LLM analyzer
        
        Args:
            parallel_client: Optional ParallelClient for context retrieval
        """
        self.parallel_client = parallel_client
    
    def _extract_guidelines_from_parallel(self, query: str) -> list:
        """Extract security guidelines from Parallel search results."""
        if not self.parallel_client:
            return []
        
        try:
            result = self.parallel_client.search_web(query, max_tokens=512)
            if result.get("enabled") and result.get("raw"):
                # Extract snippets from Parallel response
                raw_data = result.get("raw", {})
                results = raw_data.get("results", [])
                guidelines = []
                for item in results[:3]:
                    snippet = item.get("snippet", "") or item.get("text", "")
                    if snippet:
                        guidelines.append(snippet)
                return guidelines
        except Exception as e:
            print(f"[Warning] Parallel search failed: {str(e)}")
        
        return []
    
    def diagnose(self, raw_failure_log: Dict[str, Any], commit_hash: str) -> Dict[str, str]:
        """
        Simulates the full RAG process: retrieval, contextual prompting, and structured output.
        
        In a real implementation, this would:
        1. Use Parallel/RAG to retrieve relevant code/docs
        2. Build a contextual prompt
        3. Call an LLM (OpenAI, Anthropic, etc.) for diagnosis
        4. Parse structured output
        
        Args:
            raw_failure_log: Raw failure log from test execution
            commit_hash: Git commit hash for context
        
        Returns:
            Structured diagnosis with category, root cause, steps, and fix
        """
        print("[RAG/AFA] Running RAG/AFA: Retrieving context and generating diagnosis...")
        time.sleep(2)  # Simulate LLM thinking time
        
        # TODO: Replace with real RAG + LLM call
        # This is a mock that demonstrates the expected output structure
        return {
            "FailureCategory": "Product Bug (Security/Data Exposure)",
            "RootCauseSummary": (
                "The grade retrieval endpoint is incorrectly utilizing an outdated serialization "
                "schema. A code merge in commit 4a8e2d reintroduced the 'ssn' field during "
                "database hydration, despite the security policy requiring masking. The RAG "
                "system correlated the failing test log with the code change in `models.py` "
                "and the internal PII policy document."
            ),
            "ReproductionSteps": (
                "curl -X GET 'https://api.prod/v1/grades?user=123' -H 'Authorization: Bearer token'"
            ),
            "SuggestedFix": (
                "File: models.py, Line 78. Change `include_ssn=True` to `include_ssn=False` "
                "in the user schema serializer."
            )
        }


def generate_html_report(diagnosis: Dict[str, str], raw_log: Dict[str, Any]) -> str:
    """
    Converts the structured diagnosis into a human-readable HTML report.
    
    Includes specialized styling for the Postman Value Proposition (UI Sync).
    
    Args:
        diagnosis: Diagnosis dictionary from LLM analyzer
        raw_log: Raw failure log from test execution
    
    Returns:
        HTML report as string
    """
    current_time_str = time.strftime('%Y-%m-%d %H:%M:%S')
    
    # Extract failure details safely
    failure_details = raw_log.get("test_result", {}).get("failure_details", {})
    endpoint = failure_details.get("endpoint", "Unknown")
    agent_version = raw_log.get("agent_version", "1.0.0")
    
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Agentic Failure Analysis Report</title>
    <style>
        body {{ font-family: 'Inter', sans-serif; background-color: #f7f7f7; padding: 20px; }}
        .container {{ max-width: 900px; margin: auto; background: #ffffff; padding: 30px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
        .header {{ border-bottom: 2px solid #10b981; padding-bottom: 15px; margin-bottom: 25px; }}
        .category {{ font-size: 1.5rem; font-weight: 700; color: #10b981; margin-bottom: 10px; }}
        .section-title {{ font-size: 1.25rem; font-weight: 600; color: #333; margin-top: 20px; margin-bottom: 10px; padding-left: 10px; border-left: 4px solid #10b981; }}
        pre {{ background: #1e293b; color: #f8fafc; padding: 15px; border-radius: 6px; overflow-x: auto; font-size: 0.875rem; }}
        code {{ font-family: monospace; }}
        .alert {{ padding: 10px 15px; background: #fee2e2; color: #dc2626; border-radius: 6px; margin-top: 10px; }}
        .value-prop {{ border: 2px solid #3b82f6; background-color: #eff6ff; padding: 15px; border-radius: 8px; margin-bottom: 20px; color: #1e40af; font-weight: 600; }}
    </style>
</head>
<body>
    <div class="container">
        
        <div class="value-prop">
            🎯 **Postman Value Proposition:** This report eliminates the 13 hours of manual debugging (reproduction, RCA) you would normally spend on your failing Postman test.
        </div>

        <div class="header">
            <h1 style="font-size: 2rem; color: #1f2937;">Automated Failure Analysis (AFA) Report</h1>
            <p style="color: #6b7280;">Generated from a failing **Postman Run** by VerifyPulse Agent (v{agent_version}) at {current_time_str}</p>
        </div>

        <div class="category">FAILURE CATEGORY: {diagnosis.get('FailureCategory', 'Unknown')}</div>

        <div class="section-title">Root Cause Summary (The "Why" - RAG Powered)</div>
        <p>{diagnosis.get('RootCauseSummary', 'No summary available')}</p>

        <div class="section-title">Suggested Fix (Code-Level Recommendation)</div>
        <pre><code>{diagnosis.get('SuggestedFix', 'No fix suggested')}</code></pre>

        <div class="section-title">Reproduction Steps (The 41% Solution)</div>
        <p style="color: #4b5563; font-style: italic;">Use this command to verify the fix in your local terminal (or re-run your Postman collection after fix):</p>
        <pre><code>{diagnosis.get('ReproductionSteps', 'No steps provided')}</code></pre>
        
        <div class="section-title">Raw Log Context</div>
        <div class="alert">Test Run ID: {raw_log.get('commit_hash', 'Unknown')} | Endpoint: {endpoint}</div>
        <pre><code>{json.dumps(failure_details, indent=2)}</code></pre>

    </div>
</body>
</html>
    """
    
    return html_content


async def run_full_agent_pipeline(
    requirement: str,
    api_url: str,
    collection_id: str,
    commit_hash: str = "4a8e2d",
    postman_client: Optional[PostmanClient] = None,
    skyflow_client: Optional[SkyflowClient] = None,
    redis_client: Optional[VerifyPulseRedis] = None
) -> Dict[str, Any]:
    """
    Executes the full Agentic Quality Coach workflow (Modules 1, 2, 3).
    
    Args:
        requirement: Original requirement text
        api_url: Base URL of the API to test
        collection_id: Postman collection ID to execute
        commit_hash: Git commit hash for context
        postman_client: Optional PostmanClient (creates new if not provided)
        skyflow_client: Optional SkyflowClient for PII tokenization
        redis_client: Optional RedisClient for storing logs
    
    Returns:
        Dictionary with status, diagnostic summary, and HTML report
    """
    from verifypulse.config import load_config
    
    # Initialize clients if not provided
    if postman_client is None:
        cfg = load_config()
        postman_client = PostmanClient(cfg.POSTMAN_API_KEY)
    
    if skyflow_client is None:
        cfg = load_config()
        skyflow_client = SkyflowClient(
            vault_id=cfg.SKYFLOW_VAULT_ID,
            api_token=cfg.SKYFLOW_API_TOKEN
        )
    
    if redis_client is None:
        cfg = load_config()
        redis_client = VerifyPulseRedis(cfg.REDIS_URL)
    
    # Initialize components
    test_runner = PostmanTestRunner(postman_client)
    llm_analyzer = LLMAnalyzer()
    
    # 1. Execute Test Sequence (Postman Validation)
    print(f"[Agent] Executing Postman collection {collection_id}...")
    test_result = test_runner.run_collection(api_url, collection_id)
    
    # 2. Handle success case
    if test_result.get("status") == "PASSED":
        return {
            "status": "PASSED",
            "summary": "All tests passed. No failure log generated for diagnosis.",
            "html_report_content": ""
        }
    
    # 3. Generate Raw Failure Log (with Skyflow tokenization for PII)
    print("[Agent] Generating raw failure log with PII tokenization...")
    
    # Tokenize any PII in the failure response
    failure_response = test_result.get("failure_details", {}).get("full_response", "")
    tokenized_response = failure_response
    
    if failure_response:
        try:
            # Try to parse and tokenize PII fields
            response_data = json.loads(failure_response)
            pii_fields = {}
            
            # Identify PII fields
            for key, value in response_data.items():
                if key.lower() in ["ssn", "email", "phone", "credit_card"]:
                    pii_fields[key] = value
            
            if pii_fields:
                tokenize_result = skyflow_client.tokenize_record(pii_fields)
                if tokenize_result.get("enabled") and tokenize_result.get("tokenized"):
                    # Replace PII with tokens in response
                    for key, token in tokenize_result["tokenized"].items():
                        response_data[key] = token
                    tokenized_response = json.dumps(response_data)
                    print(f"[Skyflow] Tokenized {len(pii_fields)} PII fields in failure log")
        except Exception as e:
            print(f"[Warning] Failed to tokenize PII in failure log: {str(e)}")
    
    raw_failure_log = {
        "timestamp": time.time(),
        "commit_hash": commit_hash,
        "test_result": test_result,
        "requirement_tested": requirement,
        "agent_version": "1.0.0",
        "tokenized_response": tokenized_response  # Store tokenized version
    }
    
    # 4. RAG for Semantic Diagnosis
    print("[Agent] Running RAG/AFA diagnosis...")
    diagnostic_report_json = llm_analyzer.diagnose(raw_failure_log, commit_hash)
    
    # 5. Generate Final HTML Report
    print("[Agent] Generating HTML report...")
    html_report = generate_html_report(diagnostic_report_json, raw_failure_log)
    
    # 6. Save to Redis (for /history endpoint)
    try:
        log_key = f"failure_log:{commit_hash}:{int(time.time())}"
        redis_client.set(log_key, json.dumps(raw_failure_log))
        print(f"[Redis] Saved failure log to {log_key}")
    except Exception as e:
        print(f"[Warning] Failed to save to Redis: {str(e)}")
    
    return {
        "status": "FAILURE_DIAGNOSED",
        "diagnostic_summary": diagnostic_report_json.get("RootCauseSummary", ""),
        "html_report_content": html_report,
        "diagnosis": diagnostic_report_json,
        "raw_log": raw_failure_log
    }

