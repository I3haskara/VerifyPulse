from verifypulse.models import Requirement, TestPlan, EndpointPlan, TestCase

from verifypulse.integrations.postman_client import PostmanClient

from verifypulse.integrations.redis_client import VerifyPulseRedis

from verifypulse.integrations.skyflow_client import SkyflowClient

from verifypulse.integrations.sanity_client import SanityClient

from verifypulse.integrations.parallel_client import ParallelClient

from verifypulse.config import load_config

def build_test_plan(requirement_text: str) -> TestPlan:

    """

    Very simple LLM-simulated test plan generator.

    """

    req = Requirement(text=requirement_text)

    login_ep = EndpointPlan(

        path="/login",

        method="POST",

        description="User login endpoint"

    )

    tests = [

        TestCase(

            id="TC-1",

            category="happy",

            description="Valid login",

            steps=["Send valid credentials"],

            expected_result="200 OK"

        ),

        TestCase(

            id="TC-2",

            category="negative",

            description="Invalid password",

            steps=["Send invalid password"],

            expected_result="401 Unauthorized"

        )

    ]

    return TestPlan(

        requirement=req,

        endpoints=[login_ep],

        tests=tests

    )

def execute_pipeline(requirement_text: str):

    # Load config
    cfg = load_config()

    # Instantiate all clients
    redis_client = VerifyPulseRedis(cfg.REDIS_URL)

    postman = PostmanClient(cfg.POSTMAN_API_KEY)

    # Initialize Skyflow client (reads from env or uses config)
    skyflow = SkyflowClient(
        vault_id=cfg.SKYFLOW_VAULT_ID,
        api_token=cfg.SKYFLOW_API_TOKEN
    )

    sanity = SanityClient(

        cfg.SANITY_PROJECT_ID,

        cfg.SANITY_DATASET,

        cfg.SANITY_WRITE_TOKEN

    )

    # Handle missing Parallel API key gracefully
    parallel_api_key = getattr(cfg, 'PARALLEL_API_KEY', None) or ""
    parallel = ParallelClient(parallel_api_key)

    # a) Store the raw requirement in Redis
    redis_client.store_requirement("last_requirement", requirement_text)

    # b) Build a base TestPlan for a login endpoint (happy + negative)
    plan = build_test_plan(requirement_text)

    # c) Call Parallel to enrich tests with security guidelines
    guidelines = parallel.search_security_guidelines("OWASP API security login checklist")
    
    # Add security test cases from guidelines
    security_test_counter = len(plan.tests) + 1
    for guideline in guidelines:
        if guideline and guideline.strip():
            security_test = TestCase(
                id=f"TC-{security_test_counter}",
                category="security",
                description=f"Security check: {guideline[:100]}",
                steps=[f"Verify: {guideline[:200]}"],
                expected_result="Compliant with security guidelines"
            )
            plan.tests.append(security_test)
            security_test_counter += 1

    # d) Call PostmanClient to build and create collection
    collection_json = postman.build_collection_from_plan(plan)
    collection_id = postman.create_or_update_collection(collection_json)

    # e) Call skyflow.tokenize_record to tokenize PII and use tokens in tests
    pii_data = {
        "email": "test@example.com",
        "password": "testpassword123"
    }
    tokenize_result = skyflow.tokenize_record(pii_data)
    
    # Extract tokenized fields from result
    if tokenize_result.get("enabled") and tokenize_result.get("tokenized"):
        tokens = tokenize_result["tokenized"]
        print(f"[Skyflow] Generated tokens for {len(tokens)} fields")
        # Store tokens for use in Postman collection variables
        # The Postman collection builder will use {{tokenized_email}} etc.
    else:
        reason = tokenize_result.get("reason", "Unknown error")
        print(f"[Warning] Skyflow tokenization not enabled: {reason}")

    # f) Call sanity.create_test_report
    report_id = sanity.create_test_report(plan, collection_id)

    # g) Return result dict
    return {

        "collection_id": collection_id,

        "report_id": report_id,

        "endpoints": len(plan.endpoints),

        "tests": len(plan.tests)

    }

