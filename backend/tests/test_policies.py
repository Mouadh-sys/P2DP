import shutil
import subprocess
import zipfile
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient

from app.services.scanner_service import POLICY_DIR, _parse_conftest_results, run_conftest_scan

POLICIES_DIR = Path(__file__).resolve().parents[1] / "app" / "policies" / "kubernetes"
SAMPLES_VULNERABLE = Path(__file__).resolve().parents[2] / "samples" / "kubernetes" / "vulnerable"


def _build_zip(directory: Path) -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for path in directory.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(directory).as_posix())
    return buffer.getvalue()


def test_parse_conftest_results_maps_policy_metadata() -> None:
    payload = [
        {
            "filename": "deployment.yaml",
            "failures": [
                {
                    "msg": "Container app is privileged.",
                    "metadata": {
                        "id": "P2DP-K8S-001",
                        "severity": "HIGH",
                        "resource": "Pod/bad-pod",
                        "recommendation": "Remove privileged=true from the container securityContext.",
                    },
                }
            ],
        }
    ]
    findings = _parse_conftest_results(payload)
    assert len(findings) == 1
    assert findings[0]["rule_id"] == "P2DP-K8S-001"
    assert findings[0]["severity"] == "HIGH"
    assert findings[0]["resource"] == "Pod/bad-pod"


def test_policy_directory_exists() -> None:
    assert (POLICY_DIR / "kubernetes" / "security.rego").exists()


@pytest.mark.skipif(shutil.which("opa") is None, reason="opa CLI not installed")
def test_opa_policy_suite() -> None:
    result = subprocess.run(
        ["opa", "test", str(POLICIES_DIR), "-v"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.skipif(shutil.which("conftest") is None, reason="conftest CLI not installed")
def test_conftest_detects_vulnerable_samples(tmp_path: Path) -> None:
    workspace = tmp_path / "uploaded-template"
    workspace.mkdir()
    for sample in SAMPLES_VULNERABLE.glob("*.yaml"):
        workspace.joinpath(sample.name).write_text(sample.read_text(encoding="utf-8"), encoding="utf-8")

    findings = run_conftest_scan(str(workspace))["findings"]
    rule_ids = {finding["rule_id"] for finding in findings}
    assert "P2DP-K8S-001" in rule_ids
    assert "P2DP-K8S-002" in rule_ids
    assert "P2DP-K8S-004" in rule_ids
    assert "P2DP-K8S-005" in rule_ids
    assert "P2DP-K8S-003" in rule_ids
    assert "P2DP-K8S-006" in rule_ids


@pytest.mark.asyncio
async def test_scan_policies_endpoint(async_client: AsyncClient, auth_headers: dict[str, str]) -> None:
    project_response = await async_client.post("/api/projects", json={"name": "policy-project"}, headers=auth_headers)
    project_id = project_response.json()["id"]
    env_response = await async_client.post(
        f"/api/projects/{project_id}/environments",
        json={"target": "local-k8s", "status": "active"},
        headers=auth_headers,
    )
    environment_id = env_response.json()["id"]

    files = {
        "file": (
            "template.zip",
            _build_zip(SAMPLES_VULNERABLE),
            "application/zip",
        )
    }
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

    mock_findings = [
        {
            "rule_id": "P2DP-K8S-001",
            "severity": "HIGH",
            "resource": "Pod/privileged-pod",
            "evidence": "Container app is privileged.",
            "recommendation": "Remove privileged=true from the container securityContext.",
        }
    ]
    with patch(
        "app.api.template_versions.scan_template_with_policies",
        return_value=mock_findings,
    ):
        response = await async_client.post(
            f"/api/template-versions/{template_version_id}/scan/policies",
            headers=auth_headers,
        )

    assert response.status_code == 201
    body = response.json()
    assert len(body) == 1
    assert body[0]["engine"] == "policies"
    assert body[0]["rule_id"] == "P2DP-K8S-001"
    assert body[0]["layer"] == "L2"
