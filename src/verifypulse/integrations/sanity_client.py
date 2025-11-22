"""
Sanity CMS Client - Real Integration
"""
import requests
from typing import Dict, Any, List, Optional
from verifypulse.models import TestPlan


class SanityClient:
    """
    Sanity CMS integration for creating test reports.
    """
    
    def __init__(self, project_id: str, dataset: str, token: str, api_version: str = "v2021-10-21"):
        """
        Initialize Sanity client
        
        Args:
            project_id: Sanity project ID
            dataset: Sanity dataset name
            token: Sanity write token
            api_version: Sanity API version
        """
        self.project_id = project_id
        self.dataset = dataset
        self.token = token
        self.api_version = api_version
        
        self.base_url = f"https://{project_id}.api.sanity.io/{api_version}"
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    def create_report_document(
        self,
        plan: TestPlan,
        collection_id: str,
        privacy_findings: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Create a testReport document in Sanity with the specified structure.
        
        Args:
            plan: TestPlan containing requirement and test information
            collection_id: Postman collection ID
            privacy_findings: Optional list of privacy findings
        
        Returns:
            Sanity document ID
        """
        # Build endpoints array
        endpoints = []
        for ep in plan.endpoints:
            endpoints.append({
                "path": ep.path,
                "method": ep.method,
                "description": ep.description
            })
        
        # Build privacy findings (default empty if not provided)
        if privacy_findings is None:
            privacy_findings = []
        
        # Create document
        document = {
            "_type": "testReport",
            "apiName": plan.requirement.text[:60],
            "summary": f"{len(plan.endpoints)} endpoints, {len(plan.tests)} tests.",
            "endpoints": endpoints,
            "privacyFindings": privacy_findings,
            "collectionId": collection_id,
            "requirementText": plan.requirement.text
        }
        
        url = f"{self.base_url}/data/mutate/{self.dataset}"
        
        mutation = {
            "mutations": [
                {
                    "create": document
                }
            ]
        }
        
        try:
            response = requests.post(url, json=mutation, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            document_id = result.get("documentIds", [None])[0]
            
            if document_id:
                print(f"[Sanity] Test report created: {document_id}")
                return document_id
            else:
                print("[Warning] Sanity API returned no document ID")
                return "unknown_report_id"
                
        except requests.exceptions.RequestException as e:
            print(f"[Warning] Sanity report creation failed: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"[Warning] Response: {e.response.text}")
            return "failed_report_id"
        except Exception as e:
            print(f"[Warning] Sanity report creation error: {str(e)}")
            return "failed_report_id"
    
    def create_test_report(self, plan: TestPlan, collection_id: str) -> str:
        """
        Alias for create_report_document for backward compatibility.
        
        Args:
            plan: TestPlan
            collection_id: Collection ID
        
        Returns:
            Report document ID
        """
        return self.create_report_document(plan, collection_id)
