from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import (
    alerts,
    auth,
    deployments,
    environments,
    findings,
    projects,
    reports,
    risk,
    templates,
)
from app.core.config import settings
from app.db.database import Base, engine
from app.db.models import Environment, Project, TemplateVersion, User


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    _ = (User, Project, Environment, TemplateVersion)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(environments.router, prefix="/api/environments", tags=["environments"])
app.include_router(templates.router, prefix="/api/templates", tags=["templates"])
app.include_router(deployments.router, prefix="/api/deployments", tags=["deployments"])
app.include_router(findings.router, prefix="/api/findings", tags=["findings"])
app.include_router(risk.router, prefix="/api/risk", tags=["risk"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["alerts"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
