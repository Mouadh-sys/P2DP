import json
import os
import shutil
import stat
import subprocess
import tarfile
import tempfile
import zipfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from fastapi import HTTPException, status

from app.services.storage_service import storage_service

ALLOWED_SEVERITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
SCAN_TIMEOUT_SECONDS = 300
POLICY_DIR = Path(__file__).resolve().parents[1] / "policies"


def _normalize_severity(value: str | None) -> str:
    if not value:
        return "LOW"
    normalized = value.upper()
    if normalized in ALLOWED_SEVERITIES:
        return normalized
    if normalized in {"UNKNOWN", "UNDEFINED", "INFO", "INFORMATIONAL", "NOTICE"}:
        return "LOW"
    return "LOW"


def _is_safe_member(name: str) -> bool:
    if name.startswith("/"):
        return False
    normalized = Path(name)
    for part in normalized.parts:
        if part == "..":
            return False
    return True


def _extract_archive(archive_path: str, destination: Path) -> None:
    lower = archive_path.lower()
    if lower.endswith(".zip"):
        with zipfile.ZipFile(archive_path, "r") as archive:
            destination_root = destination.resolve()
            for info in archive.infolist():
                if not _is_safe_member(info.filename):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid filename in archive: {info.filename}",
                    )
                if stat.S_ISLNK(info.external_attr >> 16):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Symlink entries are not allowed: {info.filename}",
                    )
                target = (destination / info.filename).resolve()
                if not str(target).startswith(str(destination_root)):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid filename in archive: {info.filename}",
                    )
                if info.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as source, open(target, "wb") as dest_file:
                    shutil.copyfileobj(source, dest_file)
        return

    if lower.endswith((".tar.gz", ".tgz", ".tar")):
        if lower.endswith((".tar.gz", ".tgz")):
            mode = "r:gz"
        else:
            mode = "r:"
        with tarfile.open(archive_path, mode) as archive:
            destination_root = destination.resolve()
            for member in archive.getmembers():
                if not _is_safe_member(member.name):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid filename in archive: {member.name}",
                    )
                if member.issym() or member.islnk():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Symlink entries are not allowed: {member.name}",
                    )
                target = (destination / member.name).resolve()
                if not str(target).startswith(str(destination_root)):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid filename in archive: {member.name}",
                    )
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                source = archive.extractfile(member)
                if source is None:
                    continue
                with source, open(target, "wb") as dest_file:
                    shutil.copyfileobj(source, dest_file)
        return

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported template archive format.")


@contextmanager
def _template_workspace(files_ref: str) -> Iterator[str]:
    with tempfile.TemporaryDirectory() as tmpdir:
        archive_path = storage_service.download_template_archive(files_ref, destination_dir=tmpdir)
        extracted_dir = Path(tmpdir) / "uploaded-template"
        extracted_dir.mkdir(parents=True, exist_ok=True)
        _extract_archive(archive_path, extracted_dir)
        yield str(extracted_dir)


def _ensure_text(value: str | None, fallback: str) -> str:
    if value is None or not str(value).strip():
        return fallback
    return str(value)


def _parse_trivy_results(data: dict) -> list[dict[str, str | None]]:
    findings: list[dict[str, str | None]] = []
    results = data.get("Results") or data.get("results") or []
    for result in results:
        for misconfig in result.get("Misconfigurations") or result.get("misconfigurations") or []:
            rule_id = (
                misconfig.get("ID")
                or misconfig.get("AVDID")
                or misconfig.get("UID")
                or misconfig.get("id")
                or "unknown"
            )
            severity = _normalize_severity(misconfig.get("Severity") or misconfig.get("severity"))
            resource = (
                (misconfig.get("CauseMetadata") or {}).get("Resource")
                or misconfig.get("Resource")
                or misconfig.get("resource")
                or result.get("Target")
                or result.get("target")
                or "unknown"
            )
            evidence = (
                misconfig.get("Description")
                or misconfig.get("description")
                or misconfig.get("Message")
                or misconfig.get("message")
                or misconfig.get("Title")
                or misconfig.get("title")
            )
            recommendation = (
                misconfig.get("Resolution")
                or misconfig.get("resolution")
                or misconfig.get("Recommendation")
                or misconfig.get("recommendation")
            )
            findings.append(
                {
                    "rule_id": _ensure_text(rule_id, "unknown"),
                    "severity": severity,
                    "resource": _ensure_text(resource, "unknown"),
                    "evidence": evidence,
                    "recommendation": recommendation,
                }
            )
    return findings


def _parse_checkov_results(data: dict) -> list[dict[str, str | None]]:
    findings: list[dict[str, str | None]] = []
    results = data.get("results") or {}
    failed_checks = results.get("failed_checks") or []
    for check in failed_checks:
        rule_id = check.get("check_id") or check.get("checkId") or "unknown"
        severity = _normalize_severity(check.get("severity"))
        resource = check.get("resource") or check.get("file_path") or "unknown"
        evidence = check.get("description") or check.get("check_name")
        guideline = check.get("guideline")
        if isinstance(guideline, list):
            recommendation = " ".join([str(item) for item in guideline if item])
        else:
            recommendation = guideline
        findings.append(
            {
                "rule_id": _ensure_text(rule_id, "unknown"),
                "severity": severity,
                "resource": _ensure_text(resource, "unknown"),
                "evidence": evidence,
                "recommendation": recommendation,
            }
        )
    return findings


def _parse_conftest_results(data: list[dict] | dict) -> list[dict[str, str | None]]:
    findings: list[dict[str, str | None]] = []
    if isinstance(data, dict):
        results = data.get("results") or []
    else:
        results = data
    for result in results:
        filename = result.get("filename") or result.get("file") or "unknown"
        failures = result.get("failures") or []
        for failure in failures:
            metadata = failure.get("metadata") or {}
            rule_id = metadata.get("id") or metadata.get("rule_id") or "opa-policy"
            severity = _normalize_severity(metadata.get("severity"))
            resource = metadata.get("resource") or filename
            evidence = failure.get("msg") or failure.get("message")
            recommendation = metadata.get("recommendation")
            findings.append(
                {
                    "rule_id": _ensure_text(rule_id, "opa-policy"),
                    "severity": severity,
                    "resource": _ensure_text(resource, "unknown"),
                    "evidence": evidence,
                    "recommendation": recommendation,
                }
            )
    return findings


def run_trivy_scan(path: str) -> dict[str, list[dict[str, str | None]]]:
    resolved_path = str(Path(path).resolve())
    if not Path(resolved_path).is_dir():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Template path is not a directory.")
    with tempfile.NamedTemporaryFile(delete=False, prefix="trivy-report-", suffix=".json") as handle:
        output_path = handle.name
    try:
        try:
            result = subprocess.run(
                ["trivy", "config", "--format", "json", "--output", output_path, resolved_path],
                capture_output=True,
                text=True,
                check=False,
                timeout=SCAN_TIMEOUT_SECONDS,
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Trivy is not installed.") from exc
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="Trivy scan timed out."
        ) from exc
    try:
        if result.returncode != 0:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Trivy scan failed.")

        if not os.path.exists(output_path):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY, detail="Trivy did not produce an output report."
            )

        try:
            with open(output_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Invalid Trivy JSON output.") from exc

        return {"findings": _parse_trivy_results(data)}
    finally:
        try:
            os.unlink(output_path)
        except OSError:
            pass


def run_checkov_scan(path: str) -> dict[str, list[dict[str, str | None]]]:
    resolved_path = str(Path(path).resolve())
    if not Path(resolved_path).is_dir():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Template path is not a directory.")
    try:
        try:
            result = subprocess.run(
                ["checkov", "-d", resolved_path, "-o", "json"],
                capture_output=True,
                text=True,
                check=False,
                timeout=SCAN_TIMEOUT_SECONDS,
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Checkov is not installed.") from exc
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="Checkov scan timed out."
        ) from exc
    # Checkov uses exit code 1 when policy violations are found, so treat 0 and 1 as successful runs.
    if result.returncode not in {0, 1}:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Checkov scan failed.")

    if not result.stdout.strip():
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Checkov did not return JSON output.")

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Invalid Checkov JSON output.") from exc

    return {"findings": _parse_checkov_results(data)}


def run_conftest_scan(path: str) -> dict[str, list[dict[str, str | None]]]:
    resolved_path = str(Path(path).resolve())
    if not Path(resolved_path).is_dir():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Template path is not a directory.")
    if not POLICY_DIR.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Policy directory is missing.",
        )
    try:
        try:
            result = subprocess.run(
                [
                    "conftest",
                    "test",
                    resolved_path,
                    "--policy",
                    str(POLICY_DIR),
                    "--output",
                    "json",
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=SCAN_TIMEOUT_SECONDS,
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Conftest is not installed.") from exc
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="Conftest scan timed out."
        ) from exc

    if result.returncode not in {0, 1}:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Conftest scan failed.")

    if not result.stdout.strip():
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Conftest did not return JSON output.")

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Invalid Conftest JSON output.") from exc

    return {"findings": _parse_conftest_results(data)}


def scan_template_with_trivy(files_ref: str) -> list[dict[str, str | None]]:
    with _template_workspace(files_ref) as path:
        return run_trivy_scan(path)["findings"]


def scan_template_with_checkov(files_ref: str) -> list[dict[str, str | None]]:
    with _template_workspace(files_ref) as path:
        return run_checkov_scan(path)["findings"]


def scan_template_with_policies(files_ref: str) -> list[dict[str, str | None]]:
    with _template_workspace(files_ref) as path:
        return run_conftest_scan(path)["findings"]
