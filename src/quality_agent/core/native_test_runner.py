"""
Core module for native test execution without GUI or Newman.
Runs API tests directly via httpx and captures full request/response data.
"""

from __future__ import annotations

import dataclasses
from typing import Any, Dict, List, Optional

import httpx

from .test_cases import load_test_cases


@dataclasses.dataclass
class RequestRecord:
    """Captures one HTTP interaction in the test run."""

    method: str
    url: str
    request_headers: Dict[str, Any]
    request_body: Any
    status_code: int
    response_headers: Dict[str, Any]
    response_body: Any


@dataclasses.dataclass
class TestFailure:
    """Represents a failing test in the suite."""

    test_name: str
    reason: str
    failed_record: RequestRecord


@dataclasses.dataclass
class TestRunResult:
    """Encapsulates the overall result of a test run."""

    success: bool
    request_history: List[RequestRecord]
    failure: Optional[TestFailure] = None


def run_native_tests(api_base_url: str) -> TestRunResult:
    """
    Core test runner - executes tests natively via httpx.
    
    - No GUI / Newman dependencies
    - Records full request/response for every call
    - Stops on the *first* failing assertion
    - Flexible test case structure
    
    Returns:
        TestRunResult with success status and full interaction history
    """
    history: List[RequestRecord] = []
    client = httpx.Client(timeout=10.0)

    def record_and_return(
        response: httpx.Response | None,
        method: str,
        url: str,
        request_body: Any,
        exception: Exception | None = None
    ) -> RequestRecord:
        """Helper to create a RequestRecord from response or exception."""
        if response is not None:
            req = response.request
            try:
                req_body = req.content.decode("utf-8") if req.content else None
            except Exception:
                req_body = "<binary>"

            try:
                resp_body = response.json()
            except Exception:
                resp_body = response.text

            record = RequestRecord(
                method=req.method,
                url=str(req.url),
                request_headers=dict(req.headers),
                request_body=req_body,
                status_code=response.status_code,
                response_headers=dict(response.headers),
                response_body=resp_body,
            )
        else:
            # Exception case
            record = RequestRecord(
                method=method,
                url=url,
                request_headers={},
                request_body=request_body,
                status_code=0,
                response_headers={},
                response_body=str(exception) if exception else "Unknown error",
            )
        
        history.append(record)
        return record

    # Load test cases from configuration
    test_cases = load_test_cases()

    # Execute test cases
    for test in test_cases:
        test_name = test["name"]
        method = test["method"]
        url = f"{api_base_url.rstrip('/')}{test['endpoint']}"
        payload = test["payload"]
        expected_status = test["expected_status"]
        requires_json = test.get("requires_json", False)

        try:
            # Make HTTP request
            if method.upper() == "GET":
                resp = client.get(url)
            elif method.upper() == "POST":
                resp = client.post(url, json=payload)
            elif method.upper() == "PUT":
                resp = client.put(url, json=payload)
            elif method.upper() == "DELETE":
                resp = client.delete(url)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            rec = record_and_return(resp, method, url, payload)

            # Check status code
            if resp.status_code not in expected_status:
                expected_str = " or ".join(str(s) for s in expected_status)
                reason = f"Expected {expected_str} from {test['endpoint']}, got {resp.status_code}"
                client.close()
                return TestRunResult(
                    success=False,
                    request_history=history,
                    failure=TestFailure(test_name=test_name, reason=reason, failed_record=rec),
                )

            # Check JSON body if required
            if requires_json and not isinstance(rec.response_body, (dict, list)):
                reason = f"Expected JSON response from {test['endpoint']}"
                client.close()
                return TestRunResult(
                    success=False,
                    request_history=history,
                    failure=TestFailure(test_name=test_name, reason=reason, failed_record=rec),
                )

        except Exception as exc:
            rec = record_and_return(None, method, url, payload, exc)
            reason = f"Exception calling {test['endpoint']}: {exc!r}"
            client.close()
            return TestRunResult(
                success=False,
                request_history=history,
                failure=TestFailure(test_name=test_name, reason=reason, failed_record=rec),
            )

    # All tests passed
    client.close()
    return TestRunResult(success=True, request_history=history, failure=None)
