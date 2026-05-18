import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from opentelemetry import trace
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.database import get_db
from app.db.models import DeploymentRun, Environment, Finding, Project, RiskAssessment, TemplateVersion, User
from app.schemas.deployment import DeploymentRunRead, to_deployment_read
from app.schemas.environment import EnvironmentRead
from app.schemas.risk import RiskAssessmentRead, RiskFactorDetail
from app.schemas.template_version import TemplateVersionRead
from app.services.risk_service import build_risk_assessment, parse_assessment_payload
from app.services.storage_service import storage_service
from app.workers.deploy_tasks import deploy_environment_task
from app.workers.scan_tasks import scan_post_deployment_task

router = APIRouter()


async def _get_environment_for_user(
    environment_id: uuid.UUID,
    db: AsyncSession,
    current_user: User,
) -> Environment:
    env_result = await db.execute(
        select(Environment, Project)
        .join(Project, Environment.project_id == Project.id)
        .where(Environment.id == environment_id, Project.owner_id == current_user.id)
    )
    row = env_result.first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Environment not found")
    environment, _project = row
    return environment


def _to_risk_read(assessment: RiskAssessment) -> RiskAssessmentRead:
    payload = parse_assessment_payload(assessment)
    return RiskAssessmentRead(
        id=payload["id"],
        env_id=payload["env_id"],
        score=payload["score"],
        risk_class=payload["risk_class"],
        factors=[RiskFactorDetail(**factor) for factor in payload["factors"]],
        top_factors=[RiskFactorDetail(**factor) for factor in payload["top_factors"]],
        recommendations=payload["recommendations"],
        timestamp=payload["timestamp"],
    )


@router.get("/{environment_id}", response_model=EnvironmentRead)
async def get_environment(
    environment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Environment:
    return await _get_environment_for_user(environment_id, db, current_user)


@router.post(
    "/{environment_id}/risk-assessments",
    response_model=RiskAssessmentRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_risk_assessment(
    environment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RiskAssessmentRead:
    await _get_environment_for_user(environment_id, db, current_user)

    findings_result = await db.execute(
        select(Finding).where(Finding.env_id == environment_id, Finding.layer == "L2")
    )
    findings = list(findings_result.scalars().all())

    assessment = build_risk_assessment(environment_id, findings)
    db.add(assessment)
    await db.commit()
    await db.refresh(assessment)
    return _to_risk_read(assessment)


@router.get("/{environment_id}/risk-assessments/latest", response_model=RiskAssessmentRead)
async def get_latest_risk_assessment(
    environment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RiskAssessmentRead:
    await _get_environment_for_user(environment_id, db, current_user)

    result = await db.execute(
        select(RiskAssessment)
        .where(RiskAssessment.env_id == environment_id)
        .order_by(RiskAssessment.timestamp.desc())
        .limit(1)
    )
    assessment = result.scalar_one_or_none()
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Risk assessment not found")
    return _to_risk_read(assessment)


@router.post(
    "/{environment_id}/deploy",
    response_model=DeploymentRunRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def deploy_environment(
    environment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DeploymentRunRead:
    environment = await _get_environment_for_user(environment_id, db, current_user)

    template_result = await db.execute(
        select(TemplateVersion)
        .where(TemplateVersion.env_id == environment.id)
        .order_by(TemplateVersion.created_at.desc())
        .limit(1)
    )
    if not template_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload a template before deploying.",
        )

    deployment_id = uuid.uuid4()
    span = trace.get_current_span()
    trace_id = None
    if span.is_recording():
        trace_id = format(span.get_span_context().trace_id, "032x")

    deployment_run = DeploymentRun(
        id=deployment_id,
        env_id=environment.id,
        status="RUNNING",
        trace_id=trace_id,
        started_at=datetime.now(timezone.utc),
    )
    db.add(deployment_run)
    await db.commit()
    await db.refresh(deployment_run)

    deploy_environment_task.delay(str(deployment_id))
    return to_deployment_read(deployment_run)


@router.get("/{environment_id}/deployments/latest", response_model=DeploymentRunRead)
async def get_latest_deployment(
    environment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DeploymentRunRead:
    await _get_environment_for_user(environment_id, db, current_user)

    result = await db.execute(
        select(DeploymentRun)
        .where(DeploymentRun.env_id == environment_id)
        .order_by(DeploymentRun.started_at.desc())
        .limit(1)
    )
    deployment_run = result.scalar_one_or_none()
    if not deployment_run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deployment not found")
    return to_deployment_read(deployment_run)


@router.post(
    "/{environment_id}/scan/post-deployment",
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_post_deployment_scan(
    environment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    await _get_environment_for_user(environment_id, db, current_user)
    task = scan_post_deployment_task.delay(str(environment_id))
    return {"status": "queued", "task_id": task.id, "env_id": str(environment_id)}


@router.post("/{environment_id}/upload", response_model=TemplateVersionRead, status_code=status.HTTP_201_CREATED)
async def upload_environment_template(
    environment_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TemplateVersion:
    env_result = await db.execute(
        select(Environment, Project)
        .join(Project, Environment.project_id == Project.id)
        .where(Environment.id == environment_id, Project.owner_id == current_user.id)
    )
    row = env_result.first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Environment not found")

    environment, project = row
    template_version_id = uuid.uuid4()
    files_ref = storage_service.upload_template_archive(
        project_id=project.id,
        environment_id=environment.id,
        template_version_id=template_version_id,
        upload_file=file,
    )

    template_version = TemplateVersion(
        id=template_version_id,
        env_id=environment.id,
        files_ref=files_ref,
    )
    db.add(template_version)
    await db.commit()
    await db.refresh(template_version)
    return template_version


# Alternate path matching Phase 9 suggestion: POST /environments/{env_id}/templates/upload
# This is an alias that preserves the same behavior and response model.
@router.post("/{environment_id}/templates/upload", response_model=TemplateVersionRead, status_code=status.HTTP_201_CREATED)
async def upload_environment_template_v2(
    environment_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TemplateVersion:
    # reuse the existing logic by delegating to the same flow: perform the same DB checks
    env_result = await db.execute(
        select(Environment, Project)
        .join(Project, Environment.project_id == Project.id)
        .where(Environment.id == environment_id, Project.owner_id == current_user.id)
    )
    row = env_result.first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Environment not found")

    environment, project = row
    template_version_id = uuid.uuid4()
    files_ref = storage_service.upload_template_archive(
        project_id=project.id,
        environment_id=environment.id,
        template_version_id=template_version_id,
        upload_file=file,
    )

    template_version = TemplateVersion(
        id=template_version_id,
        env_id=environment.id,
        files_ref=files_ref,
    )
    db.add(template_version)
    await db.commit()
    await db.refresh(template_version)
    return template_version

