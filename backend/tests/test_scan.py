import zipfile
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient

from app.services.scan_service import run_pre_deployment_scan


def _build_zip() -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("deployment.yaml", "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: demo\n")
    return buffer.getvalue()


@pytest.mark.asyncio
async def test_unified_scan_endpoint_queues_task(async_client: AsyncClient, auth_headers: dict[str, str]) -> None:
    project_response = await async_client.post("/api/projects", json={"name": "scan-project"}, headers=auth_headers)
    project_id = project_response.json()["id"]
    env_response = await async_client.post(
        f"/api/projects/{project_id}/environments",
        json={"target": "dev", "status": "active"},
        headers=auth_headers,
    )
    environment_id = env_response.json()["id"]

    files = {"file": ("template.zip", _build_zip(), "application/zip")}
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

    with patch("app.api.template_versions.scan_pre_deployment_task.delay") as delay_mock:
        delay_mock.return_value = MagicMock(id="scan-task-1")
        response = await async_client.post(
            f"/api/template-versions/{template_version_id}/scan",
            headers=auth_headers,
        )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "PENDING"
    assert body["task_id"] == "scan-task-1"
    delay_mock.assert_called_once()


@patch("app.services.scan_service.scan_template_with_policies", return_value=[])
@patch("app.services.scan_service.scan_template_with_checkov", return_value=[])
@patch("app.services.scan_service.scan_template_with_trivy")
def test_run_pre_deployment_scan_aggregates_engines(
    mock_trivy: MagicMock,
    _mock_checkov: MagicMock,
    _mock_policies: MagicMock,
) -> None:
    mock_trivy.return_value = [
        {
            "rule_id": "TEST-001",
            "severity": "HIGH",
            "resource": "Pod/demo",
            "evidence": "test",
            "recommendation": "fix",
        }
    ]
    results, errors = run_pre_deployment_scan("projects/demo/source.zip")
    assert "trivy" in results
    assert len(results["trivy"]) == 1
    assert errors == {}


@pytest.mark.asyncio
async def test_list_findings_for_environment(async_client: AsyncClient, auth_headers: dict[str, str]) -> None:
    project_response = await async_client.post("/api/projects", json={"name": "findings-project"}, headers=auth_headers)
    project_id = project_response.json()["id"]
    env_response = await async_client.post(
        f"/api/projects/{project_id}/environments",
        json={"target": "dev", "status": "active"},
        headers=auth_headers,
    )
    environment_id = env_response.json()["id"]

    response = await async_client.get(
        f"/api/findings/environments/{environment_id}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json() == []
