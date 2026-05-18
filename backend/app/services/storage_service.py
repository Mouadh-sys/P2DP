import os
import uuid
import zipfile
import tempfile
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import HTTPException, UploadFile, status

from app.core.config import settings


class StorageService:
    # Maximum upload size in bytes (50 MiB default). Adjust as needed.
    MAX_UPLOAD_SIZE_BYTES = 50 * 1024 * 1024

    # Allowed file types inside a template archive for MVP.
    ALLOWED_INTERNAL_EXTS = {".tf", ".tfvars", ".yaml", ".yml"}
    # Files named exactly "Dockerfile" are allowed (no extension)
    ALLOWED_INTERNAL_NAMES = {"Dockerfile"}
    # Disallowed extensions
    DISALLOWED_EXTS = {".exe", ".sh"}

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

    def _is_name_safe(self, member_name: str) -> bool:
        # Prevent absolute paths and path traversal
        if member_name.startswith("/"):
            return False
        normalized = Path(member_name)
        for part in normalized.parts:
            if part == "..":
                return False
        return True

    def _validate_zip_contents(self, zpath: str) -> None:
        # Open zip and validate each entry
        with zipfile.ZipFile(zpath, "r") as z:
            for info in z.infolist():
                name = info.filename
                # skip directories
                if name.endswith("/"):
                    continue

                if not self._is_name_safe(name):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid filename in archive: {name}",
                    )

                base = Path(name).name
                # allow Dockerfile by name
                if base in self.ALLOWED_INTERNAL_NAMES:
                    continue

                ext = Path(name).suffix.lower()
                if ext in self.DISALLOWED_EXTS:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Disallowed file type in archive: {ext}",
                    )

                if ext not in self.ALLOWED_INTERNAL_EXTS:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Unsupported file type in archive: {ext}",
                    )

    def upload_template_archive(
        self,
        project_id: uuid.UUID,
        environment_id: uuid.UUID,
        template_version_id: uuid.UUID,
        upload_file: UploadFile,
    ) -> str:
        """
        Securely accept an uploaded archive (MVP focuses on .zip):
        - stream upload to a temp file while enforcing MAX_UPLOAD_SIZE_BYTES
        - if .zip: validate internal filenames and extensions to avoid path traversal and disallowed types
        - upload the original archive to MinIO at the canonical path
        - return the object key stored in MinIO
        """
        filename = upload_file.filename or ""
        lower = filename.lower()

        if not lower.endswith(".zip"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only .zip uploads are supported for the MVP",
            )

        # Stream upload to temporary file to avoid reading whole file into memory
        tmp = None
        total = 0
        try:
            tmpf = tempfile.NamedTemporaryFile(delete=False)
            tmp = tmpf.name
            chunk = upload_file.file.read(65536)
            while chunk:
                total += len(chunk)
                if total > self.MAX_UPLOAD_SIZE_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"Uploaded file exceeds maximum allowed size ({self.MAX_UPLOAD_SIZE_BYTES} bytes)",
                    )
                tmpf.write(chunk)
                chunk = upload_file.file.read(65536)
            tmpf.flush()
            tmpf.close()

            try:
                self._validate_zip_contents(tmp)
            except zipfile.BadZipFile as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Uploaded file is not a valid zip archive",
                ) from exc

            object_key = (
                f"projects/{project_id}/envs/{environment_id}/templates/"
                f"{template_version_id}/source.zip"
            )

            # upload the temp file to MinIO
            try:
                self._ensure_bucket_exists()
                with open(tmp, "rb") as fobj:
                    content_type = upload_file.content_type or "application/octet-stream"
                    self.client.upload_fileobj(fobj, self.bucket, object_key, ExtraArgs={"ContentType": content_type})
            except (BotoCoreError, ClientError, OSError) as exc:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Failed to upload template to MinIO storage. Verify endpoint, credentials, and bucket access.",
                ) from exc

            return object_key
        finally:
            # cleanup temp file if it exists
            try:
                if tmp and os.path.exists(tmp):
                    os.unlink(tmp)
            except OSError:
                pass

    def download_template_archive(self, object_key: str, destination_dir: str | None = None) -> str:
        destination = Path(destination_dir) if destination_dir else Path(tempfile.mkdtemp())
        destination.mkdir(parents=True, exist_ok=True)
        filename = Path(object_key).name
        target_path = destination / filename
        try:
            self.client.download_file(self.bucket, object_key, str(target_path))
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") == "404":
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Template archive not found in storage.",
                ) from exc
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to download template from MinIO storage. Verify endpoint, credentials, and bucket access.",
            ) from exc
        except (BotoCoreError, OSError) as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to download template from MinIO storage. Verify endpoint, credentials, and bucket access.",
            ) from exc

        return str(target_path)

    def upload_text(self, object_key: str, content: str, content_type: str = "text/plain") -> str:
        try:
            self._ensure_bucket_exists()
            self.client.put_object(
                Bucket=self.bucket,
                Key=object_key,
                Body=content.encode("utf-8"),
                ContentType=content_type,
            )
        except (BotoCoreError, ClientError, OSError) as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to upload artifact to MinIO storage.",
            ) from exc
        return object_key

    def validation_log_key(
        self,
        project_id: uuid.UUID,
        environment_id: uuid.UUID,
        template_version_id: uuid.UUID,
    ) -> str:
        return (
            f"projects/{project_id}/envs/{environment_id}/templates/"
            f"{template_version_id}/artifacts/validation-log.txt"
        )

    def report_object_key(self, project_id: uuid.UUID, environment_id: uuid.UUID, report_id: uuid.UUID) -> str:
        return f"projects/{project_id}/envs/{environment_id}/reports/{report_id}.html"

    def get_object_bytes(self, object_key: str) -> bytes:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=object_key)
            return response["Body"].read()
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in ("404", "NoSuchKey"):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Report object not found in storage.",
                ) from exc
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to read object from MinIO storage.",
            ) from exc
        except (BotoCoreError, OSError) as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to read object from MinIO storage.",
            ) from exc


storage_service = StorageService()
