import uuid
import zipfile
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient

from app.services.validation_service import (
    detect_template_types,
    run_validation,
    validate_dockerfile,
    validate_kubernetes,
)


def _build_zip(content: dict[str, str]) -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, body in content.items():
            archive.writestr(name, body)
    return buffer.getvalue()


@pytest.mark.asyncio
async def test_validate_endpoint_queues_task(async_client: AsyncClient, auth_headers: dict[str, str]) -> None:
    project_response = await async_client.post("/api/projects", json={"name": "validate-project"}, headers=auth_headers)
    project_id = project_response.json()["id"]
    env_response = await async_client.post(
        f"/api/projects/{project_id}/environments",
        json={"target": "dev", "status": "pending"},
        headers=auth_headers,
    )
    environment_id = env_response.json()["id"]

    files = {"file": ("template.zip", _build_zip({"deployment.yaml": "apiVersion: v1\nkind: ConfigMap\n"}), "application/zip")}
    with patch(
        "app.api.environments.storage_service.upload_template_archive",
        return_value="projects/test/envs/test/templates/test/source.zip",
    ):
        upload_response = await async_client.post(
            f"/api/environments/{environment_id}/upload",
            files=files,
            headers=auth_headers,
        )
    template_version_id = upload_response.json()["id"]

    with patch("app.api.template_versions.validate_template_task.delay") as delay_mock:
        delay_mock.return_value = MagicMock(id="task-123")
        response = await async_client.post(
            f"/api/template-versions/{template_version_id}/validate",
            headers=auth_headers,
        )

    assert response.status_code == 202
    assert response.json()["status"] == "queued"
    assert response.json()["task_id"] == "task-123"
    delay_mock.assert_called_once_with(template_version_id)


def test_detect_template_types(tmp_path: Path) -> None:
    (tmp_path / "main.tf").write_text('resource "null_resource" "demo" {}', encoding="utf-8")
    (tmp_path / "deployment.yaml").write_text("apiVersion: v1\nkind: ConfigMap\n", encoding="utf-8")
    (tmp_path / "Dockerfile").write_text("FROM alpine:3.20\n", encoding="utf-8")

    detected = detect_template_types(tmp_path)
    assert detected == ["terraform", "dockerfile", "kubernetes"]


def test_validate_dockerfile_basic_parse(tmp_path: Path) -> None:
    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text("FROM alpine:3.20\nRUN echo hello\n", encoding="utf-8")
    logs: list[str] = []

    assert validate_dockerfile(tmp_path, logs) is True
    assert "Basic Dockerfile parsing passed" in "".join(logs)


@patch("app.services.validation_service._run_command")
def test_validate_kubernetes_uses_server_dry_run(mock_run_command: MagicMock, tmp_path: Path) -> None:
    manifest = tmp_path / "deployment.yaml"
    manifest.write_text("apiVersion: v1\nkind: ConfigMap\n", encoding="utf-8")
    mock_run_command.return_value = MagicMock(returncode=0, stdout="configured\n", stderr="")

    logs: list[str] = []
    assert validate_kubernetes(tmp_path, logs) is True
    mock_run_command.assert_called_once_with(["kubectl", "apply", "--dry-run=server", "-f", str(tmp_path)])


@patch("app.services.validation_service.storage_service.upload_text")
@patch("app.services.validation_service._template_workspace")
@patch("app.services.validation_service.validate_dockerfile", return_value=True)
@patch("app.services.validation_service.validate_terraform", return_value=True)
@patch("app.services.validation_service.validate_kubernetes", return_value=True)
def test_run_validation_uploads_log_and_returns_storage_ref(
    _mock_k8s: MagicMock,
    _mock_tf: MagicMock,
    _mock_docker: MagicMock,
    mock_workspace: MagicMock,
    mock_upload_text: MagicMock,
    tmp_path: Path,
) -> None:
    (tmp_path / "deployment.yaml").write_text("apiVersion: v1\nkind: ConfigMap\n", encoding="utf-8")
    mock_workspace.return_value.__enter__.return_value = str(tmp_path)
    mock_upload_text.return_value = "projects/p/e/templates/tv/artifacts/validation-log.txt"

    project_id = uuid.uuid4()
    environment_id = uuid.uuid4()
    template_version_id = uuid.uuid4()
    outcome = run_validation("files/ref.zip", project_id, environment_id, template_version_id)

    assert outcome.success is True
    assert outcome.storage_ref.endswith("artifacts/validation-log.txt")
    mock_upload_text.assert_called_once()
