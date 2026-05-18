import client from "./client";
import type {
  DeploymentRun,
  Environment,
  Finding,
  PostDeploymentScanQueued,
  Project,
  ReportCreated,
  RiskAssessment,
  ScanQueued,
  ScanStatus,
  TemplateVersion,
} from "./types";

export const authApi = {
  login: (email: string, password: string) => {
    const form = new URLSearchParams();
    form.append("username", email);
    form.append("password", password);
    return client.post<{ access_token: string }>("/api/auth/token", form, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
  },
};

export const projectsApi = {
  list: () => client.get<Project[]>("/api/projects"),
  create: (name: string) => client.post<Project>("/api/projects", { name }),
  get: (projectId: string) => client.get<Project>(`/api/projects/${projectId}`),
  delete: (projectId: string) => client.delete(`/api/projects/${projectId}`),
  listEnvironments: (projectId: string) =>
    client.get<Environment[]>(`/api/projects/${projectId}/environments`),
  createEnvironment: (projectId: string, body: { target: string; status: string }) =>
    client.post<Environment>(`/api/projects/${projectId}/environments`, body),
};

export const environmentsApi = {
  get: (environmentId: string) => client.get<Environment>(`/api/environments/${environmentId}`),
  uploadTemplate: (environmentId: string, file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return client.post<TemplateVersion>(`/api/environments/${environmentId}/upload`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
  deploy: (environmentId: string) =>
    client.post<DeploymentRun>(`/api/environments/${environmentId}/deploy`),
  latestDeployment: (environmentId: string) =>
    client.get<DeploymentRun>(`/api/environments/${environmentId}/deployments/latest`),
  latestRisk: (environmentId: string) =>
    client.get<RiskAssessment>(`/api/environments/${environmentId}/risk-assessments/latest`),
  computeRisk: (environmentId: string) =>
    client.post<RiskAssessment>(`/api/environments/${environmentId}/risk-assessments`),
  postDeploymentScan: (environmentId: string) =>
    client.post<PostDeploymentScanQueued>(`/api/environments/${environmentId}/scan/post-deployment`),
  createReport: (environmentId: string) =>
    client.post<ReportCreated>(`/api/environments/${environmentId}/reports`),
};

export const findingsApi = {
  list: (
    environmentId: string,
    params?: { severity?: string; engine?: string; phase?: string }
  ) => client.get<Finding[]>(`/api/findings/environments/${environmentId}`, { params }),
};

export const templateVersionsApi = {
  validate: (templateVersionId: string) =>
    client.post<{ task_id: string }>(`/api/template-versions/${templateVersionId}/validate`),
  scan: (templateVersionId: string) =>
    client.post<ScanQueued>(`/api/template-versions/${templateVersionId}/scan`),
  scanStatus: (templateVersionId: string, scanId: string) =>
    client.get<ScanStatus>(`/api/template-versions/${templateVersionId}/scan/${scanId}`),
};

export const reportsApi = {
  download: (reportId: string) =>
    client.get(`/api/reports/${reportId}/download`, { responseType: "blob" }),
};
