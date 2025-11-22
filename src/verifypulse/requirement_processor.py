"""
Requirement Processor for Natural Language Requirements
"""
from typing import Dict, Any, Optional
from datetime import datetime
import json
from verifypulse.test_plan import TestPlan, TestPlanGenerator
from verifypulse.integrations import RedisClient


class RequirementProcessor:
    """Processes natural language requirements and generates test plans"""
    
    def __init__(self, redis_client: Optional[RedisClient] = None):
        """
        Initialize requirement processor
        
        Args:
            redis_client: Optional Redis client for storage (creates new if not provided)
        """
        self.test_plan_generator = TestPlanGenerator()
        self.redis_client = redis_client or RedisClient()
    
    def process_requirement(
        self,
        requirement: str,
        requirement_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a natural language requirement and generate test plan
        
        Args:
            requirement: Natural language requirement
            requirement_id: Optional requirement ID
        
        Returns:
            Dictionary with requirement_id, test_plan, and status
        """
        # Generate test plan
        test_plan = self.test_plan_generator.generate(requirement, requirement_id)
        
        # Store in Redis
        self._store_requirement(test_plan)
        
        return {
            "requirement_id": test_plan.requirement_id,
            "requirement_text": test_plan.requirement_text,
            "test_plan": test_plan.model_dump(),
            "status": "generated",
            "endpoints_count": len(test_plan.endpoints),
            "test_cases_count": sum(len(ep.test_cases) for ep in test_plan.endpoints)
        }
    
    def get_requirement_history(self, requirement_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get requirement history from Redis
        
        Args:
            requirement_id: Optional requirement ID (returns all if not provided)
        
        Returns:
            Requirement history
        """
        if requirement_id:
            # Get specific requirement
            key = f"requirement:{requirement_id}"
            data = self.redis_client.get(key)
            if data:
                return json.loads(data)
            return {}
        else:
            # Get all requirements
            pattern = "requirement:*"
            keys = self.redis_client.keys(pattern)
            requirements = {}
            for key in keys:
                req_id = key.split(":")[1]
                data = self.redis_client.get(key)
                if data:
                    requirements[req_id] = json.loads(data)
            return requirements
    
    def _store_requirement(self, test_plan: TestPlan):
        """Store requirement and test plan in Redis"""
        key = f"requirement:{test_plan.requirement_id}"
        
        # Store full test plan
        data = {
            "requirement_id": test_plan.requirement_id,
            "requirement_text": test_plan.requirement_text,
            "test_plan": test_plan.model_dump(),
            "created_at": test_plan.created_at.isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        self.redis_client.set(key, json.dumps(data))
        
        # Also store in history
        history_key = f"history:{test_plan.requirement_id}"
        history_data = {
            "requirement_id": test_plan.requirement_id,
            "events": [
                {
                    "event": "created",
                    "timestamp": test_plan.created_at.isoformat(),
                    "data": test_plan.model_dump()
                }
            ]
        }
        
        existing_history = self.redis_client.get(history_key)
        if existing_history:
            history_data = json.loads(existing_history)
            history_data["events"].append({
                "event": "updated",
                "timestamp": datetime.now().isoformat(),
                "data": test_plan.model_dump()
            })
        
        self.redis_client.set(history_key, json.dumps(history_data))


