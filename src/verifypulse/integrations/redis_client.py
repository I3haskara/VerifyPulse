"""
Redis Client with In-Memory Fallback
"""
import redis
import json
from typing import Any, Optional, List
from verifypulse.config import load_config


class VerifyPulseRedis:
    """
    Simple key-value wrapper for MVP with optional Redis and in-memory fallback.
    Never crashes if Redis is unavailable.
    """
    
    def __init__(self, url: Optional[str] = None):
        """
        Initialize Redis client with fallback to in-memory store.
        
        Args:
            url: Redis URL (if None, will try to read from config)
        """
        self.use_memory = False
        self._store: dict[str, Any] = {}
        self.client: Optional[redis.Redis] = None
        
        # Get URL from parameter or config
        if url is None:
            try:
                cfg = load_config()
                url = cfg.REDIS_URL
            except Exception:
                url = ""
        
        # If URL is empty, use in-memory store
        if not url or not url.strip():
            self.use_memory = True
            self._store = {}
            print("[Redis] No REDIS_URL set, using in-memory store.")
            return
        
        # Try to connect to Redis
        try:
            self.client = redis.Redis.from_url(url, decode_responses=True)
            # Test connection
            self.client.ping()
            self.use_memory = False
            print(f"[Redis] Connected to {url}.")
        except (redis.ConnectionError, redis.TimeoutError, Exception) as e:
            # Connection failed, fall back to in-memory
            self.use_memory = True
            self._store = {}
            self.client = None
            error_msg = str(e)
            print(f"[Redis] Connection failed, using in-memory store instead: {error_msg}")
    
    def store_requirement(self, requirement_id: str, text: str) -> None:
        """
        Store a requirement as a string value.
        
        Args:
            requirement_id: Key for the requirement
            text: Requirement text to store
        """
        try:
            if self.use_memory:
                self._store[requirement_id] = text
            else:
                if self.client:
                    self.client.set(requirement_id, text)
        except Exception as e:
            # Fallback to memory if Redis operation fails
            print(f"[Redis] Store operation failed, using in-memory: {str(e)}")
            self.use_memory = True
            self._store[requirement_id] = text
    
    def get_requirement(self, requirement_id: str) -> Optional[str]:
        """
        Get a requirement by ID.
        
        Args:
            requirement_id: Key for the requirement
        
        Returns:
            Requirement text or None if not found
        """
        try:
            if self.use_memory:
                return self._store.get(requirement_id)
            else:
                if self.client:
                    result = self.client.get(requirement_id)
                    return result if result else None
                return None
        except Exception as e:
            # Fallback to memory if Redis operation fails
            print(f"[Redis] Get operation failed, using in-memory: {str(e)}")
            self.use_memory = True
            return self._store.get(requirement_id)
    
    def set(self, key: str, value: str) -> None:
        """
        Set a key-value pair (string).
        
        Args:
            key: Key to set
            value: String value to store
        """
        try:
            if self.use_memory:
                self._store[key] = value
            else:
                if self.client:
                    self.client.set(key, value)
        except Exception as e:
            print(f"[Redis] Set operation failed, using in-memory: {str(e)}")
            self.use_memory = True
            self._store[key] = value
    
    def get(self, key: str) -> Optional[str]:
        """
        Get a value by key (string).
        
        Args:
            key: Key to retrieve
        
        Returns:
            String value or None if not found
        """
        try:
            if self.use_memory:
                return self._store.get(key)
            else:
                if self.client:
                    result = self.client.get(key)
                    return result if result else None
                return None
        except Exception as e:
            print(f"[Redis] Get operation failed, using in-memory: {str(e)}")
            self.use_memory = True
            return self._store.get(key)
    
    def keys(self, pattern: str = "*") -> List[str]:
        """
        Get keys matching a pattern.
        
        Args:
            pattern: Pattern to match (e.g., "requirement:*")
        
        Returns:
            List of matching keys
        """
        try:
            if self.use_memory:
                # Simple pattern matching for in-memory store
                if pattern == "*":
                    return list(self._store.keys())
                # Handle simple prefix patterns like "requirement:*"
                if pattern.endswith("*"):
                    prefix = pattern[:-1]
                    return [k for k in self._store.keys() if k.startswith(prefix)]
                return [k for k in self._store.keys() if pattern in k]
            else:
                if self.client:
                    return list(self.client.keys(pattern))
                return []
        except Exception as e:
            print(f"[Redis] Keys operation failed, using in-memory: {str(e)}")
            self.use_memory = True
            # Fallback to in-memory pattern matching
            if pattern == "*":
                return list(self._store.keys())
            if pattern.endswith("*"):
                prefix = pattern[:-1]
                return [k for k in self._store.keys() if k.startswith(prefix)]
            return [k for k in self._store.keys() if pattern in k]

    def save_run_result(self, run_id: str, payload: dict[str, Any]) -> None:
        """
        Store a run result in Redis as JSON.

        - run_id: usually the Postman collection_id
        - payload: full dict returned by the pipeline
        """
        key = f"run:{run_id}"
        try:
            self.set(key, json.dumps(payload))
        except Exception as exc:  # noqa: BLE001
            # Fail soft: log to stdout; the main pipeline must not crash.
            print(f"[Redis] Failed to save run {run_id}: {exc!s}")

    def list_run_history(self) -> List[dict[str, Any]]:
        """
        Retrieve all stored run results.

        Returns a list of dicts. Any corrupted entries are skipped.
        """
        results: List[dict[str, Any]] = []
        try:
            for key in self.keys("run:*"):
                raw = self.get(key)
                if not raw:
                    continue
                try:
                    results.append(json.loads(raw))
                except Exception:
                    continue
        except Exception as exc:  # noqa: BLE001
            print(f"[Redis] Failed to read history: {exc!s}")
        return results
