"""
Example: Dynamic test generation for quality agent.

This demonstrates how to programmatically generate test cases
based on API specifications, Postman collections, or other sources.
"""

from typing import Any, Dict, List


def generate_crud_tests(resource: str, base_endpoint: str) -> List[Dict[str, Any]]:
    """
    Generate standard CRUD test cases for a REST resource.
    
    Args:
        resource: Name of the resource (e.g., "user", "product")
        base_endpoint: Base API path (e.g., "/api/users")
        
    Returns:
        List of test case dictionaries covering Create, Read, Update, Delete
    """
    return [
        {
            "name": f"{resource}_list",
            "method": "GET",
            "endpoint": base_endpoint,
            "payload": None,
            "expected_status": [200],
            "requires_json": True,
        },
        {
            "name": f"{resource}_get_by_id",
            "method": "GET",
            "endpoint": f"{base_endpoint}/1",
            "payload": None,
            "expected_status": [200, 404],
            "requires_json": True,
        },
        {
            "name": f"{resource}_create",
            "method": "POST",
            "endpoint": base_endpoint,
            "payload": {f"{resource}_data": "test_value"},
            "expected_status": [200, 201],
            "requires_json": True,
        },
        {
            "name": f"{resource}_update",
            "method": "PUT",
            "endpoint": f"{base_endpoint}/1",
            "payload": {f"{resource}_data": "updated_value"},
            "expected_status": [200, 404],
            "requires_json": True,
        },
        {
            "name": f"{resource}_delete",
            "method": "DELETE",
            "endpoint": f"{base_endpoint}/1",
            "payload": None,
            "expected_status": [200, 204, 404],
            "requires_json": False,
        },
    ]


def generate_auth_tests(auth_endpoints: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    Generate authentication/authorization test cases.
    
    Args:
        auth_endpoints: Dictionary mapping auth actions to endpoints
            Example: {"login": "/auth/login", "logout": "/auth/logout"}
            
    Returns:
        List of authentication test cases
    """
    tests = []
    
    if "login" in auth_endpoints:
        tests.extend([
            {
                "name": "auth_login_valid",
                "method": "POST",
                "endpoint": auth_endpoints["login"],
                "payload": {"username": "admin", "password": "admin123"},
                "expected_status": [200],
                "requires_json": True,
            },
            {
                "name": "auth_login_invalid",
                "method": "POST",
                "endpoint": auth_endpoints["login"],
                "payload": {"username": "bad", "password": "wrong"},
                "expected_status": [401, 403],
                "requires_json": True,
            },
        ])
    
    if "register" in auth_endpoints:
        tests.append({
            "name": "auth_register",
            "method": "POST",
            "endpoint": auth_endpoints["register"],
            "payload": {
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "secure123"
            },
            "expected_status": [200, 201, 409],  # 409 if already exists
            "requires_json": True,
        })
    
    if "logout" in auth_endpoints:
        tests.append({
            "name": "auth_logout",
            "method": "POST",
            "endpoint": auth_endpoints["logout"],
            "payload": None,
            "expected_status": [200, 204],
            "requires_json": False,
        })
    
    return tests


def generate_from_postman_collection(collection_path: str) -> List[Dict[str, Any]]:
    """
    Generate test cases from a Postman collection JSON file.
    
    Args:
        collection_path: Path to Postman collection JSON
        
    Returns:
        List of test cases extracted from the collection
    """
    import json
    from pathlib import Path
    
    tests = []
    collection_file = Path(collection_path)
    
    if not collection_file.exists():
        return tests
    
    try:
        with open(collection_file, 'r', encoding='utf-8') as f:
            collection = json.load(f)
        
        # Parse collection items (simplified - real implementation would be recursive)
        for item in collection.get("item", []):
            if "request" in item:
                req = item["request"]
                test_case = {
                    "name": item.get("name", "unnamed_test"),
                    "method": req.get("method", "GET"),
                    "endpoint": req.get("url", {}).get("raw", "/"),
                    "payload": req.get("body", {}).get("raw"),
                    "expected_status": [200],  # Default, could extract from tests
                    "requires_json": True,
                }
                tests.append(test_case)
    
    except Exception as e:
        print(f"Error parsing Postman collection: {e}")
    
    return tests


# Example usage patterns:
if __name__ == "__main__":
    # Generate CRUD tests for multiple resources
    user_tests = generate_crud_tests("user", "/api/users")
    product_tests = generate_crud_tests("product", "/api/products")
    
    # Generate auth tests
    auth_tests = generate_auth_tests({
        "login": "/auth/login",
        "register": "/auth/register",
        "logout": "/auth/logout"
    })
    
    # Combine all tests
    all_tests = user_tests + product_tests + auth_tests
    
    print(f"Generated {len(all_tests)} test cases:")
    for test in all_tests:
        print(f"  - {test['name']}: {test['method']} {test['endpoint']}")
