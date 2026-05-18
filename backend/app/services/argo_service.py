import os
import subprocess

from app.core.config import settings


class ArgoSyncError(Exception):
    pass


def sync_application(deployment_id: str) -> str:
    if not settings.argocd_server:
        return "skipped: ARGOCD_SERVER not configured"

    app_name = settings.argocd_app_name
    command = ["argocd", "app", "sync", app_name, "--grpc-web", "--server", settings.argocd_server]
    if settings.argocd_token:
        command.extend(["--auth-token", settings.argocd_token])

    env = os.environ.copy()
    if settings.argocd_token:
        env["ARGOCD_AUTH_TOKEN"] = settings.argocd_token

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=180,
            env=env,
        )
    except FileNotFoundError as exc:
        raise ArgoSyncError("argocd CLI is not installed") from exc
    except subprocess.TimeoutExpired as exc:
        raise ArgoSyncError("argocd sync timed out") from exc

    if result.returncode != 0:
        raise ArgoSyncError(result.stderr or result.stdout or "argocd sync failed")

    return f"synced application {app_name} for deployment {deployment_id}"
