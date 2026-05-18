import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.db.models import Finding, PreDeploymentScan, TemplateVersion
from app.services.scanner_service import (
    scan_template_with_checkov,
    scan_template_with_policies,
    scan_template_with_trivy,
)

FINDING_LAYER = "L2"
PHASE_PRE_DEPLOYMENT = "PRE_DEPLOYMENT"


def get_scan_engines() -> list[tuple[str, object]]:
    return [
        ("trivy", scan_template_with_trivy),
        ("checkov", scan_template_with_checkov),
        ("policies", scan_template_with_policies),
    ]


def replace_findings_for_engine(
    db: Session,
    env_id: uuid.UUID,
    engine: str,
    payloads: list[dict[str, str | None]],
    phase: str = PHASE_PRE_DEPLOYMENT,
    finding_layer: str | None = None,
) -> list[Finding]:
    layer = finding_layer if finding_layer is not None else FINDING_LAYER
    db.execute(
        delete(Finding).where(
            Finding.env_id == env_id,
            Finding.engine == engine,
            Finding.phase == phase,
            Finding.layer == layer,
        )
    )
    findings = [
        Finding(
            env_id=env_id,
            layer=layer,
            phase=phase,
            engine=engine,
            rule_id=payload["rule_id"],
            severity=payload["severity"],
            resource=payload["resource"],
            evidence=payload.get("evidence"),
            recommendation=payload.get("recommendation"),
        )
        for payload in payloads
    ]
    db.add_all(findings)
    return findings


def run_pre_deployment_scan(files_ref: str) -> tuple[dict[str, list[dict[str, str | None]]], dict[str, str]]:
    results: dict[str, list[dict[str, str | None]]] = {}
    errors: dict[str, str] = {}

    for engine, scanner in get_scan_engines():
        try:
            results[engine] = scanner(files_ref)
        except Exception as exc:  # noqa: BLE001 - collect per-engine failures for unified scan
            errors[engine] = str(exc)
            results[engine] = []

    return results, errors


def execute_pre_deployment_scan(db: Session, scan: PreDeploymentScan) -> None:
    template_version = db.get(TemplateVersion, scan.template_version_id)
    if not template_version:
        raise ValueError("Template version not found")

    scan.status = "RUNNING"
    scan.started_at = datetime.now(timezone.utc)
    db.commit()

    try:
        results, errors = run_pre_deployment_scan(template_version.files_ref)
        for engine, payloads in results.items():
            replace_findings_for_engine(db, scan.env_id, engine, payloads, phase=PHASE_PRE_DEPLOYMENT)
        db.commit()

        if errors and not any(results.values()):
            scan.status = "FAILED"
            scan.error_message = "; ".join(f"{engine}: {message}" for engine, message in errors.items())
        else:
            scan.status = "SUCCESS"
            if errors:
                scan.error_message = "; ".join(f"{engine}: {message}" for engine, message in errors.items())
            else:
                scan.error_message = None
    except Exception as exc:  # noqa: BLE001
        scan.status = "FAILED"
        scan.error_message = str(exc)
        raise
    finally:
        scan.finished_at = datetime.now(timezone.utc)
        db.commit()


def count_scan_findings(db: Session, env_id: uuid.UUID) -> int:
    return int(db.scalar(select(func.count()).select_from(Finding).where(Finding.env_id == env_id)) or 0)
