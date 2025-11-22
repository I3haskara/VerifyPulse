"""
Main Workflow Service - Orchestrates the complete API quality agent workflow
"""
from typing import Dict, Any, Optional
from verifypulse.requirement_processor import RequirementProcessor
from verifypulse.integrations import PostmanClient, RedisClient, SkyflowClient, SanityClient
from verifypulse.pii_tokenizer import PIITokenizer
from verifypulse.report_writer import ReportWriter
from verifypulse.test_plan import TestPlan


class VerifyPulseWorkflow:
    """Main workflow orchestrator for VerifyPulse"""
    
    def __init__(
        self,
        redis_client: Optional[RedisClient] = None,
        postman_client: Optional[PostmanClient] = None,
        skyflow_client: Optional[SkyflowClient] = None,
        sanity_client: Optional[SanityClient] = None
    ):
        """
        Initialize workflow with clients
        
        Args:
            redis_client: Optional Redis client
            postman_client: Optional Postman client
            skyflow_client: Optional Skyflow client
            sanity_client: Optional Sanity client
        """
        self.redis_client = redis_client or RedisClient()
        self.postman_client = postman_client or PostmanClient()
        self.skyflow_client = skyflow_client or SkyflowClient(use_stub=True)
        self.sanity_client = sanity_client or SanityClient()
        
        # Initialize processors
        self.requirement_processor = RequirementProcessor(self.redis_client)
        self.pii_tokenizer = PIITokenizer(self.skyflow_client, use_stub=True)
        self.report_writer = ReportWriter(self.sanity_client)
    
    def process_requirement(
        self,
        requirement: str,
        requirement_id: Optional[str] = None,
        base_url: str = "{{base_url}}",
        workspace_id: Optional[str] = None,
        create_collection: bool = True,
        write_report: bool = True
    ) -> Dict[str, Any]:
        """
        Complete workflow: process requirement, generate test plan, create Postman collection, write report
        
        Args:
            requirement: Natural language requirement
            requirement_id: Optional requirement ID
            base_url: Base URL for Postman requests
            workspace_id: Optional Postman workspace ID
            create_collection: Whether to create Postman collection
            write_report: Whether to write Sanity report
        
        Returns:
            Complete workflow result
        """
        result = {
            "requirement_id": None,
            "requirement_text": requirement,
            "test_plan": None,
            "collection": None,
            "report": None,
            "status": "pending"
        }
        
        try:
            # Step 1: Process requirement and generate test plan
            processed = self.requirement_processor.process_requirement(requirement, requirement_id)
            result["requirement_id"] = processed["requirement_id"]
            result["test_plan"] = processed["test_plan"]
            
            # Reconstruct TestPlan object
            test_plan = TestPlan(**processed["test_plan"])
            
            # Step 2: Apply PII tokenization
            tokenized_test_plan = self.pii_tokenizer.apply_tokenization_to_test_plan(test_plan)
            
            # Step 3: Create Postman collection
            collection = None
            if create_collection:
                try:
                    collection = self.postman_client.create_collection_from_test_plan(
                        tokenized_test_plan,
                        base_url=base_url,
                        workspace_id=workspace_id
                    )
                    result["collection"] = {
                        "id": collection.get("id"),
                        "uid": collection.get("uid"),
                        "name": collection.get("info", {}).get("name")
                    }
                except Exception as e:
                    result["collection_error"] = str(e)
            
            # Step 4: Write report to Sanity
            report = None
            if write_report:
                try:
                    collection_id = collection.get("id") if collection else None
                    report = self.report_writer.write_summary_report(
                        tokenized_test_plan,
                        collection_id=collection_id,
                        execution_status="created"
                    )
                    result["report"] = report
                except Exception as e:
                    result["report_error"] = str(e)
            
            result["status"] = "completed"
            result["endpoints_count"] = len(tokenized_test_plan.endpoints)
            result["test_cases_count"] = sum(len(ep.test_cases) for ep in tokenized_test_plan.endpoints)
            
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
        
        return result
    
    def get_requirement_status(self, requirement_id: str) -> Dict[str, Any]:
        """
        Get status of a processed requirement
        
        Args:
            requirement_id: Requirement ID
        
        Returns:
            Requirement status and details
        """
        history = self.requirement_processor.get_requirement_history(requirement_id)
        return {
            "requirement_id": requirement_id,
            "history": history,
            "status": "found" if history else "not_found"
        }


