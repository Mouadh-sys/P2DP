import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.database import get_db
from app.db.models import Environment, Finding, Project, User
from app.schemas.finding import FindingRead

router = APIRouter()


async def _get_environment_for_user(
    environment_id: uuid.UUID,
    db: AsyncSession,
    current_user: User,
) -> Environment:
    result = await db.execute(
        select(Environment)
        .join(Project, Environment.project_id == Project.id)
        .where(Environment.id == environment_id, Project.owner_id == current_user.id)
    )
    environment = result.scalar_one_or_none()
    if not environment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Environment not found")
    return environment


@router.get("/environments/{environment_id}", response_model=list[FindingRead])
async def list_environment_findings(
    environment_id: uuid.UUID,
    severity: str | None = Query(default=None),
    engine: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Finding]:
    await _get_environment_for_user(environment_id, db, current_user)

    query = select(Finding).where(Finding.env_id == environment_id, Finding.layer == "L2")
    if severity:
        query = query.where(Finding.severity == severity.upper())
    if engine:
        query = query.where(Finding.engine == engine.lower())

    result = await db.execute(query.order_by(Finding.severity.desc(), Finding.engine.asc(), Finding.rule_id.asc()))
    return list(result.scalars().all())
