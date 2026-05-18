"""Simulated log-based threat detection for Layer 4 MVP (no Falco required locally)."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import NamedTuple

from app.core.config import settings

ISO_TS = re.compile(r"^(?P<ts>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?)\s")
SSH_FAIL = re.compile(r"Failed password for .+ from (?P<ip>[\d.]+)\b")
INGRESS = re.compile(r"client=(?P<ip>[\d.]+).*target_port=(?P<port>\d+)")
CONTAINER_CTX = re.compile(r"(?:\bpod=|\bnamespace=|\bcontainer=)", re.I)
SUSPICIOUS_TOOL = re.compile(r"\b(?:curl|wget|nc|bash)\b", re.I)

WINDOW = timedelta(minutes=1)
SSH_FAIL_THRESHOLD = 5  # alert when strictly more than 5 attempts in window
PORT_SCAN_THRESHOLD = 10  # alert when strictly more than 10 distinct ports in window


class _TsEvent(NamedTuple):
    ts: datetime
    line: str


def _parse_line_ts(line: str) -> tuple[datetime | None, str]:
    m = ISO_TS.match(line.strip())
    if not m:
        return None, line
    raw = m.group("ts").replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt, line
    except ValueError:
        return None, line


def _read_log_lines(path: Path) -> list[str]:
    if not path.is_file():
        return []
    return path.read_text(encoding="utf-8").splitlines()


def _max_ssh_fails_in_window(events: list[_TsEvent]) -> int:
    if not events:
        return 0
    times = [e.ts for e in events]
    best = 0
    for i, start in enumerate(times):
        count = 0
        for t in times[i:]:
            if t - start > WINDOW:
                break
            count += 1
        best = max(best, count)
    return best


def _max_unique_ports_in_window(events: list[tuple[datetime, int]]) -> int:
    if not events:
        return 0
    events_sorted = sorted(events, key=lambda x: x[0])
    best = 0
    for i, (start, _) in enumerate(events_sorted):
        ports: set[int] = set()
        for t, port in events_sorted[i:]:
            if t - start > WINDOW:
                break
            ports.add(port)
        best = max(best, len(ports))
    return best


def detect_ssh_bruteforce(lines: list[str]) -> list[dict[str, str | None]]:
    """Alert if the same source IP has more than SSH_FAIL_THRESHOLD failures within WINDOW."""
    by_ip: dict[str, list[_TsEvent]] = {}
    for line in lines:
        if "Failed password" not in line:
            continue
        m_ssh = SSH_FAIL.search(line)
        if not m_ssh:
            continue
        ts, _ = _parse_line_ts(line)
        if ts is None:
            continue
        ip = m_ssh.group("ip")
        by_ip.setdefault(ip, []).append(_TsEvent(ts, line.strip()))

    out: list[dict[str, str | None]] = []
    for ip, events in by_ip.items():
        events.sort(key=lambda e: e.ts)
        peak = _max_ssh_fails_in_window(events)
        if peak > SSH_FAIL_THRESHOLD:
            out.append(
                {
                    "rule_id": "L4-SIM-SSH-BRUTEFORCE",
                    "severity": "HIGH",
                    "resource": f"ssh/client:{ip}",
                    "evidence": f"{peak} failed password attempts from {ip} within 1 minute (threshold >{SSH_FAIL_THRESHOLD}).",
                    "recommendation": "Block the source IP, enforce key-only auth, and enable rate limiting or fail2ban.",
                }
            )
    return out


def detect_port_scan(lines: list[str]) -> list[dict[str, str | None]]:
    """Alert if the same client hits more than PORT_SCAN_THRESHOLD distinct ports within WINDOW."""
    by_ip: dict[str, list[tuple[datetime, int]]] = {}
    for line in lines:
        m = INGRESS.search(line)
        if not m:
            continue
        ts, _ = _parse_line_ts(line)
        if ts is None:
            continue
        ip = m.group("ip")
        port = int(m.group("port"))
        by_ip.setdefault(ip, []).append((ts, port))

    out: list[dict[str, str | None]] = []
    for ip, events in by_ip.items():
        peak_ports = _max_unique_ports_in_window(events)
        if peak_ports > PORT_SCAN_THRESHOLD:
            out.append(
                {
                    "rule_id": "L4-SIM-PORT-SCAN",
                    "severity": "HIGH",
                    "resource": f"ingress/client:{ip}",
                    "evidence": f"{peak_ports} distinct target ports from {ip} within 1 minute (threshold >{PORT_SCAN_THRESHOLD}).",
                    "recommendation": "Investigate the client, tighten ingress/WAF rules, and alert SOC.",
                }
            )
    return out


def detect_suspicious_container_commands(lines: list[str]) -> list[dict[str, str | None]]:
    """Alert on unexpected shell tooling when line clearly references a workload (pod/namespace/container)."""
    out: list[dict[str, str | None]] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        ts, _ = _parse_line_ts(stripped)
        if ts is None:
            continue
        if not CONTAINER_CTX.search(stripped):
            continue
        tool_m = SUSPICIOUS_TOOL.search(stripped)
        if not tool_m:
            continue
        tool = tool_m.group(0).lower()
        out.append(
            {
                "rule_id": "L4-SIM-SUSPICIOUS-EXEC",
                "severity": "MEDIUM",
                "resource": "workload/exec",
                "evidence": stripped[:2048],
                "recommendation": f"Review why `{tool}` ran inside the container; restrict images and runtime policies.",
            }
        )
    return out


def analyze_simulated_logs_for_threats(logs_dir: Path | None = None) -> list[dict[str, str | None]]:
    """Parse sample auth, ingress, and app logs and return Finding-shaped payloads (layer L4 at insert time)."""
    base = logs_dir if logs_dir is not None else Path(settings.resolved_simulated_logs_path)
    if not base.is_dir():
        return []

    payloads: list[dict[str, str | None]] = []
    payloads.extend(detect_ssh_bruteforce(_read_log_lines(base / "auth.log")))
    payloads.extend(detect_port_scan(_read_log_lines(base / "ingress.log")))
    payloads.extend(detect_suspicious_container_commands(_read_log_lines(base / "app.log")))
    return payloads
