"""
Report Writer for Sanity CMS
"""
from typing import Dict, Any, Optional
from datetime import datetime
from verifypulse.integrations import SanityClient
from verifypulse.test_plan import TestPlan


class ReportWriter:
    """Writes test plan summaries to Sanity CMS"""
    
    def __init__(self, sanity_client: Optional[SanityClient] = None):
        """
        Initialize report writer
        
        Args:
            sanity_client: Optional Sanity client (creates new if not provided)
        """
        self.sanity_client = sanity_client or SanityClient()
    
    def write_summary_report(
        self,
        test_plan: TestPlan,
        collection_id: Optional[str] = None,
        execution_status: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Write a summary report to Sanity
        
        Args:
            test_plan: TestPlan to summarize
            collection_id: Optional Postman collection ID
            execution_status: Optional execution status
        
        Returns:
            Created/updated document data
        """
        # Build report document
        report_doc = {
            "_type": "testReport",
            "_id": f"test-report-{test_plan.requirement_id}",
            "requirementId": test_plan.requirement_id,
            "requirementText": test_plan.requirement_text,
            "title": f"Test Report: {test_plan.requirement_id}",
            "summary": self._generate_summary(test_plan),
            "endpoints": [
                {
                    "path": ep.path,
                    "method": ep.method.value,
                    "description": ep.description,
                    "testCasesCount": len(ep.test_cases),
                    "requiresAuth": ep.requires_auth
                }
                for ep in test_plan.endpoints
            ],
            "statistics": {
                "totalEndpoints": len(test_plan.endpoints),
                "totalTestCases": sum(len(ep.test_cases) for ep in test_plan.endpoints),
                "endpointsWithAuth": sum(1 for ep in test_plan.endpoints if ep.requires_auth),
                "endpointsWithPII": sum(
                    1 for ep in test_plan.endpoints
                    for tc in ep.test_cases
                    if tc.use_pii_tokenization
                )
            },
            "collectionId": collection_id,
            "executionStatus": execution_status or "pending",
            "createdAt": test_plan.created_at.isoformat(),
            "updatedAt": datetime.now().isoformat(),
            "metadata": test_plan.metadata
        }
        
        # Try to create or update document
        try:
            # Check if document exists
            existing = self.sanity_client.get_document(report_doc["_id"])
            if existing:
                # Update existing
                return self.sanity_client.update_document(
                    report_doc["_id"],
                    {
                        "summary": report_doc["summary"],
                        "endpoints": report_doc["endpoints"],
                        "statistics": report_doc["statistics"],
                        "collectionId": report_doc["collectionId"],
                        "executionStatus": report_doc["executionStatus"],
                        "updatedAt": report_doc["updatedAt"]
                    }
                )
            else:
                # Create new
                return self.sanity_client.create_document(report_doc)
        except Exception as e:
            # If Sanity is not configured, return stub response
            return {
                "status": "stub",
                "message": f"Sanity client not configured: {str(e)}",
                "report": report_doc
            }
    
    def _generate_summary(self, test_plan: TestPlan) -> str:
        """Generate a text summary of the test plan"""
        total_endpoints = len(test_plan.endpoints)
        total_tests = sum(len(ep.test_cases) for ep in test_plan.endpoints)
        
        summary = f"""
Test Plan Summary for Requirement: {test_plan.requirement_id}

Requirement: {test_plan.requirement_text}

Generated {total_endpoints} endpoint(s) with {total_tests} total test case(s).

Endpoints:
"""
        for endpoint in test_plan.endpoints:
            summary += f"  - {endpoint.method.value} {endpoint.path} ({len(endpoint.test_cases)} test cases)\n"
        
        summary += f"\nGenerated at: {test_plan.created_at.isoformat()}"
        
        return summary.strip()


