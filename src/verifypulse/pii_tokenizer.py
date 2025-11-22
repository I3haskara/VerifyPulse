"""
PII Tokenization Service using Skyflow-style tokenization
"""
from typing import Dict, Any, Optional
import re
from verifypulse.integrations import SkyflowClient


class PIITokenizer:
    """Service for tokenizing PII data in test cases"""
    
    # Sample PII patterns
    EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    PHONE_PATTERN = re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b')
    SSN_PATTERN = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
    CREDIT_CARD_PATTERN = re.compile(r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b')
    
    def __init__(self, skyflow_client: Optional[SkyflowClient] = None, use_stub: bool = True):
        """
        Initialize PII tokenizer
        
        Args:
            skyflow_client: Optional Skyflow client (uses stub if not provided)
            use_stub: Whether to use stub tokenization (default: True)
        """
        self.skyflow_client = skyflow_client
        self.use_stub = use_stub or skyflow_client is None
    
    def tokenize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tokenize PII in a data dictionary
        
        Args:
            data: Dictionary containing potentially sensitive data
        
        Returns:
            Dictionary with PII replaced by tokens or placeholders
        """
        tokenized = {}
        
        for key, value in data.items():
            if isinstance(value, str):
                tokenized[key] = self._tokenize_string(value, key)
            elif isinstance(value, dict):
                tokenized[key] = self.tokenize_data(value)
            elif isinstance(value, list):
                tokenized[key] = [self.tokenize_data(item) if isinstance(item, dict) else item for item in value]
            else:
                tokenized[key] = value
        
        return tokenized
    
    def _tokenize_string(self, value: str, field_name: str) -> str:
        """Tokenize a string value"""
        field_lower = field_name.lower()
        
        # Check field name for hints
        if 'email' in field_lower:
            return self._tokenize_email(value)
        elif 'password' in field_lower:
            return self._tokenize_password(value)
        elif 'phone' in field_lower or 'mobile' in field_lower:
            return self._tokenize_phone(value)
        elif 'ssn' in field_lower or 'social' in field_lower:
            return self._tokenize_ssn(value)
        elif 'card' in field_lower or 'credit' in field_lower:
            return self._tokenize_credit_card(value)
        else:
            # Try pattern matching
            if self.EMAIL_PATTERN.search(value):
                return self._tokenize_email(value)
            elif self.PHONE_PATTERN.search(value):
                return self._tokenize_phone(value)
            elif self.SSN_PATTERN.search(value):
                return self._tokenize_ssn(value)
            elif self.CREDIT_CARD_PATTERN.search(value):
                return self._tokenize_credit_card(value)
        
        return value
    
    def _tokenize_email(self, email: str) -> str:
        """Tokenize an email address"""
        if self.use_stub:
            # Stub: return placeholder
            return "{{tokenized_email}}"
        else:
            # Real Skyflow tokenization
            try:
                response = self.skyflow_client.insert_record(
                    table="pii_data",
                    fields={"email": email},
                    tokens=True
                )
                return response.get("tokens", {}).get("email", "{{tokenized_email}}")
            except Exception:
                return "{{tokenized_email}}"
    
    def _tokenize_password(self, password: str) -> str:
        """Tokenize a password (usually just placeholder)"""
        return "{{tokenized_password}}"
    
    def _tokenize_phone(self, phone: str) -> str:
        """Tokenize a phone number"""
        if self.use_stub:
            return "{{tokenized_phone}}"
        else:
            try:
                response = self.skyflow_client.insert_record(
                    table="pii_data",
                    fields={"phone": phone},
                    tokens=True
                )
                return response.get("tokens", {}).get("phone", "{{tokenized_phone}}")
            except Exception:
                return "{{tokenized_phone}}"
    
    def _tokenize_ssn(self, ssn: str) -> str:
        """Tokenize an SSN"""
        if self.use_stub:
            return "{{tokenized_ssn}}"
        else:
            try:
                response = self.skyflow_client.insert_record(
                    table="pii_data",
                    fields={"ssn": ssn},
                    tokens=True
                )
                return response.get("tokens", {}).get("ssn", "{{tokenized_ssn}}")
            except Exception:
                return "{{tokenized_ssn}}"
    
    def _tokenize_credit_card(self, card: str) -> str:
        """Tokenize a credit card number"""
        if self.use_stub:
            return "{{tokenized_credit_card}}"
        else:
            try:
                response = self.skyflow_client.insert_record(
                    table="pii_data",
                    fields={"credit_card": card},
                    tokens=True
                )
                return response.get("tokens", {}).get("credit_card", "{{tokenized_credit_card}}")
            except Exception:
                return "{{tokenized_credit_card}}"
    
    def apply_tokenization_to_test_plan(self, test_plan: 'TestPlan') -> 'TestPlan':
        """
        Apply tokenization to all test cases in a test plan that require it
        
        Args:
            test_plan: TestPlan to tokenize
        
        Returns:
            TestPlan with tokenized PII
        """
        from verifypulse.test_plan import TestPlan, Endpoint, TestCase
        
        tokenized_endpoints = []
        for endpoint in test_plan.endpoints:
            tokenized_test_cases = []
            for test_case in endpoint.test_cases:
                if test_case.use_pii_tokenization and test_case.request_body:
                    tokenized_body = self.tokenize_data(test_case.request_body)
                    # Create new test case with tokenized body
                    tokenized_test_case = TestCase(
                        name=test_case.name,
                        description=test_case.description,
                        expected_status=test_case.expected_status,
                        request_body=tokenized_body,
                        query_params=test_case.query_params,
                        headers=test_case.headers,
                        assertions=test_case.assertions,
                        use_pii_tokenization=test_case.use_pii_tokenization
                    )
                    tokenized_test_cases.append(tokenized_test_case)
                else:
                    tokenized_test_cases.append(test_case)
            
            tokenized_endpoint = Endpoint(
                path=endpoint.path,
                method=endpoint.method,
                description=endpoint.description,
                test_cases=tokenized_test_cases,
                requires_auth=endpoint.requires_auth
            )
            tokenized_endpoints.append(tokenized_endpoint)
        
        return TestPlan(
            requirement_id=test_plan.requirement_id,
            requirement_text=test_plan.requirement_text,
            endpoints=tokenized_endpoints,
            created_at=test_plan.created_at,
            metadata=test_plan.metadata
        )


