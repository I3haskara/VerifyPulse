from pydantic import BaseModel

from typing import List

class Requirement(BaseModel):

    text: str

class EndpointPlan(BaseModel):

    path: str

    method: str

    description: str

class TestCase(BaseModel):

    id: str

    category: str

    description: str

    steps: List[str]

    expected_result: str

class TestPlan(BaseModel):

    requirement: Requirement

    endpoints: List[EndpointPlan]

    tests: List[TestCase]
