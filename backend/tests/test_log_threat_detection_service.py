from pathlib import Path

from app.services.log_threat_detection_service import (
    analyze_simulated_logs_for_threats,
    detect_port_scan,
    detect_ssh_bruteforce,
    detect_suspicious_container_commands,
)

REPO_SAMPLES_LOGS = Path(__file__).resolve().parents[2] / "samples" / "logs"


def test_detect_ssh_bruteforce_threshold(tmp_path: Path) -> None:
    log = tmp_path / "auth.log"
    log.write_text(
        "\n".join(
            [
                "2024-01-01T12:00:00Z sshd: Failed password for root from 10.0.0.1 port 22 ssh2",
                "2024-01-01T12:00:10Z sshd: Failed password for root from 10.0.0.1 port 22 ssh2",
                "2024-01-01T12:00:20Z sshd: Failed password for root from 10.0.0.1 port 22 ssh2",
                "2024-01-01T12:00:30Z sshd: Failed password for root from 10.0.0.1 port 22 ssh2",
                "2024-01-01T12:00:40Z sshd: Failed password for root from 10.0.0.1 port 22 ssh2",
                "2024-01-01T12:00:50Z sshd: Failed password for root from 10.0.0.1 port 22 ssh2",
            ]
        ),
        encoding="utf-8",
    )
    lines = log.read_text(encoding="utf-8").splitlines()
    hits = detect_ssh_bruteforce(lines)
    assert len(hits) == 1
    assert hits[0]["rule_id"] == "L4-SIM-SSH-BRUTEFORCE"
    assert "10.0.0.1" in (hits[0]["resource"] or "")


def test_detect_port_scan_threshold(tmp_path: Path) -> None:
    base_ts = "2024-01-01T12:00:{sec:02d}Z"
    rows = [f'{base_ts.format(sec=i)} ingress/tcp client=10.0.0.2 target_port={8000 + i} action=connect' for i in range(12)]
    lines = "\n".join(rows)
    hits = detect_port_scan(lines.splitlines())
    assert len(hits) == 1
    assert hits[0]["rule_id"] == "L4-SIM-PORT-SCAN"


def test_detect_suspicious_exec_requires_container_context(tmp_path: Path) -> None:
    lines = [
        "2024-01-01T12:00:00Z argv=curl http://x",
        "2024-01-01T12:00:01Z pod=p1 container=c1 argv=curl http://x",
    ]
    hits = detect_suspicious_container_commands(lines)
    assert len(hits) == 1


def test_repo_sample_logs_produce_l4_payloads() -> None:
    if not REPO_SAMPLES_LOGS.is_dir():
        return
    payloads = analyze_simulated_logs_for_threats(REPO_SAMPLES_LOGS)
    rule_ids = {p["rule_id"] for p in payloads}
    assert "L4-SIM-SSH-BRUTEFORCE" in rule_ids
    assert "L4-SIM-PORT-SCAN" in rule_ids
    assert "L4-SIM-SUSPICIOUS-EXEC" in rule_ids
    assert len([p for p in payloads if p["rule_id"] == "L4-SIM-SUSPICIOUS-EXEC"]) >= 3
