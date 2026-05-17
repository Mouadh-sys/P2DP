import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.database import get_db
from app.db.models import Environment, Project, TemplateVersion, User
from app.schemas.environment import EnvironmentRead
from app.schemas.template_version import TemplateVersionRead
from app.services.storage_service import storage_service

router = APIRouter()


@router.get("/{environment_id}", response_model=EnvironmentRead)
async def get_environment(
    environment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
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

