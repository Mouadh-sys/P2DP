from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    auth,
    environments,
    findings,
    projects,
    reports,
    template_versions,
)
from app.core.config import settings
from app.core.security import get_password_hash
from app.db.database import Base, engine, SessionLocal
from sqlalchemy import select
from app.db.models import (
    Artifact,
    DeploymentRun,
    Environment,
    Finding,
    PreDeploymentScan,
    Project,
    Report,
    RiskAssessment,
    TemplateVersion,
    ThreatAlert,
    User,
    UserRole,
)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # import model classes so SQLAlchemy metadata is populated
    _ = (
        User,
        Project,
        Environment,
        TemplateVersion,
        Artifact,
        PreDeploymentScan,
        RiskAssessment,
        DeploymentRun,
        Finding,
        ThreatAlert,
        Report,
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    # Seed minimal users for local/dev environment if they don't exist.
    # This is convenient for development; in production use a proper bootstrap/migration.
    if settings.environment == "dev":
        async with SessionLocal() as session:
            # users to ensure exist: (email, role, password)
            seeds = [
                ("admin@p2dp.local", UserRole.ADMIN.value, "admin123"),
                ("devops@p2dp.local", UserRole.DEVOPS.value, "devops123"),
                ("security@p2dp.local", UserRole.SECURITY_VIEWER.value, "security123"),
            ]
            for email, role, password in seeds:
                result = await session.execute(select(User).where(User.email == email))
                if not result.scalar_one_or_none():
                    user = User(email=email, role=role, password_hash=get_password_hash(password))
                    session.add(user)
            await session.commit()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

from app.core.otel import setup_telemetry  # noqa: E402

setup_telemetry("p2dp-api")

if settings.environment == "dev":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(environments.router, prefix="/api/environments", tags=["environments"])
app.include_router(template_versions.router, prefix="/api/template-versions", tags=["template-versions"])
app.include_router(findings.router, prefix="/api/findings", tags=["findings"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
