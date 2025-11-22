"""
Path: src/quality_agent/agent_runner.py

Agentic AI Quality Coach
========================
Autonomous diagnostic pipeline orchestrator.

Coordinates:
  1. Native test execution (no GUI / Newman)
  2. RAG-based context retrieval
  3. LLM-powered automated failure analysis
  4. HTML report generation
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
import uuid
from pathlib import Path
from typing import Any, Dict

from quality_agent.core import (
    run_native_tests,
    save_raw_failure_log,
    run_rag_diagnosis,
    generate_html_report,
)


def run_agent(api_url: str, commit_hash: str) -> Dict[str, Any]:
    """
    Main autonomous diagnostic pipeline.
    
    Args:
        api_url: Base URL of the API service under test
        commit_hash: Git commit or build identifier
        
    Returns:
        Dictionary with run_id, report_path, and diagnosis
    """
    run_id = str(uuid.uuid4())
    timestamp = dt.datetime.now(dt.UTC).isoformat()

    print(f"\n{'='*70}")
    print(f"[VerifyPulse] Starting Autonomous Diagnostic Run")
    print(f"{'='*70}")
    print(f"  Run ID:     {run_id}")
    print(f"  Target API: {api_url}")
    print(f"  Commit:     {commit_hash}")
    print(f"  Timestamp:  {timestamp}")
    print(f"{'='*70}\n")

    # 1. Native test execution (no GUI, no Newman)
    print("[Step 1/4] Running native API tests...")
    test_result = run_native_tests(api_url)
    
    if test_result.success:
        print("✅ All tests passed!")
    else:
        print(f"❌ Test failure detected: {test_result.failure.test_name if test_result.failure else 'unknown'}")

    # 2. Persist raw log
    print("\n[Step 2/4] Persisting raw failure log...")
    raw_log = save_raw_failure_log(test_result, commit_hash, run_id, timestamp)

    # 3. RAG + AFA diagnosis
    print("\n[Step 3/4] Running RAG + AFA diagnosis...")
    diagnosis = run_rag_diagnosis(raw_log, commit_hash)

    # 4. Generate final HTML report
    print("\n[Step 4/4] Generating HTML report...")
    report_path = generate_html_report(run_id, diagnosis, raw_log)

    print(f"\n{'='*70}")
    print(f"[✔] Autonomous Run Complete!")
    print(f"{'='*70}")
    print(f"  Report:     {report_path}")
    print(f"  Category:   {diagnosis.get('FailureCategory', 'Unknown')}")
    print(f"  Status:     {'Success' if test_result.success else 'Failure'}")
    print(f"{'='*70}\n")
    
    return {
        "run_id": run_id,
        "report_path": report_path,
        "diagnosis": diagnosis,
        "success": test_result.success,
    }


def main() -> None:
    """
    CLI entry point for CI/CD and local runs.

    Example use:
        python -m quality_agent.agent_runner \\
            --api-url http://127.0.0.1:8000 \\
            --commit-hash abc123

    Or via script arguments:
        python -m quality_agent.agent_runner http://127.0.0.1:8000 abc123
    """
    parser = argparse.ArgumentParser(
        description="VerifyPulse Agentic AI Quality Coach – Autonomous Diagnostic Runner"
    )
    parser.add_argument(
        "--api-url",
        help="Base URL of the API service under test (e.g., http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--commit-hash",
        help="Commit hash or version tag of the build being tested.",
    )

    # Also support positional arguments for simpler invocation
    parser.add_argument(
        "positional_api_url",
        nargs="?",
        help="API URL (positional argument alternative)",
    )
    parser.add_argument(
        "positional_commit_hash",
        nargs="?",
        help="Commit hash (positional argument alternative)",
    )

    args = parser.parse_args()

    # Determine API URL and commit hash from either named or positional args
    api_url = args.api_url or args.positional_api_url
    commit_hash = args.commit_hash or args.positional_commit_hash

    if not api_url or not commit_hash:
        parser.error("Both API URL and commit hash are required (use --api-url and --commit-hash, or pass as positional args)")

    # Run the autonomous diagnostic pipeline
    result = run_agent(api_url, commit_hash)
    
    # Exit with appropriate code
    exit_code = 0 if result["success"] else 1
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
