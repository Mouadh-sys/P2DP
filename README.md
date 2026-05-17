# P2DP

Predictive DevSecOps Deployment and Protection.

## Kick start

This repository is now initialized with the project security requirements and scope document:

- [`docs/cahier-des-charges.md`](docs/cahier-des-charges.md)

## MVP layers

1. **Infrastructure Deployment Engine** (upload, validation, simulation, GitOps deployment)
2. **Misconfiguration Detection** (Trivy, Checkov, OPA/Conftest)
3. **Risk Forecasting** (heuristic score in MVP, ML extension)
4. **Threat Detection** (runtime monitoring, Falco, logs/events correlation)

## Target architecture (high level)

- Frontend: React + TypeScript
- Backend: FastAPI + Celery + Redis + PostgreSQL
- Security/Scan: Trivy, Checkov, OPA/Conftest
- GitOps: Argo CD
- Observability: OpenTelemetry + Jaeger + Prometheus + Loki + Grafana

For full requirements, acceptance criteria, and detailed functional scope, refer to the cahier des charges.
