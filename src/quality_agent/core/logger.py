"""
Logger module for persisting raw failure logs and test results.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

from quality_agent.core.native_test_runner import TestRunResult, RequestRecord


def save_raw_failure_log(
    test_result: TestRunResult,
    commit_hash: str,
    run_id: str,
    timestamp: str,
) -> Dict[str, Any]:
    """
    Build and persist the structured JSON failure log.
    
    Args:
        test_result: The test execution result
        commit_hash: Git commit or build identifier
        run_id: Unique run identifier
        timestamp: ISO timestamp of the run
        
    Returns:
        Dictionary containing the failure log structure
    """
    
    def record_to_dict(r: RequestRecord) -> Dict[str, Any]:
        return {
            "method": r.method,
            "url": r.url,
            "request_headers": r.request_headers,
            "request_body": r.request_body,
            "status_code": r.status_code,
            "response_headers": r.response_headers,
            "response_body": r.response_body,
        }
    
    # Build result dictionary based on success/failure
    if test_result.success:
        result = {
            "status": "passed",
            "request_history": [record_to_dict(r) for r in test_result.request_history],
        }
    else:
        failure = test_result.failure
        failed_record = failure.failed_record if failure else None
        
        result = {
            "status": "failed",
            "test_name": failure.test_name if failure else "unknown",
            "failure_reason": failure.reason if failure else "unknown",
            "request_history": [record_to_dict(r) for r in test_result.request_history],
        }
        
        if failed_record:
            result["failing_call"] = {
                "request_data": {
                    "method": failed_record.method,
                    "url": failed_record.url,
                    "headers": failed_record.request_headers,
                    "body": failed_record.request_body,
                },
                "response_data": {
                    "status_code": failed_record.status_code,
                    "headers": failed_record.response_headers,
                    "body": failed_record.response_body,
                },
            }
    
    # Create runs directory
    os.makedirs("runs", exist_ok=True)
    path = f"runs/{run_id}_raw.json"
    
    # Build payload with metadata
    payload = {
        "run_id": run_id,
        "timestamp": timestamp,
        "commit_hash": commit_hash,
        **result
    }
    
    # Write to file
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=4)
    
    print(f"[Logger] Raw failure log saved: {path}")
    
    return payload
