"""
Test case configuration and loader.
Define your test cases here and they'll be automatically executed.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def load_test_cases() -> List[Dict[str, Any]]:
    """
    Load test cases from configuration.
    
    Each test case should have:
    - name: Unique identifier for the test
    - method: HTTP method (GET, POST, PUT, DELETE, etc.)
    - endpoint: API endpoint path
    - payload: Request body (None for GET requests)
    - expected_status: List of acceptable status codes
    - requires_json: Whether response must be JSON
    
    Returns:
        List of test case dictionaries
    """
    return [
        {
            "name": "health_check",
            "method": "GET",
            "endpoint": "/health",
            "payload": None,
            "expected_status": [200],
            "requires_json": False,
        },
        {
            "name": "login_requirements",
            "method": "POST",
            "endpoint": "/login",
            "payload": {"username": "test_user", "password": "wrong_password"},
            "expected_status": [200, 401],
            "requires_json": True,
        },
        # Add more test cases here:
        # {
        #     "name": "user_profile_get",
        #     "method": "GET",
        #     "endpoint": "/api/user/profile",
        #     "payload": None,
        #     "expected_status": [200, 401],
        #     "requires_json": True,
        # },
    ]


def load_test_cases_from_dict(test_dict: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Load test cases from a dictionary (useful for dynamic generation).
    
    Args:
        test_dict: Dictionary with test definitions
        
    Returns:
        List of test case dictionaries
    """
    test_cases = []
    
    for name, config in test_dict.items():
        test_case = {
            "name": name,
            "method": config.get("method", "GET"),
            "endpoint": config.get("endpoint", "/"),
            "payload": config.get("payload"),
            "expected_status": config.get("expected_status", [200]),
            "requires_json": config.get("requires_json", True),
        }
        test_cases.append(test_case)
    
    return test_cases


# Example: Custom test suite for specific API
EXAMPLE_ECOMMERCE_TESTS = [
    {
        "name": "product_list",
        "method": "GET",
        "endpoint": "/api/products",
        "payload": None,
        "expected_status": [200],
        "requires_json": True,
    },
    {
        "name": "product_search",
        "method": "GET",
        "endpoint": "/api/products?q=laptop",
        "payload": None,
        "expected_status": [200],
        "requires_json": True,
    },
    {
        "name": "cart_add_item",
        "method": "POST",
        "endpoint": "/api/cart/items",
        "payload": {"product_id": "123", "quantity": 1},
        "expected_status": [200, 201],
        "requires_json": True,
    },
    {
        "name": "checkout",
        "method": "POST",
        "endpoint": "/api/checkout",
        "payload": {"payment_method": "credit_card"},
        "expected_status": [200, 400],  # 400 for invalid cart
        "requires_json": True,
    },
]
