# P2DP

**Predictive DevSecOps Deployment and Protection** — upload IaC templates, run pre/post-deployment security scans, score risk, and push manifests through GitOps.

## Project structure

```text
backend/         FastAPI API, Celery workers, scanning, risk, GitOps services
frontend/        React + TypeScript dashboard (MUI, Tailwind, Vite)
gitops-repo/     Desired-state manifests for Argo CD sync
infra/           Docker Compose stack (Postgres, Redis, MinIO, API, workers, UI)
samples/         Vulnerable and secure IaC/Kubernetes sample scenarios
docs/            Architecture, API reference, demo, and reporting documentation
```

## Quick start (Docker Compose)

Recommended for running the full stack locally.

```bash
cd infra
cp .env.example .env   # optional — defaults work for local dev
docker compose up --build
```

| Service    | URL |
|------------|-----|
| Dashboard  | http://localhost:5173 |
| API        | http://localhost:8000 |
| API health | http://localhost:8000/health |
| MinIO      | http://localhost:9001 (console) |
| Jaeger UI  | http://localhost:16686 |

Tracing: the API and Celery worker send OTLP traces to the collector (`OTEL_EXPORTER_OTLP_ENDPOINT`, default `http://otel-collector:4317`). After deploy, the dashboard shows the trace ID with a link to Jaeger.

## Dev login

In `ENVIRONMENT=dev`, the API seeds these users on startup:

| Email | Password | Role |
|-------|----------|------|
| `admin@p2dp.local` | `admin123` | Admin |
| `devops@p2dp.local` | `devops123` | DevOps |
| `security@p2dp.local` | `security123` | Security viewer |

Sign in at http://localhost:5173/login — the UI stores a JWT and calls the backend API.

## Frontend

Stack: **React 18**, **TypeScript**, **Vite**, **MUI**, **Tailwind CSS**, **React Router**.

```bash
cd frontend
cp .env.example .env    # set VITE_API_BASE_URL / VITE_JAEGER_UI_URL if needed
npm install
npm run dev             # http://localhost:5173
```

Build for production:

```bash
npm run build
npm run preview
```

### Main routes

| Route | Description |
|-------|-------------|
| `/` | Redirects to dashboard (authenticated) |
| `/login` | Sign in |
| `/dashboard` | Deployment control center |
| `/projects` | List and manage projects |
| `/projects/:id/environments` | Create environment, upload template, scan, deploy |
| `/projects/:id/environments/:envId/findings` | Security findings |
| `/projects/:id/environments/:envId/risk` | Risk assessment |
| `/environment` | Deployment overview across projects |
| `/upload`, `/threats`, `/traces`, `/reports`, `/settings` | Additional dashboard views |

The browser talks to the API via `VITE_API_BASE_URL` (default `http://localhost:8000`). In dev, the API enables CORS for `localhost:5173`.

## Backend

```bash
cd backend
python -m venv .venv

# Linux / macOS
source .venv/bin/activate

# Windows (PowerShell)
# .venv\Scripts\Activate.ps1

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Requires **PostgreSQL**, **Redis**, and **MinIO** (or use Docker Compose for dependencies).

Run Celery workers separately when testing async scans and deployments:

```bash
celery -A app.workers.celery_app.celery_app worker --loglevel=info
```

### API surface (summary)

- **Auth** — `POST /api/auth/token`, `POST /api/auth/register`
- **Projects** — CRUD, list/create environments per project
- **Environments** — upload templates, deploy, post-deployment scan, risk assessments
- **Template versions** — pre-deployment scan trigger and status
- **Findings** — list findings per environment (filters: severity, engine, phase)

See [docs/api.md](docs/api.md) for details.

## Configuration

Copy [infra/.env.example](infra/.env.example) to `infra/.env` and adjust as needed:

- `VITE_API_BASE_URL` — must be reachable from the **browser** (not the Docker internal hostname)
- `SECRET_KEY` — change in production
- `GITOPS_REMOTE_URL`, `ARGOCD_*`, `KUBECTL_CONTEXT` — optional GitOps/Kubernetes integration

## Documentation

- [Architecture](docs/architecture.md)
- [API reference](docs/api.md)
- [Cahier des charges](docs/cahier-des-charges.md)

## Development notes

- The MVP flow is: **create project → environment → upload archive → pre-deployment scan → risk → deploy → post-deployment scan**.
- Some dashboard pages (threats, traces, reports) are UI placeholders; core project/environment/findings/risk flows are wired to the API.
- Use `samples/` manifests to exercise scanners and policies during development.
