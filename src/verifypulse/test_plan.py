"""
TestPlan Models and AI-Powered Test Plan Generator
"""
import re
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class HTTPMethod(str, Enum):
    """HTTP methods for API endpoints"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


class TestCase(BaseModel):
    """Individual test case within an endpoint"""
    name: str = Field(..., description="Test case name")
    description: Optional[str] = Field(None, description="Test case description")
    expected_status: int = Field(200, description="Expected HTTP status code")
    request_body: Optional[Dict[str, Any]] = Field(None, description="Request body for POST/PUT/PATCH")
    query_params: Optional[Dict[str, str]] = Field(None, description="Query parameters")
    headers: Optional[Dict[str, str]] = Field(None, description="Custom headers")
    assertions: List[str] = Field(default_factory=list, description="JavaScript test assertions")
    use_pii_tokenization: bool = Field(False, description="Whether to tokenize PII in this test")


class Endpoint(BaseModel):
    """API endpoint definition"""
    path: str = Field(..., description="Endpoint path (e.g., /login)")
    method: HTTPMethod = Field(..., description="HTTP method")
    description: Optional[str] = Field(None, description="Endpoint description")
    test_cases: List[TestCase] = Field(default_factory=list, description="Test cases for this endpoint")
    requires_auth: bool = Field(False, description="Whether endpoint requires authentication")


class TestPlan(BaseModel):
    """Complete test plan with endpoints and test cases"""
    requirement_id: str = Field(..., description="Unique identifier for the requirement")
    requirement_text: str = Field(..., description="Original natural language requirement")
    endpoints: List[Endpoint] = Field(default_factory=list, description="List of endpoints to test")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class TestPlanGenerator:
    """AI-powered test plan generator from natural language requirements"""
    
    def __init__(self):
        """Initialize the test plan generator"""
        pass
    
    def generate(self, requirement: str, requirement_id: Optional[str] = None) -> TestPlan:
        """
        Generate a test plan from a natural language requirement
        
        Args:
            requirement: Natural language requirement (e.g., "API must allow user login via POST /login")
            requirement_id: Optional requirement ID (generated if not provided)
        
        Returns:
            Generated TestPlan
        """
        import uuid
        req_id = requirement_id or f"req_{uuid.uuid4().hex[:8]}"
        
        # Parse requirement to extract endpoints and test cases
        endpoints = self._parse_requirement(requirement)
        
        return TestPlan(
            requirement_id=req_id,
            requirement_text=requirement,
            endpoints=endpoints,
            metadata={
                "generator": "VerifyPulse",
                "version": "0.1.0"
            }
        )
    
    def _parse_requirement(self, requirement: str) -> List[Endpoint]:
        """
        Parse natural language requirement into structured endpoints
        
        This is a rule-based parser that can be replaced with LLM integration
        
        Args:
            requirement: Natural language requirement
        
        Returns:
            List of parsed endpoints
        """
        endpoints = []
        requirement_lower = requirement.lower()
        
        # Match patterns like "POST /login", "GET /api/users", etc.
        method_path_pattern = r'\b(GET|POST|PUT|PATCH|DELETE)\s+([/\w-]+)'
        matches = re.finditer(method_path_pattern, requirement, re.IGNORECASE)
        
        for match in matches:
            method_str = match.group(1).upper()
            path = match.group(2)
            
            # Ensure path starts with /
            if not path.startswith('/'):
                path = '/' + path
            
            method = HTTPMethod(method_str)
            
            # Generate test cases based on endpoint type
            test_cases = self._generate_test_cases(method, path, requirement)
            
            endpoint = Endpoint(
                path=path,
                method=method,
                description=f"Endpoint for {requirement}",
                test_cases=test_cases,
                requires_auth=self._requires_auth(path, requirement)
            )
            endpoints.append(endpoint)
        
        # If no explicit method/path found, try to infer from keywords
        if not endpoints:
            endpoints = self._infer_endpoints(requirement)
        
        return endpoints
    
    def _generate_test_cases(self, method: HTTPMethod, path: str, requirement: str) -> List[TestCase]:
        """Generate test cases for an endpoint"""
        test_cases = []
        
        # Common test cases based on method
        if method == HTTPMethod.POST:
            # Success case
            test_cases.append(TestCase(
                name=f"{method.value} {path} - Success",
                description=f"Test successful {method.value} request to {path}",
                expected_status=200,
                request_body=self._generate_sample_body(path, method),
                assertions=[
                    "pm.response.to.have.status(200)",
                    "pm.response.to.be.json",
                    "pm.response.to.have.jsonBody()"
                ],
                use_pii_tokenization=self._contains_pii_keywords(requirement)
            ))
            
            # Validation error case
            test_cases.append(TestCase(
                name=f"{method.value} {path} - Validation Error",
                description=f"Test validation error for {method.value} {path}",
                expected_status=400,
                request_body={},
                assertions=[
                    "pm.response.to.have.status(400)",
                    "pm.response.to.be.json"
                ]
            ))
        
        elif method == HTTPMethod.GET:
            # Success case
            test_cases.append(TestCase(
                name=f"{method.value} {path} - Success",
                description=f"Test successful {method.value} request to {path}",
                expected_status=200,
                assertions=[
                    "pm.response.to.have.status(200)",
                    "pm.response.to.be.json"
                ]
            ))
            
            # Not found case (if path suggests resource ID)
            if '{' in path or re.search(r'/\d+', path):
                test_cases.append(TestCase(
                    name=f"{method.value} {path} - Not Found",
                    description=f"Test 404 for non-existent resource",
                    expected_status=404,
                    assertions=[
                        "pm.response.to.have.status(404)"
                    ]
                ))
        
        elif method == HTTPMethod.PUT or method == HTTPMethod.PATCH:
            # Success case
            test_cases.append(TestCase(
                name=f"{method.value} {path} - Success",
                description=f"Test successful {method.value} request to {path}",
                expected_status=200,
                request_body=self._generate_sample_body(path, method),
                assertions=[
                    "pm.response.to.have.status(200)",
                    "pm.response.to.be.json"
                ]
            ))
        
        elif method == HTTPMethod.DELETE:
            # Success case
            test_cases.append(TestCase(
                name=f"{method.value} {path} - Success",
                description=f"Test successful {method.value} request to {path}",
                expected_status=200,
                assertions=[
                    "pm.response.to.have.status(200)"
                ]
            ))
        
        return test_cases
    
    def _generate_sample_body(self, path: str, method: HTTPMethod) -> Dict[str, Any]:
        """Generate sample request body based on path"""
        import re
        
        # Common patterns
        if 'login' in path.lower():
            return {
                "email": "{{tokenized_email}}",
                "password": "{{tokenized_password}}"
            }
        elif 'user' in path.lower():
            return {
                "name": "Test User",
                "email": "{{tokenized_email}}"
            }
        elif 'register' in path.lower() or 'signup' in path.lower():
            return {
                "email": "{{tokenized_email}}",
                "password": "{{tokenized_password}}",
                "name": "Test User"
            }
        else:
            return {
                "data": "test_value"
            }
    
    def _requires_auth(self, path: str, requirement: str) -> bool:
        """Determine if endpoint requires authentication"""
        auth_keywords = ['auth', 'login', 'protected', 'secure', 'token', 'jwt', 'bearer']
        requirement_lower = requirement.lower()
        path_lower = path.lower()
        
        # Login/register endpoints typically don't require auth
        if any(kw in path_lower for kw in ['login', 'register', 'signup', 'signin']):
            return False
        
        # Check for auth keywords
        return any(kw in requirement_lower for kw in auth_keywords)
    
    def _contains_pii_keywords(self, requirement: str) -> bool:
        """Check if requirement mentions PII"""
        pii_keywords = ['email', 'password', 'ssn', 'credit card', 'phone', 'address', 'name', 'user']
        requirement_lower = requirement.lower()
        return any(kw in requirement_lower for kw in pii_keywords)
    
    def _infer_endpoints(self, requirement: str) -> List[Endpoint]:
        """Infer endpoints from requirement when no explicit method/path is given"""
        endpoints = []
        requirement_lower = requirement.lower()
        
        # Common patterns
        if 'login' in requirement_lower:
            endpoints.append(Endpoint(
                path="/login",
                method=HTTPMethod.POST,
                description="User login endpoint",
                test_cases=[
                    TestCase(
                        name="POST /login - Success",
                        expected_status=200,
                        request_body={"email": "{{tokenized_email}}", "password": "{{tokenized_password}}"},
                        assertions=["pm.response.to.have.status(200)", "pm.response.to.be.json"],
                        use_pii_tokenization=True
                    )
                ],
                requires_auth=False
            ))
        
        return endpoints

