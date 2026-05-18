import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.database import get_db
from app.db.models import Environment, Finding, Project, TemplateVersion, User
from app.schemas.finding import FindingRead
from app.services.scanner_service import (
    scan_template_with_checkov,
    scan_template_with_policies,
    scan_template_with_trivy,
)

router = APIRouter()
FINDING_LAYER = "L2"


async def _get_template_version_for_user(
    template_version_id: uuid.UUID,
    db: AsyncSession,
    current_user: User,
) -> tuple[TemplateVersion, Environment, Project]:
    result = await db.execute(
        select(TemplateVersion, Environment, Project)
        .join(Environment, TemplateVersion.env_id == Environment.id)
        .join(Project, Environment.project_id == Project.id)
        .where(TemplateVersion.id == template_version_id, Project.owner_id == current_user.id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template version not found")
    template_version, environment, project = row
    return template_version, environment, project


async def _replace_findings(
    db: AsyncSession,
    env_id: uuid.UUID,
    engine: str,
    payloads: list[dict[str, str | None]],
) -> list[Finding]:
    """Replace existing findings for the environment/engine with the latest scan results."""
    findings = [
        Finding(
            env_id=env_id,
            layer=FINDING_LAYER,
            engine=engine,
            rule_id=payload["rule_id"],
            severity=payload["severity"],
            resource=payload["resource"],
            evidence=payload.get("evidence"),
            recommendation=payload.get("recommendation"),
        )
        for payload in payloads
    ]
    async with db.begin():
        await db.execute(delete(Finding).where(Finding.env_id == env_id, Finding.engine == engine))
        db.add_all(findings)
    for finding in findings:
        await db.refresh(finding)
    return findings


@router.post("/{template_version_id}/scan/trivy", response_model=list[FindingRead], status_code=status.HTTP_201_CREATED)
async def scan_template_version_trivy(
    template_version_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Finding]:
    template_version, environment, _project = await _get_template_version_for_user(
        template_version_id, db, current_user
    )
    payloads = await asyncio.to_thread(scan_template_with_trivy, template_version.files_ref)
    return await _replace_findings(db, environment.id, "trivy", payloads)


@router.post("/{template_version_id}/scan/checkov", response_model=list[FindingRead], status_code=status.HTTP_201_CREATED)
async def scan_template_version_checkov(
    template_version_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Finding]:
    template_version, environment, _project = await _get_template_version_for_user(
        template_version_id, db, current_user
    )
    payloads = await asyncio.to_thread(scan_template_with_checkov, template_version.files_ref)
    return await _replace_findings(db, environment.id, "checkov", payloads)


@router.post(
    "/{template_version_id}/scan/policies",
    response_model=list[FindingRead],
    status_code=status.HTTP_201_CREATED,
)
async def scan_template_version_policies(
    template_version_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Finding]:
    template_version, environment, _project = await _get_template_version_for_user(
        template_version_id, db, current_user
    )
    payloads = await asyncio.to_thread(scan_template_with_policies, template_version.files_ref)
    return await _replace_findings(db, environment.id, "policies", payloads)
