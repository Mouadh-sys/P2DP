import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.database import get_db
from app.db.models import Environment, Project, Report, User
from app.services.storage_service import storage_service

router = APIRouter()


@router.get("/{report_id}/download")
async def download_report(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    result = await db.execute(
        select(Report, Environment, Project)
        .join(Environment, Report.env_id == Environment.id)
        .join(Project, Environment.project_id == Project.id)
        .where(Report.id == report_id, Project.owner_id == current_user.id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    report, _environment, _project = row
    body = storage_service.get_object_bytes(report.storage_ref)
    return Response(
        content=body,
        media_type="text/html; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="p2dp-report-{report_id}.html"'},
    )
