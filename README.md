# P2DP

Predictive DevSecOps Deployment and Protection.

## Project structure

```text
backend/         FastAPI API, core services, workers, policies
frontend/        React + TypeScript UI scaffold
gitops-repo/     Desired-state manifests for Argo CD sync
infra/           Local infra setup, k8s/helm/argocd/otel/monitoring assets
samples/         Vulnerable and secure IaC/Kubernetes sample scenarios
docs/            Architecture, API, demo, and reporting documentation
```

## Backend quick start

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Frontend quick start

```bash
cd frontend
npm install
npm run dev
```

## Notes

- This is an initialized scaffold aligned with the P2DP architecture and stack from the cahier des charges.
- The implementation layers (deployment engine, scanning, risk, monitoring) are intentionally stubbed for iterative development.
