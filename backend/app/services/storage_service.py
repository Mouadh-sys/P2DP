import io
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

        # Only allow archives for now; prefer .zip for MVP
        if not lower.endswith((".zip", ".tar.gz", ".tgz")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Template upload must be an archive (.zip, .tar.gz, or .tgz)",
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

            # If it's a zip, validate internal contents
            if lower.endswith(".zip"):
                try:
                    # zip will raise if invalid
                    self._validate_zip_contents(tmp)
                except zipfile.BadZipFile as exc:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Uploaded file is not a valid zip archive",
                    ) from exc

            # build object key preserving extension and matching Phase 9 spec
            suffix = Path(filename).suffix or ""
            # for double-extension like .tar.gz keep full suffix
            if lower.endswith(".tar.gz"):
                suffix = ".tar.gz"

            object_key = f"projects/{project_id}/envs/{environment_id}/templates/{template_version_id}/source{suffix}"

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


storage_service = StorageService()
