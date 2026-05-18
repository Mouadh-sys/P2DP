import re
import shutil
import subprocess
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Environment, Finding
from app.services.scanner_service import run_checkov_scan, run_conftest_scan, run_trivy_scan
from app.services.scan_service import FINDING_LAYER, replace_findings_for_engine

PHASE_POST_DEPLOYMENT = "POST_DEPLOYMENT"
SCAN_TIMEOUT_SECONDS = 300


class PostDeploymentScanError(Exception):
    pass


def resolve_namespace(env_target: str) -> str:
    safe_target = re.sub(r"[^a-zA-Z0-9_-]", "", env_target) or "dev"
    return f"{settings.k8s_namespace_prefix}-{safe_target}"


def _kubectl_base_command() -> list[str]:
    command = ["kubectl"]
    if settings.kubectl_context:
        command.extend(["--context", settings.kubectl_context])
    return command


def export_live_cluster_state(workspace: Path, namespace: str) -> Path:
    scan_dir = workspace / "cluster-state"
    scan_dir.mkdir(parents=True, exist_ok=True)
    cluster_state_file = scan_dir / "cluster-state.yaml"

    namespaced_cmd = [
        *_kubectl_base_command(),
        "get",
        "deploy,svc,role,rolebinding",
        "-n",
        namespace,
        "-o",
        "yaml",
    ]
    cluster_cmd = [
        *_kubectl_base_command(),
        "get",
        "clusterrolebinding",
        "-o",
        "yaml",
    ]

    try:
        namespaced = subprocess.run(
            namespaced_cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=SCAN_TIMEOUT_SECONDS,
        )
        cluster = subprocess.run(
            cluster_cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=SCAN_TIMEOUT_SECONDS,
        )
    except FileNotFoundError as exc:
        raise PostDeploymentScanError("kubectl is not installed") from exc
    except subprocess.TimeoutExpired as exc:
        raise PostDeploymentScanError("kubectl export timed out") from exc

    if namespaced.returncode != 0:
        raise PostDeploymentScanError(namespaced.stderr or "Failed to export namespaced resources")

    documents = []
    if namespaced.stdout.strip():
        documents.append(namespaced.stdout.strip())
    if cluster.returncode == 0 and cluster.stdout.strip():
        documents.append(cluster.stdout.strip())

    if not documents:
        raise PostDeploymentScanError(f"No live resources found in namespace {namespace}")

    cluster_state_file.write_text("\n---\n".join(documents) + "\n", encoding="utf-8")
    return scan_dir


def export_gitops_fallback_state(env_target: str, workspace: Path) -> Path:
    safe_target = re.sub(r"[^a-zA-Z0-9_-]", "", env_target) or "dev"
    env_dir = Path(settings.resolved_gitops_repo_path) / "environments" / safe_target
    if not env_dir.exists():
        raise PostDeploymentScanError(f"GitOps environment folder not found: {env_dir}")

    deployment_dirs = sorted(
        [path for path in env_dir.iterdir() if path.is_dir()],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not deployment_dirs:
        raise PostDeploymentScanError("No rendered GitOps manifests available for post-deployment scan")

    scan_dir = workspace / "cluster-state"
    if scan_dir.exists():
        shutil.rmtree(scan_dir)
    shutil.copytree(deployment_dirs[0], scan_dir)
    return scan_dir


def collect_cluster_scan_path(env_target: str, workspace: Path) -> tuple[Path, str]:
    namespace = resolve_namespace(env_target)
    try:
        scan_dir = export_live_cluster_state(workspace, namespace)
        return scan_dir, f"live cluster namespace {namespace}"
    except PostDeploymentScanError as live_error:
        scan_dir = export_gitops_fallback_state(env_target, workspace)
        return scan_dir, f"gitops fallback ({live_error})"


def run_post_deployment_scanners(scan_dir: Path) -> tuple[dict[str, list[dict[str, str | None]]], dict[str, str]]:
    results: dict[str, list[dict[str, str | None]]] = {}
    errors: dict[str, str] = {}
    scan_path = str(scan_dir.resolve())

    scanners: list[tuple[str, object]] = [
        ("trivy", lambda path: run_trivy_scan(path)["findings"]),
        ("checkov", lambda path: run_checkov_scan(path)["findings"]),
        ("policies", lambda path: run_conftest_scan(path)["findings"]),
    ]

    for engine, scanner in scanners:
        try:
            results[engine] = scanner(scan_path)
        except Exception as exc:  # noqa: BLE001
            errors[engine] = str(exc)
            results[engine] = []

    return results, errors


def execute_post_deployment_scan(db: Session, env_id: uuid.UUID) -> dict[str, str | int]:
    environment = db.get(Environment, env_id)
    if not environment:
        raise ValueError("Environment not found")

    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        scan_dir, source = collect_cluster_scan_path(environment.target, workspace)
        results, errors = run_post_deployment_scanners(scan_dir)

        saved = 0
        for engine, payloads in results.items():
            replace_findings_for_engine(
                db,
                env_id,
                engine,
                payloads,
                phase=PHASE_POST_DEPLOYMENT,
            )
            saved += len(payloads)
        db.commit()

        if errors and saved == 0:
            raise PostDeploymentScanError("; ".join(f"{engine}: {message}" for engine, message in errors.items()))

        return {
            "status": "SUCCESS" if saved > 0 or not errors else "PARTIAL",
            "source": source,
            "findings_count": saved,
            "errors": "; ".join(f"{engine}: {message}" for engine, message in errors.items()) if errors else "",
        }
