import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.db.models import Environment, Finding, Project, User, UserRole
from app.services.post_deployment_scan_service import (
    PHASE_POST_DEPLOYMENT,
    execute_post_deployment_scan,
    export_gitops_fallback_state,
    resolve_namespace,
    run_post_deployment_scanners,
)


def test_resolve_namespace() -> None:
    assert resolve_namespace("dev") == "p2dp-dev"
    assert resolve_namespace("local-k8s") == "p2dp-local-k8s"


@patch("app.services.post_deployment_scan_service.run_conftest_scan")
@patch("app.services.post_deployment_scan_service.run_checkov_scan")
@patch("app.services.post_deployment_scan_service.run_trivy_scan")
def test_run_post_deployment_scanners(
    mock_trivy: MagicMock,
    mock_checkov: MagicMock,
    mock_conftest: MagicMock,
    tmp_path: Path,
) -> None:
    mock_trivy.return_value = {
        "findings": [{"rule_id": "TV-1", "severity": "HIGH", "resource": "Pod/x", "evidence": "e", "recommendation": "r"}]
    }
    mock_checkov.return_value = {"findings": []}
    mock_conftest.return_value = {"findings": []}

    results, errors = run_post_deployment_scanners(tmp_path)
    assert len(results["trivy"]) == 1
    assert errors == {}


def test_export_gitops_fallback_state(tmp_path: Path) -> None:
    repo = tmp_path / "gitops-repo"
    deployment_dir = repo / "environments" / "dev" / str(uuid.uuid4())
    deployment_dir.mkdir(parents=True)
    (deployment_dir / "deployment.yaml").write_text(
        "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: demo\n",
        encoding="utf-8",
    )

    with patch("app.services.post_deployment_scan_service.settings") as settings_mock:
        settings_mock.resolved_gitops_repo_path = str(repo)
        scan_dir = export_gitops_fallback_state("dev", tmp_path / "workspace")

    assert (scan_dir / "deployment.yaml").exists()


@patch("app.services.post_deployment_scan_service.analyze_simulated_logs_for_threats", return_value=[])
@patch("app.services.post_deployment_scan_service.run_post_deployment_scanners")
@patch("app.services.post_deployment_scan_service.collect_cluster_scan_path")
def test_execute_post_deployment_scan_saves_post_phase_findings(
    mock_collect: MagicMock,
    mock_scanners: MagicMock,
    tmp_path: Path,
) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    scan_dir = tmp_path / "cluster-state"
    scan_dir.mkdir()
    (scan_dir / "cluster-state.yaml").write_text("apiVersion: v1\nkind: ConfigMap\n", encoding="utf-8")
    mock_collect.return_value = (scan_dir, "gitops fallback")
    mock_scanners.return_value = (
        {
            "trivy": [
                {
                    "rule_id": "TV-POST",
                    "severity": "HIGH",
                    "resource": "Pod/live",
                    "evidence": None,
                    "recommendation": None,
                }
            ],
            "checkov": [],
            "policies": [],
        },
        {},
    )

    with SessionLocal() as db:
        user = User(email="scan@example.com", password_hash="x", role=UserRole.DEVOPS)
        db.add(user)
        db.flush()
        project = Project(name="p", owner_id=user.id)
        db.add(project)
        db.flush()
        environment = Environment(project_id=project.id, target="dev", status="active")
        db.add(environment)
        db.commit()

        result = execute_post_deployment_scan(db, environment.id)
        assert result["findings_count"] == 1

        findings = list(db.execute(select(Finding).where(Finding.env_id == environment.id)).scalars().all())
        assert len(findings) == 1
        assert findings[0].phase == PHASE_POST_DEPLOYMENT
        assert findings[0].engine == "trivy"
