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
    # default bucket used to store uploaded artifacts
    minio_bucket: str = "p2dp-artifacts"
    gitops_repo_path: str = ""
    gitops_git_user: str = "p2dp-bot"
    gitops_git_email: str = "p2dp-bot@local"
    gitops_remote_url: str = ""
    github_token: str = ""
    argocd_server: str = ""
    argocd_token: str = ""
    argocd_app_name: str = "p2dp-dev"
    k8s_namespace_prefix: str = "p2dp"
    kubectl_context: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def resolved_gitops_repo_path(self) -> str:
        if self.gitops_repo_path:
            return self.gitops_repo_path
        from pathlib import Path

        return str(Path(__file__).resolve().parents[3] / "gitops-repo")


settings = Settings()
