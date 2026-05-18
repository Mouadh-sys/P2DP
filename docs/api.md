# P2DP API

Base URL (local): `http://localhost:8000`

All protected routes require a JWT:

```http
Authorization: Bearer <access_token>
```

The dashboard uses **axios** (`frontend/src/api/client.ts`) with `VITE_API_BASE_URL` and attaches the token from `localStorage`.

---

## Authentication

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/auth/register` | Register user (JSON body: `email`, `password`, `role`) |
| `POST` | `/api/auth/token` | OAuth2 password flow (`username`=email, `password`) → `{ access_token }` |
| `POST` | `/api/auth/login` | JSON login (`email`, `password`) → `{ access_token }` |
| `GET` | `/api/auth/me` | Current user profile |

**Frontend:** `LoginPage` → `POST /api/auth/token` via `authApi.login()`.

---

## Projects

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/projects` | Create project `{ "name": "..." }` |
| `GET` | `/api/projects` | List projects for current user |
| `GET` | `/api/projects/{project_id}` | Get project |
| `DELETE` | `/api/projects/{project_id}` | Delete project |
| `POST` | `/api/projects/{project_id}/environments` | Create environment `{ "target", "status" }` |
| `GET` | `/api/projects/{project_id}/environments` | List environments |

**Frontend:** `ProjectsPage`, `EnvironmentPage`, `EnvironmentDetailPage`, `ReportsPage`, `ThreatAlertsPage`, `TracesPage`.

---

## Environments

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/environments/{environment_id}` | Get environment |
| `POST` | `/api/environments/{environment_id}/upload` | Upload template ZIP (`multipart/form-data`, field `file`) → `TemplateVersion` |
| `POST` | `/api/environments/{environment_id}/templates/upload` | Alias of upload |
| `POST` | `/api/environments/{environment_id}/deploy` | Start GitOps deployment → `DeploymentRun` (202) |
| `GET` | `/api/environments/{environment_id}/deployments/latest` | Latest deployment run |
| `POST` | `/api/environments/{environment_id}/risk-assessments` | Compute risk from L2 findings |
| `GET` | `/api/environments/{environment_id}/risk-assessments/latest` | Latest risk assessment |
| `POST` | `/api/environments/{environment_id}/scan/post-deployment` | Queue post-deployment scan (Celery) |
| `POST` | `/api/environments/{environment_id}/reports` | Generate HTML report, store in MinIO |

### Deployment run response

```json
{
  "deployment_id": "uuid",
  "env_id": "uuid",
  "status": "RUNNING",
  "git_commit": null,
  "trace_id": "32-char-hex",
  "logs_ref": null,
  "started_at": "2024-06-15T12:00:00Z",
  "finished_at": null
}
```

**Frontend:** `EnvironmentDetailPage` (upload, pre-scan, deploy, post-scan, trace/Jaeger link), `TracesPage` (latest deployments with `trace_id`).

### Post-deployment scan response

```json
{
  "status": "queued",
  "task_id": "celery-task-id",
  "env_id": "uuid"
}
```

### Report created response

```json
{
  "report_id": "uuid",
  "env_id": "uuid",
  "download_url": "/api/reports/{report_id}/download"
}
```

**Frontend:** `ReportsPage` → create + download via `reportsApi.download()`.

---

## Findings

| Method | Path | Query params | Description |
|--------|------|--------------|-------------|
| `GET` | `/api/findings/environments/{environment_id}` | `severity`, `engine`, `phase` | List findings (L2 + L4 layers) |

Engines: `trivy`, `checkov`, `policies`, `simulated_logs` (Layer 4 log detections).

Phases: `PRE_DEPLOYMENT`, `POST_DEPLOYMENT`.

**Frontend:** `FindingsPage`, `ThreatAlertsPage` (filters `engine=simulated_logs`, `phase=POST_DEPLOYMENT`).

---

## Template versions

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/template-versions/{template_version_id}/validate` | Queue validation (202) |
| `POST` | `/api/template-versions/{template_version_id}/scan` | Queue unified pre-deployment scan (202) |
| `GET` | `/api/template-versions/{template_version_id}/scan/{scan_id}` | Poll scan status |
| `POST` | `/api/template-versions/{template_version_id}/scan/trivy` | Sync Trivy scan |
| `POST` | `/api/template-versions/{template_version_id}/scan/checkov` | Sync Checkov scan |
| `POST` | `/api/template-versions/{template_version_id}/scan/policies` | Sync Conftest scan |

**Scan queued response:**

```json
{
  "scan_id": "uuid",
  "task_id": "celery-task-id",
  "status": "PENDING"
}
```

**Frontend:** `EnvironmentDetailPage` → `POST .../scan`; `FindingsPage` polls `GET .../scan/{scan_id}`.

---

## Reports

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/reports/{report_id}/download` | Download HTML report from MinIO |

Report HTML includes: project name, environment, deployment ID, git commit, deployment status, risk score, findings summary, top critical findings, threat alerts, L4 log alerts, recommendations, trace ID, timestamp.

---

## System

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | `{ "status": "ok" }` |

---

## Frontend route ↔ API map

| UI route | API usage |
|----------|-----------|
| `/login` | `POST /api/auth/token` |
| `/projects` | Projects CRUD + list environments |
| `/projects/:id/environments` | Environment CRUD, upload, deploy, scans, trace |
| `/projects/:id/environments/:envId/findings` | Findings list + scan poll |
| `/projects/:id/environments/:envId/risk` | Risk latest + compute |
| `/environment` | List all project/environment pairs |
| `/reports` | `POST .../reports`, `GET /api/reports/{id}/download` |
| `/threats` | Findings with `simulated_logs` engine |
| `/traces` | Latest deployment `trace_id` + Jaeger link |
| `/upload` | Redirects users to project environment upload |
| `/dashboard` | Mock data (not wired to API) |

---

## Environment variables (frontend)

| Variable | Default | Purpose |
|----------|---------|---------|
| `VITE_API_BASE_URL` | `http://localhost:8000` | Axios base URL |
| `VITE_JAEGER_UI_URL` | `http://localhost:16686` | Jaeger UI for trace links |

---

## Notes

- **Threat alerts table:** `threat_alerts` is populated for reports; there is no list endpoint yet. The UI shows Layer 4 **simulated log** findings as runtime threats.
- **MVP upload:** Only `.zip` archives; internal files must be `.tf`, `.yaml`, `.yml`, or `Dockerfile`.
- **Auth in tests:** Use `POST /api/auth/register` then `POST /api/auth/token` or `POST /api/auth/login`.
