import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.database import get_db
from app.db.models import Environment, Project, TemplateVersion, User
from app.schemas.environment import EnvironmentCreate, EnvironmentRead
from app.schemas.project import ProjectCreate, ProjectRead

router = APIRouter()


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_in: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Project:
    project = Project(name=project_in.name, owner_id=current_user.id)
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


@router.get("", response_model=list[ProjectRead])
async def list_projects(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Project]:
    result = await db.execute(select(Project).where(Project.owner_id == current_user.id).order_by(Project.name.asc()))
    return list(result.scalars().all())


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id, Project.owner_id == current_user.id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    result = await db.execute(select(Project).where(Project.id == project_id, Project.owner_id == current_user.id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    env_ids_result = await db.execute(select(Environment.id).where(Environment.project_id == project_id))
    env_ids = list(env_ids_result.scalars().all())
    if env_ids:
        await db.execute(delete(TemplateVersion).where(TemplateVersion.env_id.in_(env_ids)))
        await db.execute(delete(Environment).where(Environment.id.in_(env_ids)))
    await db.delete(project)
    await db.commit()


@router.post("/{project_id}/environments", response_model=EnvironmentRead, status_code=status.HTTP_201_CREATED)
async def create_project_environment(
    project_id: uuid.UUID,
    environment_in: EnvironmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Environment:
    project_result = await db.execute(select(Project).where(Project.id == project_id, Project.owner_id == current_user.id))
    project = project_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    existing_env_result = await db.execute(select(Environment).where(Environment.project_id == project_id))
    if existing_env_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Project already has an environment",
        )

    environment = Environment(project_id=project.id, target=environment_in.target, status=environment_in.status)
    db.add(environment)
    await db.commit()
    await db.refresh(environment)
    return environment


@router.get("/{project_id}/environments", response_model=list[EnvironmentRead])
async def list_project_environments(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Environment]:
    project_result = await db.execute(select(Project).where(Project.id == project_id, Project.owner_id == current_user.id))
    if not project_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    env_result = await db.execute(
        select(Environment).where(Environment.project_id == project_id).order_by(Environment.id.asc())
    )
    return list(env_result.scalars().all())
