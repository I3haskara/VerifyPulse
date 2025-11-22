from pydantic_settings import BaseSettings

from functools import lru_cache

from dotenv import load_dotenv

import os

load_dotenv()

class Config(BaseSettings):

    POSTMAN_API_KEY: str

    REDIS_URL: str

    SKYFLOW_VAULT_ID: str

    SKYFLOW_API_TOKEN: str

    SKYFLOW_URL: str = ""

    SANITY_PROJECT_ID: str

    SANITY_DATASET: str

    SANITY_WRITE_TOKEN: str

    PARALLEL_API_KEY: str = ""

@lru_cache()

def load_config() -> Config:

    """

    Loads environment variables and returns Config singleton.

    """

    return Config()
