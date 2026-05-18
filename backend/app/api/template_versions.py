import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.database import get_db
from app.db.models import Environment, Finding, PreDeploymentScan, Project, TemplateVersion, User
from app.schemas.finding import FindingRead
from app.schemas.scan import ScanQueuedResponse, ScanStatusRead
from app.schemas.validation import ValidationQueuedResponse
from app.services.scanner_service import (
    scan_template_with_checkov,
    scan_template_with_policies,
    scan_template_with_trivy,
)
from app.workers.scan_tasks import scan_pre_deployment_task
from app.workers.validation_tasks import validate_template_task

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
    phase: str = "PRE_DEPLOYMENT",
) -> list[Finding]:
    """Replace existing findings for the environment/engine/phase with the latest scan results."""
    async with db.begin():
        await db.execute(
            delete(Finding).where(
                Finding.env_id == env_id,
                Finding.engine == engine,
                Finding.phase == phase,
            )
        )
        findings = [
            Finding(
                env_id=env_id,
                layer=FINDING_LAYER,
                phase=phase,
                engine=engine,
                rule_id=payload["rule_id"],
                severity=payload["severity"],
                resource=payload["resource"],
                evidence=payload.get("evidence"),
                recommendation=payload.get("recommendation"),
            )
            for payload in payloads
        ]
        db.add_all(findings)
    for finding in findings:
        await db.refresh(finding)
    return findings


@router.post(
    "/{template_version_id}/validate",
    response_model=ValidationQueuedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def validate_template_version(
    template_version_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ValidationQueuedResponse:
    await _get_template_version_for_user(template_version_id, db, current_user)
    task = validate_template_task.delay(str(template_version_id))
    return ValidationQueuedResponse(task_id=task.id)


@router.post(
    "/{template_version_id}/scan",
    response_model=ScanQueuedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def scan_template_version(
    template_version_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScanQueuedResponse:
    template_version, environment, _project = await _get_template_version_for_user(
        template_version_id, db, current_user
    )
    scan = PreDeploymentScan(
        template_version_id=template_version.id,
        env_id=environment.id,
        status="PENDING",
    )
    db.add(scan)
    await db.commit()
    await db.refresh(scan)

    task = scan_pre_deployment_task.delay(str(scan.id))
    scan.task_id = task.id
    await db.commit()

    return ScanQueuedResponse(scan_id=scan.id, task_id=task.id, status=scan.status)


@router.get("/{template_version_id}/scan/{scan_id}", response_model=ScanStatusRead)
async def get_scan_status(
    template_version_id: uuid.UUID,
    scan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScanStatusRead:
    _template_version, environment, _project = await _get_template_version_for_user(
        template_version_id, db, current_user
    )
    result = await db.execute(
        select(PreDeploymentScan).where(
            PreDeploymentScan.id == scan_id,
            PreDeploymentScan.template_version_id == template_version_id,
        )
    )
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")

    findings_count = await db.scalar(
        select(func.count())
        .select_from(Finding)
        .where(Finding.env_id == environment.id, Finding.layer == FINDING_LAYER)
    )

    return ScanStatusRead(
        id=scan.id,
        template_version_id=scan.template_version_id,
        env_id=scan.env_id,
        status=scan.status,
        task_id=scan.task_id,
        error_message=scan.error_message,
        findings_count=int(findings_count or 0),
        created_at=scan.created_at,
        started_at=scan.started_at,
        finished_at=scan.finished_at,
    )


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
