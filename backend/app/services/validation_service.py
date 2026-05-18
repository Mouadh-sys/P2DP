import json
import re
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path

from app.services.scanner_service import _template_workspace
from app.services.storage_service import storage_service

VALIDATION_TIMEOUT_SECONDS = 600
DOCKERFILE_FROM_PATTERN = re.compile(r"^\s*FROM\s+\S+", re.IGNORECASE | re.MULTILINE)


@dataclass
class ValidationOutcome:
    success: bool
    log: str
    template_types: list[str]
    storage_ref: str


def detect_template_types(workspace: Path) -> list[str]:
    types: list[str] = []
    if any(workspace.rglob("*.tf")):
        types.append("terraform")
    if any(
        path.is_file() and (path.name == "Dockerfile" or path.name.lower().startswith("dockerfile."))
        for path in workspace.rglob("*")
    ):
        types.append("dockerfile")
    if any(workspace.rglob("*.yaml")) or any(workspace.rglob("*.yml")):
        types.append("kubernetes")
    return types


def _run_command(command: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
        timeout=VALIDATION_TIMEOUT_SECONDS,
    )


def _append_section(log_parts: list[str], title: str, result: subprocess.CompletedProcess[str]) -> bool:
    log_parts.append(f"=== {title} ===\n")
    if result.stdout:
        log_parts.append(result.stdout)
        if not result.stdout.endswith("\n"):
            log_parts.append("\n")
    if result.stderr:
        log_parts.append(result.stderr)
        if not result.stderr.endswith("\n"):
            log_parts.append("\n")
    return result.returncode == 0


def _terraform_roots(workspace: Path) -> list[Path]:
    roots: set[Path] = set()
    for tf_file in workspace.rglob("*.tf"):
        roots.add(tf_file.parent)
    return sorted(roots, key=lambda path: len(path.parts))


def validate_kubernetes(workspace: Path, log_parts: list[str]) -> bool:
    manifests = [path for path in workspace.rglob("*") if path.is_file() and path.suffix in {".yaml", ".yml"}]
    if not manifests:
        log_parts.append("=== kubernetes ===\nNo Kubernetes manifests found.\n")
        return True

    try:
        result = _run_command(["kubectl", "apply", "--dry-run=server", "-f", str(workspace)])
    except FileNotFoundError:
        log_parts.append("=== kubernetes ===\nkubectl is not installed.\n")
        return False
    except subprocess.TimeoutExpired:
        log_parts.append("=== kubernetes ===\nkubectl validation timed out.\n")
        return False

    ok = _append_section(log_parts, "kubectl apply --dry-run=server", result)
    if not ok:
        log_parts.append("kubectl server dry-run failed; retrying with client dry-run.\n")
        try:
            client_result = _run_command(["kubectl", "apply", "--dry-run=client", "-f", str(workspace)])
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
        ok = _append_section(log_parts, "kubectl apply --dry-run=client", client_result)
    return ok


def validate_terraform(workspace: Path, log_parts: list[str]) -> bool:
    roots = _terraform_roots(workspace)
    if not roots:
        log_parts.append("=== terraform ===\nNo Terraform files found.\n")
        return True

    success = True
    for root in roots:
        relative = root.relative_to(workspace)
        label = "." if relative == Path(".") else str(relative)
        log_parts.append(f"=== terraform ({label}) ===\n")

        for step_name, command in (
            ("terraform init", ["terraform", "init", "-input=false", "-no-color"]),
            ("terraform validate", ["terraform", "validate", "-no-color"]),
            (
                "terraform plan",
                ["terraform", "plan", "-input=false", "-no-color", "-out=tfplan"],
            ),
        ):
            try:
                result = _run_command(command, cwd=root)
            except FileNotFoundError:
                log_parts.append("terraform is not installed.\n")
                return False
            except subprocess.TimeoutExpired:
                log_parts.append(f"{step_name} timed out.\n")
                return False

            if not _append_section(log_parts, step_name, result):
                success = False
                break

        if not success:
            continue

        plan_path = root / "tfplan"
        if not plan_path.exists():
            log_parts.append("terraform plan file was not created.\n")
            success = False
            continue

        try:
            show_result = _run_command(["terraform", "show", "-json", "tfplan"], cwd=root)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            success = False
            continue

        if not _append_section(log_parts, "terraform show -json tfplan", show_result):
            success = False
            continue

        if show_result.stdout.strip():
            try:
                json.loads(show_result.stdout)
                log_parts.append("terraform plan JSON parsed successfully.\n")
            except json.JSONDecodeError:
                log_parts.append("terraform show -json output is not valid JSON.\n")
                success = False

    return success


def validate_dockerfile(workspace: Path, log_parts: list[str]) -> bool:
    dockerfiles = [
        path
        for path in workspace.rglob("*")
        if path.is_file() and (path.name == "Dockerfile" or path.name.lower().startswith("dockerfile."))
    ]
    if not dockerfiles:
        log_parts.append("=== dockerfile ===\nNo Dockerfile found.\n")
        return True

    success = True
    for dockerfile in dockerfiles:
        log_parts.append(f"=== dockerfile ({dockerfile.relative_to(workspace)}) ===\n")
        build_dir = dockerfile.parent

        try:
            result = _run_command(["docker", "build", "--check", "."], cwd=build_dir)
            if _append_section(log_parts, "docker build --check", result):
                continue
        except FileNotFoundError:
            log_parts.append("docker CLI not available; falling back to basic Dockerfile parsing.\n")
        except subprocess.TimeoutExpired:
            log_parts.append("docker build --check timed out.\n")
            success = False
            continue

        try:
            content = dockerfile.read_text(encoding="utf-8")
        except OSError as exc:
            log_parts.append(f"Failed to read Dockerfile: {exc}\n")
            success = False
            continue

        if DOCKERFILE_FROM_PATTERN.search(content):
            log_parts.append("Basic Dockerfile parsing passed (FROM instruction present).\n")
        else:
            log_parts.append("Basic Dockerfile parsing failed: missing FROM instruction.\n")
            success = False

    return success


def run_validation(
    files_ref: str,
    project_id: uuid.UUID,
    environment_id: uuid.UUID,
    template_version_id: uuid.UUID,
) -> ValidationOutcome:
    log_parts: list[str] = []
    overall_success = True
    detected_types: list[str] = []

    with _template_workspace(files_ref) as workspace_str:
        workspace = Path(workspace_str)
        detected_types = detect_template_types(workspace)
        log_parts.append(f"Detected template types: {', '.join(detected_types) or 'unknown'}\n\n")

        if "kubernetes" in detected_types:
            if not validate_kubernetes(workspace, log_parts):
                overall_success = False
        if "terraform" in detected_types:
            if not validate_terraform(workspace, log_parts):
                overall_success = False
        if "dockerfile" in detected_types:
            if not validate_dockerfile(workspace, log_parts):
                overall_success = False

        if not detected_types:
            log_parts.append("No supported template files detected for validation.\n")
            overall_success = False

    log_text = "".join(log_parts)
    storage_ref = storage_service.validation_log_key(project_id, environment_id, template_version_id)
    storage_service.upload_text(storage_ref, log_text)

    return ValidationOutcome(
        success=overall_success,
        log=log_text,
        template_types=detected_types,
        storage_ref=storage_ref,
    )
