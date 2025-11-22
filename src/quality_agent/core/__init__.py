"""
Core modules for the Quality Agent.
"""

from .native_test_runner import run_native_tests, TestRunResult, TestFailure, RequestRecord
from .logger import save_raw_failure_log
from .rag_pipeline import run_rag_diagnosis
from .html_report import generate_html_report

__all__ = [
    "run_native_tests",
    "TestRunResult",
    "TestFailure",
    "RequestRecord",
    "save_raw_failure_log",
    "run_rag_diagnosis",
    "generate_html_report",
]
