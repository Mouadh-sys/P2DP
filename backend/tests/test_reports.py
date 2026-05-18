import zipfile
from io import BytesIO
from unittest.mock import patch

import pytest
from httpx import AsyncClient


def _build_zip() -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("deployment.yaml", "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: demo\n")
    return buffer.getvalue()


@pytest.mark.asyncio
async def test_create_and_download_report(async_client: AsyncClient, auth_headers: dict[str, str]) -> None:
    project_response = await async_client.post("/api/projects", json={"name": "report-project"}, headers=auth_headers)
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
        await async_client.post(
            f"/api/environments/{environment_id}/upload",
            files=files,
            headers=auth_headers,
        )

    with patch("app.services.report_service.storage_service.upload_text", return_value="mock-key") as up:
        create_resp = await async_client.post(
            f"/api/environments/{environment_id}/reports",
            headers=auth_headers,
        )
    assert create_resp.status_code == 201
    body = create_resp.json()
    assert body["env_id"] == environment_id
    assert body["download_url"].endswith("/download")
    report_id = body["report_id"]
    up.assert_called_once()
    html = up.call_args[0][1]
    assert "P2DP" in html
    assert "report-project" in html

    with patch("app.api.reports.storage_service.get_object_bytes", return_value=html.encode("utf-8")):
        dl = await async_client.get(f"/api/reports/{report_id}/download", headers=auth_headers)
    assert dl.status_code == 200
    assert "text/html" in dl.headers.get("content-type", "")
    assert b"P2DP" in dl.content


@pytest.mark.asyncio
async def test_download_report_forbidden_other_user(async_client: AsyncClient, auth_headers: dict[str, str]) -> None:
    """Report download is scoped to project owner."""
    project_response = await async_client.post("/api/projects", json={"name": "r2"}, headers=auth_headers)
    project_id = project_response.json()["id"]
    env_response = await async_client.post(
        f"/api/projects/{project_id}/environments",
        json={"target": "dev", "status": "active"},
        headers=auth_headers,
    )
    environment_id = env_response.json()["id"]

    with patch("app.services.report_service.storage_service.upload_text", return_value="k"):
        create_resp = await async_client.post(
            f"/api/environments/{environment_id}/reports",
            headers=auth_headers,
        )
    report_id = create_resp.json()["report_id"]

    await async_client.post(
        "/api/auth/register",
        json={"email": "other@example.com", "password": "pw123456", "role": "devops"},
    )
    login2 = await async_client.post("/api/auth/login", json={"email": "other@example.com", "password": "pw123456"})
    other_headers = {"Authorization": f"Bearer {login2.json()['access_token']}"}

    dl = await async_client.get(f"/api/reports/{report_id}/download", headers=other_headers)
    assert dl.status_code == 404
