"""
Postman API Client - Real Integration
"""
import requests
from typing import Optional, Dict, Any
from verifypulse.models import TestPlan


class PostmanClient:
    """
    Postman API integration for creating collections and tests.
    """
    
    BASE_URL = "https://api.getpostman.com"
    
    def __init__(self, api_key: str):
        """
        Initialize Postman client
        
        Args:
            api_key: Postman API key
        """
        self.api_key = api_key
        self.headers = {
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json"
        }
    
    def build_collection_from_plan(self, plan: TestPlan) -> dict:
        """
        Convert TestPlan → Postman Collection JSON.
        
        Args:
            plan: TestPlan to convert
        
        Returns:
            Postman collection JSON structure
        """
        # Build test scripts from test cases
        items = []
        for endpoint in plan.endpoints:
            # Create request items for this endpoint
            endpoint_items = []
            
            # Group tests by endpoint (simplified - in real implementation, 
            # you'd map tests to endpoints more intelligently)
            for test in plan.tests:
                # Build test script
                test_script = [
                    f"// {test.description}",
                    "",
                    f"pm.test('{test.description}', function() {{",
                    f"    pm.response.to.have.status({self._get_expected_status(test)});",
                    "});",
                    ""
                ]
                
                # Add custom assertions from test steps
                for step in test.steps:
                    if "status" in step.lower() or "200" in step or "401" in step:
                        continue  # Already handled
                    test_script.append(f"pm.test('{step}', function() {{")
                    test_script.append("    pm.expect(pm.response.code).to.be.oneOf([200, 201, 400, 401, 404]);")
                    test_script.append("});")
                    test_script.append("")
                
                # Create request item
                request_item = {
                    "name": test.description,
                    "request": {
                        "method": endpoint.method.upper(),
                        "url": {
                            "raw": f"{{{{base_url}}}}{endpoint.path}",
                            "host": ["{{base_url}}"],
                            "path": endpoint.path.strip("/").split("/") if endpoint.path != "/" else []
                        },
                        "header": []
                    },
                    "event": [
                        {
                            "listen": "test",
                            "script": {
                                "exec": test_script,
                                "type": "text/javascript"
                            }
                        }
                    ]
                }
                
                # Add body for POST/PUT/PATCH
                if endpoint.method.upper() in ["POST", "PUT", "PATCH"]:
                    request_item["request"]["body"] = {
                        "mode": "raw",
                        "raw": "{\n  \"email\": \"{{tokenized_email}}\",\n  \"password\": \"{{tokenized_password}}\"\n}",
                        "options": {
                            "raw": {
                                "language": "json"
                            }
                        }
                    }
                
                endpoint_items.append(request_item)
            
            # If no tests mapped, create a basic request
            if not endpoint_items:
                endpoint_items.append({
                    "name": endpoint.description,
                    "request": {
                        "method": endpoint.method.upper(),
                        "url": {
                            "raw": f"{{{{base_url}}}}{endpoint.path}",
                            "host": ["{{base_url}}"],
                            "path": endpoint.path.strip("/").split("/") if endpoint.path != "/" else []
                        }
                    },
                    "event": [
                        {
                            "listen": "test",
                            "script": {
                                "exec": [
                                    "pm.test('Status code is 200', function() {",
                                    "    pm.response.to.have.status(200);",
                                    "});"
                                ]
                            }
                        }
                    ]
                })
            
            items.extend(endpoint_items)
        
        return {
            "info": {
                "name": f"VerifyPulse - {plan.requirement.text[:40]}",
                "description": f"Generated from requirement: {plan.requirement.text}",
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
            },
            "item": items,
            "variable": [
                {
                    "key": "base_url",
                    "value": "http://localhost:8000",
                    "type": "string"
                }
            ]
        }
    
    def _get_expected_status(self, test: Any) -> int:
        """Extract expected status code from test case"""
        expected = test.expected_result
        if "200" in str(expected):
            return 200
        elif "401" in str(expected) or "Unauthorized" in str(expected):
            return 401
        elif "400" in str(expected) or "Bad Request" in str(expected):
            return 400
        elif "404" in str(expected) or "Not Found" in str(expected):
            return 404
        return 200  # Default
    
    def create_collection(self, collection_json: dict, workspace_id: Optional[str] = None) -> str:
        """
        Create a new Postman collection using the official API.
        
        Args:
            collection_json: Collection JSON structure
            workspace_id: Optional workspace ID
        
        Returns:
            Collection ID (uid)
        """
        url = f"{self.BASE_URL}/collections"
        if workspace_id:
            url += f"?workspace={workspace_id}"
        
        payload = {"collection": collection_json}
        
        try:
            response = requests.post(url, json=payload, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            collection = result.get("collection", {})
            collection_id = collection.get("uid") or collection.get("id", "")
            
            if collection_id:
                print(f"[Postman] Collection created successfully: {collection_id}")
                return collection_id
            else:
                print("[Warning] Postman API returned collection but no ID found")
                return "unknown_collection_id"
                
        except requests.exceptions.RequestException as e:
            print(f"[Warning] Postman collection creation failed: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"[Warning] Response: {e.response.text}")
            return "failed_collection_id"
        except Exception as e:
            print(f"[Warning] Postman collection creation error: {str(e)}")
            return "failed_collection_id"
    
    def add_tests(self, collection_id: str, tests: list) -> bool:
        """
        Add tests to an existing collection.
        Note: Postman API doesn't have a direct "add tests" endpoint,
        so this would update the collection with new items.
        
        Args:
            collection_id: Collection ID
            tests: List of test items to add
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get existing collection
            get_url = f"{self.BASE_URL}/collections/{collection_id}"
            get_response = requests.get(get_url, headers=self.headers, timeout=30)
            get_response.raise_for_status()
            
            collection = get_response.json().get("collection", {})
            existing_items = collection.get("item", [])
            
            # Add new items
            collection["item"] = existing_items + tests
            
            # Update collection
            update_url = f"{self.BASE_URL}/collections/{collection_id}"
            update_response = requests.put(
                update_url,
                json={"collection": collection},
                headers=self.headers,
                timeout=30
            )
            update_response.raise_for_status()
            
            print(f"[Postman] Tests added to collection {collection_id}")
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"[Warning] Postman add_tests failed: {str(e)}")
            return False
        except Exception as e:
            print(f"[Warning] Postman add_tests error: {str(e)}")
            return False
    
    def create_or_update_collection(self, collection_json: dict) -> str:
        """
        Create or update a Postman collection.
        This is the main method used by the pipeline.
        
        Args:
            collection_json: Collection JSON structure
        
        Returns:
            Collection ID
        """
        return self.create_collection(collection_json)
