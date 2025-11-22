"""
RAG (Retrieval-Augmented Generation) + AFA (Automated Failure Analysis) pipeline.
Retrieves code/docs context and uses LLM for intelligent diagnosis.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    import redis  # type: ignore
    from redisvl.query import VectorQuery  # type: ignore
    REDISVL_AVAILABLE = True
except ImportError:
    redis = None
    VectorQuery = None  # type: ignore
    REDISVL_AVAILABLE = False

from quality_agent.llm import llm_generate


class VectorDBClient:
    """
    Thin abstraction over Vector DB for semantic code/docs retrieval.
    """

    def __init__(self, url: str | None = None):
        self.url = url or os.getenv("REDIS_URL")
        self.enabled = redis is not None and self.url is not None

        self._client = None
        if self.enabled:
            try:
                self._client = redis.from_url(self.url)  # type: ignore
            except Exception:
                self.enabled = False

    def index_name(self, base: str, commit_hash: str) -> str:
        return f"{base}:{commit_hash}"

    def upsert_embeddings(
        self,
        index_name: str,
        items: List[Tuple[str, str]],
    ) -> None:
        """Upsert embeddings into the VDB (stub for now)."""
        if not self.enabled or self._client is None:
            return

        for item_id, text in items:
            key = f"{index_name}:{item_id}"
            self._client.set(key, text)  # type: ignore

    def query_vector(
        self,
        index_name: str,
        query_text: str,
        return_fields: List[str],
        filter_expr: Dict[str, Any] | None = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Perform vector similarity search using RedisVL VectorQuery.
        
        Args:
            index_name: Name of the vector index
            query_text: Text to search for
            return_fields: Fields to return in results
            filter_expr: Optional filter expression
            top_k: Number of results to return
            
        Returns:
            List of search results
        """
        if not REDISVL_AVAILABLE or not self.enabled or self._client is None:
            return []
        
        try:
            # TODO: Implement actual VectorQuery when RedisVL indices are created
            # For now, return empty list
            # Example:
            # query = VectorQuery.from_text(
            #     query_text,
            #     return_fields=return_fields,
            #     filter=filter_expr,
            #     top_k=top_k
            # )
            # results = index.query(query)
            return []
        except Exception as e:
            print(f"[VDB] Query error: {e}")
            return []

    def search(
        self,
        index_name: str,
        query_text: str,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Semantic search stub (legacy)."""
        if not self.enabled or self._client is None:
            return []
        return []


def ingest_code_and_docs(
    vdb: VectorDBClient,
    code_dir: Path,
    docs_dir: Path,
    commit_hash: str,
) -> None:
    """
    Walk code_dir and docs_dir, collect text, and upsert into VDB indices.
    """
    code_index = vdb.index_name("code_index", commit_hash)
    doc_index = vdb.index_name("doc_index", commit_hash)

    code_items: List[Tuple[str, str]] = []
    doc_items: List[Tuple[str, str]] = []

    # --- Ingest code files --------------------------------------------------
    if code_dir.exists():
        for path in code_dir.rglob("*"):
            if path.is_file() and path.suffix in {".py", ".js", ".ts", ".go", ".java"}:
                try:
                    text = path.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue
                item_id = str(path.relative_to(code_dir))
                code_items.append((item_id, text))

    # --- Ingest docs --------------------------------------------------------
    if docs_dir.exists():
        for path in docs_dir.rglob("*"):
            if path.is_file() and path.suffix.lower() in {".md", ".txt"}:
                try:
                    text = path.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue
                item_id = str(path.relative_to(docs_dir))
                doc_items.append((item_id, text))

    vdb.upsert_embeddings(code_index, code_items)
    vdb.upsert_embeddings(doc_index, doc_items)


def retrieve_context(
    error_log: Dict[str, Any],
    commit_hash: str,
    vdb: VectorDBClient | None = None,
    top_k: int = 5,
) -> Dict[str, Any]:
    """
    Hybrid retrieval over code and docs based on error_log.
    
    Uses RedisVL's VectorQuery for semantic search if available.
    
    Args:
        error_log: The failure log to query against
        commit_hash: Git commit for filtering results
        vdb: Optional VectorDBClient instance
        top_k: Number of results to return
        
    Returns:
        Dictionary with code and docs results
    """
    # Build query text from error log
    query_text = json.dumps(error_log, ensure_ascii=False)
    
    # If RedisVL is available, use VectorQuery
    if REDISVL_AVAILABLE and vdb and vdb.enabled:
        try:
            # Semantic search in code_index
            code_results = vdb.query_vector(
                index_name="code_index",
                query_text=query_text,
                return_fields=["filepath", "content", "commit_hash"],
                filter_expr={"commit_hash": commit_hash},
                top_k=top_k
            )
            
            # Semantic search in doc_index
            doc_results = vdb.query_vector(
                index_name="doc_index",
                query_text=query_text,
                return_fields=["title", "content"],
                filter_expr=None,
                top_k=top_k
            )
            
            return {
                "code": code_results,
                "docs": doc_results
            }
        except Exception as e:
            print(f"[RAG] Vector search failed: {e}")
    
    # Fallback to simple search
    code_index = vdb.index_name("code_index", commit_hash) if vdb else ""
    doc_index = vdb.index_name("doc_index", commit_hash) if vdb else ""

    code_hits = vdb.search(code_index, query_text, top_k=top_k) if vdb else []
    doc_hits = vdb.search(doc_index, query_text, top_k=top_k) if vdb else []

    return {
        "code": code_hits,
        "docs": doc_hits
    }


def build_llm_prompt(
    failure_log: Dict[str, Any],
    context: Dict[str, List[Dict[str, Any]]],
) -> str:
    """
    Construct LLM prompt with failure log and retrieved context.
    """
    instructions = {
        "task": "Automated Failure Analysis (AFA) for API test failures.",
        "schema": {
            "FailureCategory": 'string, e.g. "Product Bug", "Environment Issue", "Automation Flaw"',
            "RootCauseSummary": "string, plain-English paragraph describing why the failure occurred.",
            "ReproductionSteps": "array of strings, terminal-ready commands or API calls.",
            "SuggestedFix": "string, code snippet OR file path + line reference.",
        },
    }

    prompt = {
        "instructions": instructions,
        "failure_log": failure_log,
        "retrieved_context": context,
    }
    return json.dumps(prompt, ensure_ascii=False, indent=2)


def llm_generate(prompt: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call LLM provider for intelligent diagnosis.
    
    TODO: Replace with real LLM integration (Parallel AI, Anthropic, etc.)
    
    Args:
        prompt: Dictionary with 'log' and 'context' keys
        
    Returns:
        Diagnosis dictionary with category, summary, steps, and fix
    """
    # Extract log and context
    log = prompt.get("log", {})
    context = prompt.get("context", {})
    
    # TODO: Build actual LLM prompt and call API
    # Example:
    # from llm.client import call_llm
    # response = call_llm({
    #     "system": "You are an expert QA engineer diagnosing API failures.",
    #     "user": json.dumps(prompt),
    #     "response_format": {"type": "json_object"}
    # })
    # return json.loads(response.content)
    
    # Mocked response for now
    failure_reason = log.get("failure_reason", "Unknown failure")
    test_name = log.get("test_name", "unknown_test")
    
    return {
        "FailureCategory": "Product Bug",
        "RootCauseSummary": (
            f"Test '{test_name}' failed: {failure_reason}. "
            "This indicates the API implementation may not be following the expected contract."
        ),
        "ReproductionSteps": [
            "curl -X GET '<API_BASE_URL>/health'",
            "curl -X POST '<API_BASE_URL>/login' -H 'Content-Type: application/json' "
            "-d '{\"username\": \"test_user\", \"password\": \"wrong_password\"}'",
        ],
        "SuggestedFix": (
            "Ensure all error branches return proper HTTP status codes (401 for auth failures) "
            "and JSON response bodies. Example:\n\n"
            "response.status_code = status.HTTP_401_UNAUTHORIZED\n"
            "return {'error': 'invalid credentials'}"
        ),
    }


def call_llm_for_diagnosis(prompt: str) -> Dict[str, Any]:
    """
    Legacy function for backward compatibility.
    Calls llm_generate with converted prompt.
    """
    try:
        prompt_dict = json.loads(prompt)
    except:
        prompt_dict = {"log": {}, "context": {}}
    
    return llm_generate(prompt_dict)


def run_rag_diagnosis(
    raw_log: Dict[str, Any],
    commit_hash: str,
) -> Dict[str, Any]:
    """
    Main RAG + AFA pipeline.
    
    1. Initialize VDB client
    2. Ingest code/docs (if VDB available)
    3. Retrieve semantic context for failure
    4. Call LLM for diagnosis
    
    Returns:
        Diagnosis dictionary with category, root cause, steps, and fix
    """
    print("[RAG] Starting RAG + AFA diagnosis pipeline...")
    
    # Only run diagnosis for failures
    if raw_log.get("status") == "passed":
        return {
            "FailureCategory": "Success",
            "RootCauseSummary": "All tests passed successfully.",
            "ReproductionSteps": [],
            "SuggestedFix": "No fixes needed.",
        }
    
    vdb = VectorDBClient()
    
    if vdb.enabled:
        print("[RAG] Vector DB detected. Ingesting code/docs...")
        code_dir = Path("src/verifypulse").resolve()
        docs_dir = Path("docs").resolve()
        ingest_code_and_docs(vdb, code_dir, docs_dir, commit_hash)
        
        # Use new retrieve_context signature
        context = retrieve_context(raw_log, commit_hash, vdb)
        print(f"[RAG] Retrieved {len(context.get('code', []))} code snippets, "
              f"{len(context.get('docs', []))} doc snippets")
    else:
        print("[RAG] ⚠️  No Vector DB configured. Proceeding without semantic context.")
        context = {"code": [], "docs": []}
    
    # Build prompt with log and context
    prompt = {
        "log": raw_log,
        "context": context
    }
    
    # Call LLM for diagnosis
    diagnosis = llm_generate(prompt)
    
    print("[RAG] ✅ Diagnosis complete")
    return diagnosis
