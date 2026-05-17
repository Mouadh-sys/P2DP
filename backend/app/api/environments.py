import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.database import get_db
from app.db.models import Environment, Project, TemplateVersion, User
from app.schemas.environment import EnvironmentCreate, EnvironmentRead
from app.schemas.template_version import TemplateVersionRead
from app.services.storage_service import storage_service

router = APIRouter()


@router.post("/projects/{project_id}", response_model=EnvironmentRead, status_code=status.HTTP_201_CREATED)
async def create_environment(
    project_id: uuid.UUID,
    environment_in: EnvironmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Environment:
    project_result = await db.execute(
        select(Project).where(Project.id == project_id, Project.owner_id == current_user.id)
    )
    project = project_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    environment = Environment(project_id=project.id, target=environment_in.target, status=environment_in.status)
    db.add(environment)
    await db.commit()
    await db.refresh(environment)
    return environment


@router.get("/projects/{project_id}", response_model=list[EnvironmentRead])
async def list_project_environments(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Environment]:
    project_result = await db.execute(
        select(Project).where(Project.id == project_id, Project.owner_id == current_user.id)
    )
    if not project_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    env_result = await db.execute(
        select(Environment).where(Environment.project_id == project_id).order_by(Environment.id.asc())
    )
    return list(env_result.scalars().all())


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
