import os
import re
import shutil
import subprocess
import uuid
from pathlib import Path

from app.core.config import settings
from app.services.scanner_service import _template_workspace

MANIFEST_EXTENSIONS = {".yaml", ".yml"}
GIT_TIMEOUT_SECONDS = 120


class GitOpsError(Exception):
    pass


def _repo_path() -> Path:
    return Path(settings.resolved_gitops_repo_path)


def _run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    if settings.github_token and "github.com" in settings.gitops_remote_url:
        env["GIT_ASKPASS"] = "echo"
        env["GIT_TERMINAL_PROMPT"] = "0"
    try:
        return subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=False,
            timeout=GIT_TIMEOUT_SECONDS,
            env=env,
        )
    except FileNotFoundError as exc:
        raise GitOpsError("git is not installed") from exc
    except subprocess.TimeoutExpired as exc:
        raise GitOpsError("git command timed out") from exc


def _ensure_git_repository(repo_path: Path) -> None:
    if (repo_path / ".git").exists():
        return
    repo_path.mkdir(parents=True, exist_ok=True)
    init_result = _run_git(["init"], repo_path)
    if init_result.returncode != 0:
        raise GitOpsError(init_result.stderr or "Failed to initialize git repository")
    _run_git(["config", "user.name", settings.gitops_git_user], repo_path)
    _run_git(["config", "user.email", settings.gitops_git_email], repo_path)


def _sanitize_env_target(target: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]", "", target)
    return cleaned or "dev"


def _write_deployment_metadata(target_dir: Path, deployment_id: uuid.UUID, env_target: str) -> None:
    metadata = f"""apiVersion: v1
kind: ConfigMap
metadata:
  name: p2dp-deployment-metadata
  labels:
    p2dp.deployment/id: "{deployment_id}"
    p2dp.environment/target: "{env_target}"
data:
  deployment_id: "{deployment_id}"
  environment: "{env_target}"
"""
    (target_dir / "p2dp-deployment-metadata.yaml").write_text(metadata, encoding="utf-8")


def copy_manifests_to_gitops(
    files_ref: str,
    env_target: str,
    deployment_id: uuid.UUID,
) -> Path:
    safe_target = _sanitize_env_target(env_target)
    destination_root = _repo_path() / "environments" / safe_target / str(deployment_id)
    if destination_root.exists():
        shutil.rmtree(destination_root)
    destination_root.mkdir(parents=True, exist_ok=True)

    with _template_workspace(files_ref) as workspace_str:
        workspace = Path(workspace_str)
        copied = 0
        for path in workspace.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() not in MANIFEST_EXTENSIONS:
                continue
            relative = path.relative_to(workspace)
            dest = destination_root / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)
            copied += 1

        if copied == 0:
            raise GitOpsError("No Kubernetes manifests (.yaml/.yml) found in uploaded template")

        _write_deployment_metadata(destination_root, deployment_id, safe_target)

    return destination_root


def commit_and_push(deployment_id: uuid.UUID, env_target: str) -> str:
    repo_path = _repo_path()
    _ensure_git_repository(repo_path)

    safe_target = _sanitize_env_target(env_target)
    commit_message = f"deploy(env:{safe_target}): deployment {deployment_id}"

    add_result = _run_git(["add", "environments"], repo_path)
    if add_result.returncode != 0:
        raise GitOpsError(add_result.stderr or "git add failed")

    commit_result = _run_git(["commit", "-m", commit_message], repo_path)
    if commit_result.returncode != 0:
        if "nothing to commit" in (commit_result.stdout + commit_result.stderr).lower():
            raise GitOpsError("No changes to commit for deployment")
        raise GitOpsError(commit_result.stderr or "git commit failed")

    rev_result = _run_git(["rev-parse", "HEAD"], repo_path)
    if rev_result.returncode != 0:
        raise GitOpsError("Failed to resolve git commit hash")
    commit_hash = rev_result.stdout.strip()

    if settings.gitops_remote_url:
        remote_url = settings.gitops_remote_url
        if settings.github_token and remote_url.startswith("https://github.com"):
            remote_url = remote_url.replace(
                "https://github.com",
                f"https://{settings.github_token}@github.com",
                1,
            )
        existing_remote = _run_git(["remote", "get-url", "origin"], repo_path)
        if existing_remote.returncode != 0:
            remote_add = _run_git(["remote", "add", "origin", remote_url], repo_path)
            if remote_add.returncode != 0:
                raise GitOpsError(remote_add.stderr or "git remote add failed")
        branch_result = _run_git(["branch", "--show-current"], repo_path)
        branch = branch_result.stdout.strip() or "main"
        push_result = _run_git(["push", "-u", "origin", branch], repo_path)
        if push_result.returncode != 0:
            raise GitOpsError(push_result.stderr or "git push failed")

    return commit_hash
