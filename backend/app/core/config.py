from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "P2DP API"
    environment: str = "dev"
    database_url: str = "postgresql+psycopg://postgres:postgres@db:5432/p2dp"
    redis_url: str = "redis://redis:6379/0"
    secret_key: str
    access_token_expire_minutes: int = 60
    jwt_algorithm: str = "HS256"
    minio_endpoint: str = "http://minio:9000"
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str = "p2dp-templates"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
