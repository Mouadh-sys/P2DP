import json
import uuid
from dataclasses import dataclass
from typing import Callable

from app.db.models import Finding, RiskAssessment

FINDING_LAYER = "L2"


@dataclass(frozen=True)
class RiskFactorDefinition:
    key: str
    label: str
    weight: int
    impact: str
    recommendation: str
    matcher: Callable[[Finding], bool]


RISK_FACTOR_DEFINITIONS: tuple[RiskFactorDefinition, ...] = (
    RiskFactorDefinition(
        key="public_exposure",
        label="Internet-facing exposure",
        weight=25,
        impact="Public or node-port services increase attack surface and exposure to untrusted networks.",
        recommendation="Prefer ClusterIP or internal ingress; document justification for any public endpoint.",
        matcher=lambda finding: (
            finding.rule_id == "P2DP-K8S-005"
            or "loadbalancer" in _text(finding)
            or "nodeport" in _text(finding)
            or "internet" in _text(finding)
        ),
    ),
    RiskFactorDefinition(
        key="rbac_privilege",
        label="RBAC wildcard / cluster-admin",
        weight=25,
        impact="Over-privileged RBAC bindings enable broad cluster compromise if credentials leak.",
        recommendation="Replace cluster-admin bindings with least-privilege Roles and ClusterRoles.",
        matcher=lambda finding: (
            finding.rule_id == "P2DP-K8S-006"
            or "cluster-admin" in _text(finding)
            or "cluster_admin" in finding.rule_id.lower()
            or "wildcard" in _text(finding)
        ),
    ),
    RiskFactorDefinition(
        key="workload_hardening",
        label="Privileged workload / root / hostPath",
        weight=25,
        impact="Privileged or root workloads and hostPath mounts weaken container isolation.",
        recommendation="Drop privileged mode, enforce runAsNonRoot, and avoid hostPath unless strictly required.",
        matcher=lambda finding: (
            finding.rule_id in {"P2DP-K8S-001", "P2DP-K8S-002", "P2DP-K8S-003", "P2DP-K8S-004"}
            or "privileged" in _text(finding)
            or "hostpath" in _text(finding)
            or "runasuser" in _text(finding)
            or "run as root" in _text(finding)
        ),
    ),
    RiskFactorDefinition(
        key="network_segmentation",
        label="Missing NetworkPolicy",
        weight=15,
        impact="Without network policies, compromised pods can move laterally with fewer controls.",
        recommendation="Add NetworkPolicy resources to restrict ingress and egress between workloads.",
        matcher=lambda finding: (
            "networkpolicy" in finding.rule_id.lower()
            or "network policy" in _text(finding)
            or "CKV2_K8S_28" in finding.rule_id
            or "no network" in _text(finding)
        ),
    ),
    RiskFactorDefinition(
        key="logging_audit",
        label="Missing logging / audit",
        weight=10,
        impact="Insufficient audit and application logging slows detection and incident response.",
        recommendation="Enable Kubernetes audit logging and workload log shipping to a central store.",
        matcher=lambda finding: (
            "audit" in finding.rule_id.lower()
            or "logging" in finding.rule_id.lower()
            or "audit" in _text(finding)
            or "logging" in _text(finding)
        ),
    ),
)


def _text(finding: Finding) -> str:
    return " ".join(
        part
        for part in (finding.rule_id, finding.resource, finding.evidence or "", finding.recommendation or "")
        if part
    ).lower()


def _risk_class(score: float) -> str:
    if score < 30:
        return "LOW"
    if score < 70:
        return "MEDIUM"
    return "HIGH"


def calculate_risk_from_findings(findings: list[Finding]) -> dict:
    layer_findings = [finding for finding in findings if finding.layer == FINDING_LAYER]
    triggered: list[dict] = []

    for definition in RISK_FACTOR_DEFINITIONS:
        matched_rules = sorted(
            {
                finding.rule_id
                for finding in layer_findings
                if definition.matcher(finding)
            }
        )
        if not matched_rules:
            continue

        triggered.append(
            {
                "key": definition.key,
                "label": definition.label,
                "weight": definition.weight,
                "contribution": definition.weight,
                "impact": definition.impact,
                "recommendation": definition.recommendation,
                "findings": matched_rules,
            }
        )

    score = min(100.0, float(sum(item["contribution"] for item in triggered)))
    top_factors = sorted(triggered, key=lambda item: item["contribution"], reverse=True)[:3]
    recommendations = list(dict.fromkeys(item["recommendation"] for item in triggered))

    return {
        "score": score,
        "risk_class": _risk_class(score),
        "factors": triggered,
        "top_factors": top_factors,
        "recommendations": recommendations,
    }


def build_risk_assessment(env_id: uuid.UUID, findings: list[Finding]) -> RiskAssessment:
    result = calculate_risk_from_findings(findings)
    return RiskAssessment(
        env_id=env_id,
        score=result["score"],
        class_=result["risk_class"],
        factors_json=json.dumps(
            {
                "factors": result["factors"],
                "top_factors": result["top_factors"],
                "recommendations": result["recommendations"],
            }
        ),
    )


def parse_assessment_payload(assessment: RiskAssessment) -> dict:
    payload = json.loads(assessment.factors_json)
    return {
        "id": assessment.id,
        "env_id": assessment.env_id,
        "score": assessment.score,
        "risk_class": assessment.class_,
        "factors": payload.get("factors", []),
        "top_factors": payload.get("top_factors", []),
        "recommendations": payload.get("recommendations", []),
        "timestamp": assessment.timestamp,
    }
