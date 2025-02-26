"""Set up app configuration from env variables"""
from pydantic_settings import BaseSettings
from pydantic import field_validator

class AppConfig(BaseSettings):
    """App configuration"""
    LOGGING_LEVEL: int = 1
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    OPENAI_API_KEY: str
    OPENAI_TEXT_GENERATION_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIM: int = 1_536

    @property
    def POSTGRES_DATABASE_URL(self) -> str:
        """Postgres database URL, based on the other app configuration."""
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @field_validator("LOGGING_LEVEL")
    def validate_logging_level(cls, value):
        if value not in [0, 1, 2]:
            raise ValueError(f"Invalid log level {value}. Must be one of [0, 1, 2].")
        return value


app_config = AppConfig()
