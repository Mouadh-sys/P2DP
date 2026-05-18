import uuid

import pytest
from httpx import AsyncClient

from app.db.database import get_db
from app.db.models import Finding
from app.main import app
from app.services.risk_service import calculate_risk_from_findings


def _finding(env_id: uuid.UUID, rule_id: str, evidence: str | None = None) -> Finding:
    return Finding(
        env_id=env_id,
        layer="L2",
        phase="PRE_DEPLOYMENT",
        engine="policies",
        rule_id=rule_id,
        severity="HIGH",
        resource="Pod/demo",
        evidence=evidence,
        recommendation=None,
    )


def test_example_scenario_scores_high() -> None:
    env_id = uuid.uuid4()
    findings = [
        _finding(env_id, "P2DP-K8S-005", "Service type LoadBalancer requires justification."),
        _finding(env_id, "P2DP-K8S-001", "Container app is privileged."),
        _finding(env_id, "P2DP-K8S-006", "ClusterRoleBinding grants cluster-admin."),
        _finding(env_id, "CKV2_K8S_28", "No NetworkPolicy resource found"),
    ]
    result = calculate_risk_from_findings(findings)

    assert result["score"] == 90
    assert result["risk_class"] == "HIGH"
    assert len(result["factors"]) == 4
    assert result["top_factors"][0]["contribution"] == 25


def test_low_score_when_no_findings() -> None:
    result = calculate_risk_from_findings([])
    assert result["score"] == 0
    assert result["risk_class"] == "LOW"


def test_medium_score_boundary() -> None:
    env_id = uuid.uuid4()
    findings = [_finding(env_id, "P2DP-K8S-005")]
    result = calculate_risk_from_findings(findings)
    assert result["score"] == 25
    assert result["risk_class"] == "LOW"


@pytest.mark.asyncio
async def test_risk_assessment_endpoints(async_client: AsyncClient, auth_headers: dict[str, str]) -> None:
    project_response = await async_client.post("/api/projects", json={"name": "risk-project"}, headers=auth_headers)
    project_id = project_response.json()["id"]
    env_response = await async_client.post(
        f"/api/projects/{project_id}/environments",
        json={"target": "dev", "status": "active"},
        headers=auth_headers,
    )
    environment_id = uuid.UUID(env_response.json()["id"])

    session_gen = app.dependency_overrides[get_db]()
    db = await session_gen.__anext__()
    try:
        db.add(_finding(environment_id, "P2DP-K8S-005"))
        db.add(_finding(environment_id, "P2DP-K8S-001"))
        await db.commit()
    finally:
        await session_gen.aclose()

    create_response = await async_client.post(
        f"/api/environments/{environment_id}/risk-assessments",
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    body = create_response.json()
    assert body["score"] == 50
    assert body["risk_class"] == "MEDIUM"
    assert len(body["factors"]) == 2
    assert body["top_factors"]

    latest_response = await async_client.get(
        f"/api/environments/{environment_id}/risk-assessments/latest",
        headers=auth_headers,
    )
    assert latest_response.status_code == 200
    assert latest_response.json()["id"] == body["id"]
