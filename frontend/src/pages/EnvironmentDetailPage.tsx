import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  MenuItem,
  Grid2,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { Link as RouterLink, useNavigate, useParams } from "react-router-dom";

import client from "../api/client";

type Environment = {
  id: string;
  project_id: string;
  target: "dev" | "local-k8s";
  status: string;
};

export default function EnvironmentDetailPage() {
  const navigate = useNavigate();
  const { projectId } = useParams();
  const [target, setTarget] = useState<"dev" | "local-k8s">("local-k8s");
  const [status, setStatus] = useState<"pending" | "active" | "failed">("pending");
  const [environments, setEnvironments] = useState<Environment[]>([]);
  const [fileByEnv, setFileByEnv] = useState<Record<string, File | null>>({});
  const [templateVersionByEnv, setTemplateVersionByEnv] = useState<Record<string, string>>({});
  const [scanningEnvId, setScanningEnvId] = useState<string | null>(null);
  const [deployingEnvId, setDeployingEnvId] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const loadEnvironments = useCallback(async () => {
    if (!projectId) return;
    try {
      const listResponse = await client.get<Environment[]>(`/api/projects/${projectId}/environments`);
      if (listResponse.data.length === 0) {
        setEnvironments([]);
        setError("");
        return;
      }

      const details = await Promise.all(
        listResponse.data.map((env) => client.get<Environment>(`/api/environments/${env.id}`).then((r) => r.data))
      );
      setEnvironments(details);
      setError("");
    } catch {
      setError("Failed to load environments.");
    }
  }, [projectId]);

  useEffect(() => {
    loadEnvironments();
  }, [loadEnvironments]);

  const handleCreateEnvironment = async (event: FormEvent) => {
    event.preventDefault();
    if (!projectId) return;
    try {
      await client.post(`/api/projects/${projectId}/environments`, { target, status });
      setMessage("Environment created successfully.");
      setError("");
      await loadEnvironments();
    } catch {
      setError("Failed to create environment.");
    }
  };

  const handleUpload = async (environmentId: string) => {
    const file = fileByEnv[environmentId];
    if (!file) {
      setError("Please choose a file first.");
      return;
    }
    const formData = new FormData();
    formData.append("file", file);
    try {
      const response = await client.post(`/api/environments/${environmentId}/upload`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setTemplateVersionByEnv((prev) => ({
        ...prev,
        [environmentId]: response.data.id,
      }));
      setMessage(`Template uploaded. Version ID: ${response.data.id}`);
      setError("");
    } catch {
      setError("Failed to upload template archive.");
    }
  };

  const handleDeploy = async (environmentId: string) => {
    if (!templateVersionByEnv[environmentId]) {
      setError("Upload a template archive before deploying.");
      return;
    }
    setDeployingEnvId(environmentId);
    try {
      const response = await client.post<{
        deployment_id: string;
        status: string;
        git_commit: string | null;
        trace_id: string | null;
      }>(`/api/environments/${environmentId}/deploy`);
      setMessage(
        `Deployment ${response.data.deployment_id} started (${response.data.status}).` +
          (response.data.trace_id ? ` Trace: ${response.data.trace_id}` : "")
      );
      setError("");
    } catch {
      setError("Failed to start deployment.");
    } finally {
      setDeployingEnvId(null);
    }
  };

  const handleUnifiedScan = async (environmentId: string) => {
    const templateVersionId = templateVersionByEnv[environmentId];
    if (!templateVersionId) {
      setError("Upload a template archive before running a scan.");
      return;
    }
    if (!projectId) return;

    setScanningEnvId(environmentId);
    try {
      const response = await client.post<{ scan_id: string; status: string }>(
        `/api/template-versions/${templateVersionId}/scan`
      );
      navigate(
        `/projects/${projectId}/environments/${environmentId}/findings?templateVersionId=${templateVersionId}&scanId=${response.data.scan_id}`
      );
    } catch {
      setError("Failed to start pre-deployment scan.");
    } finally {
      setScanningEnvId(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <Typography variant="h4" className="font-bold text-slate-900 tracking-tight">
          Environments
        </Typography>
        <Button variant="outlined" onClick={() => navigate("/projects")}>
          Back to projects
        </Button>
      </div>

      {message ? <Alert severity="success">{message}</Alert> : null}
      {error ? <Alert severity="error">{error}</Alert> : null}

      {environments.length === 0 ? (
        <Box component="form" onSubmit={handleCreateEnvironment}>
          <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
            <TextField
              select
              label="Target"
              value={target}
              onChange={(e) => setTarget(e.target.value as "dev" | "local-k8s")}
              required
              sx={{ minWidth: 180 }}
            >
              <MenuItem value="dev">dev</MenuItem>
              <MenuItem value="local-k8s">local-k8s</MenuItem>
            </TextField>
            <TextField
              select
              label="Status"
              value={status}
              onChange={(e) => setStatus(e.target.value as "pending" | "active" | "failed")}
              required
              sx={{ minWidth: 180 }}
            >
              <MenuItem value="pending">pending</MenuItem>
              <MenuItem value="active">active</MenuItem>
              <MenuItem value="failed">failed</MenuItem>
            </TextField>
            <Button type="submit" variant="contained">
              Create Environment
            </Button>
          </Stack>
        </Box>
      ) : (
        <Typography variant="body2" color="text.secondary">
          This project already has its single MVP environment.
        </Typography>
      )}

      <Grid2 container spacing={2}>
        {environments.map((environment) => (
          <Grid2 size={{ xs: 12, md: 6 }} key={environment.id}>
            <Card className="bg-white border-slate-200 shadow-sm">
              <CardContent>
                <Typography variant="h6" className="text-slate-800 font-bold mb-1">
                  {environment.target}
                </Typography>
                <Typography variant="body2" className="text-slate-500 mb-3 text-xs">
                  Status: {environment.status}
                </Typography>

                <Stack spacing={1}>
                  <Button variant="outlined" component="label">
                    Select archive file
                    <input
                      type="file"
                      hidden
                      onChange={(e) =>
                        setFileByEnv((prev) => ({
                          ...prev,
                          [environment.id]: e.target.files?.[0] ?? null,
                        }))
                      }
                    />
                  </Button>
                  <Button variant="contained" onClick={() => handleUpload(environment.id)}>
                    Upload Template
                  </Button>
                  <Button
                    variant="contained"
                    color="secondary"
                    disabled={!templateVersionByEnv[environment.id] || scanningEnvId === environment.id}
                    onClick={() => handleUnifiedScan(environment.id)}
                  >
                    {scanningEnvId === environment.id ? "Starting scan…" : "Run pre-deployment scan"}
                  </Button>
                  <Button
                    variant="outlined"
                    component={RouterLink}
                    to={`/projects/${projectId}/environments/${environment.id}/findings`}
                  >
                    View findings
                  </Button>
                  <Button
                    variant="outlined"
                    component={RouterLink}
                    to={`/projects/${projectId}/environments/${environment.id}/risk`}
                  >
                    Risk forecast
                  </Button>
                  <Button
                    variant="contained"
                    color="success"
                    disabled={!templateVersionByEnv[environment.id] || deployingEnvId === environment.id}
                    onClick={() => handleDeploy(environment.id)}
                  >
                    {deployingEnvId === environment.id ? "Deploying…" : "Deploy to GitOps"}
                  </Button>
                </Stack>
              </CardContent>
            </Card>
          </Grid2>
        ))}
      </Grid2>
    </div>
  );
}
