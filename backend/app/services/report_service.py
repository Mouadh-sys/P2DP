import html
import uuid
from collections import Counter
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DeploymentRun, Environment, Finding, Project, Report, RiskAssessment, ThreatAlert
from app.services.risk_service import parse_assessment_payload
from app.services.storage_service import storage_service

SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}


def _severity_rank(severity: str) -> int:
    return SEVERITY_ORDER.get(severity.upper(), 5)


def _build_report_html(
    *,
    generated_at: datetime,
    project_name: str,
    env_target: str,
    env_status: str,
    deployment_id: str | None,
    deployment_status: str | None,
    git_commit: str | None,
    trace_id: str | None,
    risk_score: float | None,
    risk_class: str | None,
    findings_summary: str,
    top_findings_rows: list[dict[str, str | None]],
    threat_rows: list[dict[str, str | None]],
    log_threat_rows: list[dict[str, str | None]],
    recommendations: list[str],
) -> str:
    def h(s: object | None) -> str:
        return html.escape("" if s is None else str(s))

    top_rows = "".join(
        f"<tr><td>{h(r.get('severity'))}</td><td>{h(r.get('rule_id'))}</td>"
        f"<td>{h(r.get('engine'))}</td><td>{h(r.get('resource'))}</td>"
        f"<td>{h(r.get('evidence'))}</td></tr>"
        for r in top_findings_rows
    )
    if not top_findings_rows:
        top_rows = "<tr><td colspan='5'>No findings match the top-severity criteria.</td></tr>"

    threats = "".join(
        f"<tr><td>{h(t.get('timestamp'))}</td><td>{h(t.get('source'))}</td><td>{h(t.get('type'))}</td>"
        f"<td>{h(t.get('severity'))}</td><td>{h(t.get('evidence'))}</td><td>{h(t.get('status'))}</td></tr>"
        for t in threat_rows
    )
    if not threat_rows:
        threats = "<tr><td colspan='6'>No threat alert records for this environment.</td></tr>"

    logs = "".join(
        f"<tr><td>{h(x.get('severity'))}</td><td>{h(x.get('rule_id'))}</td>"
        f"<td>{h(x.get('resource'))}</td><td>{h(x.get('evidence'))}</td></tr>"
        for x in log_threat_rows
    )
    if not log_threat_rows:
        logs = "<tr><td colspan='4'>None</td></tr>"

    recs = "".join(f"<li>{h(rec)}</li>" for rec in recommendations) or "<li>No recommendations available.</li>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>P2DP security report — {h(project_name)}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; color: #0f172a; }}
    h1 {{ font-size: 1.5rem; }}
    h2 {{ font-size: 1.1rem; margin-top: 1.5rem; border-bottom: 1px solid #e2e8f0; padding-bottom: 0.25rem; }}
    table {{ border-collapse: collapse; width: 100%; font-size: 0.85rem; margin-top: 0.5rem; }}
    th, td {{ border: 1px solid #cbd5e1; padding: 0.35rem 0.5rem; vertical-align: top; }}
    th {{ background: #f1f5f9; text-align: left; }}
    .meta dt {{ font-weight: 600; }}
    .meta dd {{ margin: 0 0 0.5rem 1rem; }}
  </style>
</head>
<body>
  <h1>P2DP — environment security report</h1>
  <p>Format: HTML (MVP). PDF may be added later.</p>

  <h2>Summary</h2>
  <dl class="meta">
    <dt>Timestamp</dt><dd>{h(generated_at.isoformat())}</dd>
    <dt>Project name</dt><dd>{h(project_name)}</dd>
    <dt>Environment</dt><dd>{h(env_target)} (status: {h(env_status)})</dd>
    <dt>Deployment ID</dt><dd>{h(deployment_id)}</dd>
    <dt>Git commit</dt><dd>{h(git_commit)}</dd>
    <dt>Deployment status</dt><dd>{h(deployment_status)}</dd>
    <dt>Risk score</dt><dd>{h(risk_score)} ({h(risk_class)})</dd>
    <dt>Trace ID</dt><dd>{h(trace_id)}</dd>
  </dl>

  <h2>Findings summary</h2>
  <pre style="white-space: pre-wrap; background: #f8fafc; padding: 1rem;">{h(findings_summary)}</pre>

  <h2>Top critical findings</h2>
  <table>
    <thead><tr><th>Severity</th><th>Rule</th><th>Engine</th><th>Resource</th><th>Evidence</th></tr></thead>
    <tbody>{top_rows}</tbody>
  </table>

  <h2>Threat alerts</h2>
  <table>
    <thead><tr><th>Time</th><th>Source</th><th>Type</th><th>Severity</th><th>Evidence</th><th>Status</th></tr></thead>
    <tbody>{threats}</tbody>
  </table>

  <h2>Log-based / simulated runtime alerts (L4)</h2>
  <p>Derived from simulated log detections stored as findings (<code>simulated_logs</code>).</p>
  <table>
    <thead><tr><th>Severity</th><th>Rule</th><th>Resource</th><th>Evidence</th></tr></thead>
    <tbody>{logs}</tbody>
  </table>

  <h2>Recommendations</h2>
  <ul>{recs}</ul>
</body>
</html>
"""


async def create_html_report_for_environment(
    db: AsyncSession,
    environment: Environment,
    project: Project,
) -> Report:
    """Aggregate environment data, render HTML, upload to MinIO, persist Report row."""
    report_id = uuid.uuid4()

    dep_result = await db.execute(
        select(DeploymentRun)
        .where(DeploymentRun.env_id == environment.id)
        .order_by(DeploymentRun.started_at.desc())
        .limit(1)
    )
    deployment = dep_result.scalar_one_or_none()

    ra_result = await db.execute(
        select(RiskAssessment)
        .where(RiskAssessment.env_id == environment.id)
        .order_by(RiskAssessment.timestamp.desc())
        .limit(1)
    )
    assessment = ra_result.scalar_one_or_none()

    findings_result = await db.execute(select(Finding).where(Finding.env_id == environment.id))
    findings = list(findings_result.scalars().all())

    threats_result = await db.execute(
        select(ThreatAlert).where(ThreatAlert.env_id == environment.id).order_by(ThreatAlert.timestamp.desc()).limit(50)
    )
    threat_alerts = list(threats_result.scalars().all())

    by_severity = Counter(f.severity.upper() for f in findings)
    by_engine = Counter(f.engine for f in findings)
    summary_lines = [
        f"Total findings: {len(findings)}",
        "By severity: " + ", ".join(f"{k}: {v}" for k, v in sorted(by_severity.items())),
        "By engine: " + ", ".join(f"{k}: {v}" for k, v in sorted(by_engine.items())),
    ]
    findings_summary = "\n".join(summary_lines)

    ranked = sorted(findings, key=lambda f: (_severity_rank(f.severity), f.rule_id))
    critical_pool = [f for f in ranked if f.severity.upper() in {"CRITICAL", "HIGH"}]
    if not critical_pool:
        critical_pool = ranked[:10]
    else:
        critical_pool = critical_pool[:10]

    top_findings_rows = [
        {"severity": f.severity, "rule_id": f.rule_id, "engine": f.engine, "resource": f.resource, "evidence": f.evidence}
        for f in critical_pool
    ]

    threat_rows = [
        {
            "timestamp": t.timestamp.isoformat() if t.timestamp else "",
            "source": t.source,
            "type": t.type,
            "severity": t.severity,
            "evidence": t.evidence,
            "status": t.status,
        }
        for t in threat_alerts
    ]

    log_threat_rows = [
        {"severity": f.severity, "rule_id": f.rule_id, "resource": f.resource, "evidence": f.evidence}
        for f in findings
        if f.engine == "simulated_logs"
    ]

    recommendations: list[str] = []
    risk_score: float | None = None
    risk_class: str | None = None
    if assessment:
        payload = parse_assessment_payload(assessment)
        risk_score = float(payload["score"])
        risk_class = str(payload["risk_class"])
        recommendations = list(payload.get("recommendations") or [])

    generated_at = datetime.now(timezone.utc)
    html_doc = _build_report_html(
        generated_at=generated_at,
        project_name=project.name,
        env_target=environment.target,
        env_status=environment.status,
        deployment_id=str(deployment.id) if deployment else None,
        deployment_status=deployment.status if deployment else None,
        git_commit=deployment.git_commit if deployment else None,
        trace_id=deployment.trace_id if deployment else None,
        risk_score=risk_score,
        risk_class=risk_class,
        findings_summary=findings_summary,
        top_findings_rows=top_findings_rows,
        threat_rows=threat_rows,
        log_threat_rows=log_threat_rows,
        recommendations=recommendations,
    )

    object_key = storage_service.report_object_key(project.id, environment.id, report_id)
    storage_service.upload_text(object_key, html_doc, "text/html")

    report = Report(id=report_id, env_id=environment.id, storage_ref=object_key)
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report
