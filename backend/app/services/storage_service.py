import io
import uuid

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import HTTPException, UploadFile, status

from app.core.config import settings


class StorageService:
    def __init__(self) -> None:
        endpoint = settings.minio_endpoint
        if not endpoint.startswith(("http://", "https://")):
            endpoint = f"http://{endpoint}"

        self.bucket = settings.minio_bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=settings.minio_access_key,
            aws_secret_access_key=settings.minio_secret_key,
        )

    def _ensure_bucket_exists(self) -> None:
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except ClientError:
            self.client.create_bucket(Bucket=self.bucket)

    def upload_template_archive(
        self,
        project_id: uuid.UUID,
        environment_id: uuid.UUID,
        template_version_id: uuid.UUID,
        upload_file: UploadFile,
    ) -> str:
        object_key = f"projects/{project_id}/{environment_id}/{template_version_id}/source.tar.gz"
        filename = upload_file.filename or ""
        if not filename.endswith((".tar.gz", ".tgz", ".zip")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Template upload must be an archive (.tar.gz, .tgz, or .zip)",
            )
        try:
            self._ensure_bucket_exists()
            upload_file.file.seek(0)
            file_bytes = upload_file.file.read()
            self.client.upload_fileobj(
                io.BytesIO(file_bytes),
                self.bucket,
                object_key,
                ExtraArgs={"ContentType": upload_file.content_type or "application/gzip"},
            )
        except (BotoCoreError, ClientError, OSError) as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to upload template to MinIO storage. Verify endpoint, credentials, and bucket access.",
            ) from exc
        return object_key


storage_service = StorageService()
