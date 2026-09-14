from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    postgres_user: str = "truthtrace"
    postgres_password: str = "truthtrace"
    postgres_db: str = "truthtrace"
    postgres_host: str = "db"
    postgres_port: int = 5432

    # Auth
    jwt_secret: str = "dev-secret"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30
    refresh_token_days: int = 7

    # Bootstrap admin
    first_admin_email: str = "admin@truthtrace.com"
    first_admin_password: str = "ChangeMe123!"

    # Analysis
    analyzer_backend: str = "lexical"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    model_cache_dir: str = "/models"
    similarity_link_threshold: float = 0.55

    # Evidence storage
    evidence_dir: str = "/storage/evidence"
    max_evidence_mb: int = 50

    # CORS
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
