from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "tcm_formulas"

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()
