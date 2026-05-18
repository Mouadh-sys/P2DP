import {
  Alert,
  Button,
  Card,
  CardContent,
  CircularProgress,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { FileDown } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { environmentsApi, projectsApi, reportsApi } from "../api/endpoints";
import type { Environment, Project, ReportCreated } from "../api/types";

export default function ReportsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [environments, setEnvironments] = useState<Environment[]>([]);
  const [projectId, setProjectId] = useState("");
  const [environmentId, setEnvironmentId] = useState("");
  const [lastReport, setLastReport] = useState<ReportCreated | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const loadProjects = useCallback(async () => {
    setLoading(true);
    try {
      const response = await projectsApi.list();
      setProjects(response.data);
      setError("");
    } catch {
      setError("Failed to load projects.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  useEffect(() => {
    if (!projectId) {
      setEnvironments([]);
      setEnvironmentId("");
      return;
    }
    projectsApi
      .listEnvironments(projectId)
      .then((r) => {
        setEnvironments(r.data);
        setEnvironmentId(r.data[0]?.id ?? "");
      })
      .catch(() => setError("Failed to load environments."));
  }, [projectId]);

  const handleGenerate = async () => {
    if (!environmentId) {
      setError("Select an environment first.");
      return;
    }
    setGenerating(true);
    setError("");
    setMessage("");
    try {
      const response = await environmentsApi.createReport(environmentId);
      setLastReport(response.data);
      setMessage("HTML report generated and stored in MinIO.");
    } catch {
      setError("Failed to generate report.");
    } finally {
      setGenerating(false);
    }
  };

  const handleDownload = async () => {
    if (!lastReport) return;
    setDownloading(true);
    try {
      const response = await reportsApi.download(lastReport.report_id);
      const blob = new Blob([response.data], { type: "text/html" });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `p2dp-report-${lastReport.report_id}.html`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch {
      setError("Failed to download report.");
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="space-y-6">
      <Typography variant="h4" className="font-bold text-slate-900 tracking-tight">
        Reports
      </Typography>
      <Typography variant="body2" className="text-slate-500">
        Generate an HTML security posture report (deployment, risk, findings, threats, trace).
      </Typography>

      {error ? <Alert severity="error">{error}</Alert> : null}
      {message ? <Alert severity="success">{message}</Alert> : null}

      <Card className="bg-white border-slate-200 shadow-sm">
        <CardContent>
          {loading ? (
            <CircularProgress size={28} />
          ) : (
            <Stack spacing={2} sx={{ maxWidth: 480 }}>
              <TextField
                select
                label="Project"
                value={projectId}
                onChange={(e) => setProjectId(e.target.value)}
                size="small"
                fullWidth
              >
                <MenuItem value="">Select project</MenuItem>
                {projects.map((p) => (
                  <MenuItem key={p.id} value={p.id}>
                    {p.name}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                select
                label="Environment"
                value={environmentId}
                onChange={(e) => setEnvironmentId(e.target.value)}
                size="small"
                fullWidth
                disabled={!projectId || environments.length === 0}
              >
                <MenuItem value="">Select environment</MenuItem>
                {environments.map((env) => (
                  <MenuItem key={env.id} value={env.id}>
                    {env.target} ({env.status})
                  </MenuItem>
                ))}
              </TextField>
              <Button
                variant="contained"
                onClick={handleGenerate}
                disabled={!environmentId || generating}
              >
                {generating ? "Generating…" : "Generate HTML report"}
              </Button>
              {lastReport ? (
                <Button
                  variant="outlined"
                  startIcon={<FileDown size={16} />}
                  onClick={handleDownload}
                  disabled={downloading}
                >
                  {downloading ? "Downloading…" : "Download report"}
                </Button>
              ) : null}
            </Stack>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
