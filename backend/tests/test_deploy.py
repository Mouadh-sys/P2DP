import uuid
import zipfile
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient

from app.services.gitops_service import commit_and_push, copy_manifests_to_gitops


def _build_zip() -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("deployment.yaml", "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: demo\n")
    return buffer.getvalue()


@patch("app.services.gitops_service._template_workspace")
def test_copy_manifests_to_gitops(mock_workspace: MagicMock, tmp_path: Path) -> None:
    source = tmp_path / "uploaded-template"
    source.mkdir()
    (source / "deployment.yaml").write_text("apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: demo\n", encoding="utf-8")
    mock_workspace.return_value.__enter__.return_value = str(source)

    repo_root = tmp_path / "gitops-repo"
    deployment_id = uuid.uuid4()
    with patch("app.services.gitops_service.settings") as settings_mock:
        settings_mock.resolved_gitops_repo_path = str(repo_root)
        dest = copy_manifests_to_gitops("fake/ref.zip", "dev", deployment_id)

    assert dest.exists()
    assert (dest / "deployment.yaml").exists()
    assert (dest / "p2dp-deployment-metadata.yaml").exists()
    assert str(deployment_id) in (dest / "p2dp-deployment-metadata.yaml").read_text(encoding="utf-8")


@patch("app.services.gitops_service._run_git")
@patch("app.services.gitops_service._ensure_git_repository")
def test_commit_message_format(mock_ensure: MagicMock, mock_git: MagicMock, tmp_path: Path) -> None:
    deployment_id = uuid.uuid4()

    def git_side_effect(args: list[str], cwd: Path) -> MagicMock:
        result = MagicMock()
        result.returncode = 0
        if args[:2] == ["rev-parse", "HEAD"]:
            result.stdout = "abc123def456\n"
        else:
            result.stdout = ""
            result.stderr = ""
        return result

    mock_git.side_effect = git_side_effect
    with patch("app.services.gitops_service.settings") as settings_mock:
        settings_mock.resolved_gitops_repo_path = str(tmp_path)
        settings_mock.gitops_remote_url = ""
        commit_hash = commit_and_push(deployment_id, "dev")

    assert commit_hash == "abc123def456"
    commit_calls = [call.args[0] for call in mock_git.call_args_list]
    assert ["commit", "-m", f"deploy(env:dev): deployment {deployment_id}"] in commit_calls


@pytest.mark.asyncio
async def test_deploy_endpoint_creates_running_deployment(async_client: AsyncClient, auth_headers: dict[str, str]) -> None:
    project_response = await async_client.post("/api/projects", json={"name": "deploy-project"}, headers=auth_headers)
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

    with patch("app.api.environments.deploy_environment_task.delay") as delay_mock:
        delay_mock.return_value = MagicMock(id="deploy-task-1")
        response = await async_client.post(f"/api/environments/{environment_id}/deploy", headers=auth_headers)

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "RUNNING"
    assert body["deployment_id"]
    delay_mock.assert_called_once_with(body["deployment_id"])
