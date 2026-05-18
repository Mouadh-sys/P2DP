import {
  Alert,
  Card,
  Chip,
  CircularProgress,
  MenuItem,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import { useCallback, useEffect, useState } from "react";

import { findingsApi, projectsApi } from "../api/endpoints";
import type { Environment, Finding, Project } from "../api/types";

function severityColor(severity: string): "default" | "success" | "warning" | "error" {
  switch (severity.toUpperCase()) {
    case "CRITICAL":
    case "HIGH":
      return "error";
    case "MEDIUM":
      return "warning";
    case "LOW":
      return "success";
    default:
      return "default";
  }
}

export default function ThreatAlertsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [environments, setEnvironments] = useState<Environment[]>([]);
  const [projectId, setProjectId] = useState("");
  const [environmentId, setEnvironmentId] = useState("");
  const [alerts, setAlerts] = useState<Finding[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    projectsApi
      .list()
      .then((r) => setProjects(r.data))
      .catch(() => setError("Failed to load projects."))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!projectId) {
      setEnvironments([]);
      setEnvironmentId("");
      return;
    }
    projectsApi.listEnvironments(projectId).then((r) => {
      setEnvironments(r.data);
      setEnvironmentId(r.data[0]?.id ?? "");
    });
  }, [projectId]);

  const loadAlerts = useCallback(async () => {
    if (!environmentId) {
      setAlerts([]);
      return;
    }
    try {
      const response = await findingsApi.list(environmentId, {
        engine: "simulated_logs",
        phase: "POST_DEPLOYMENT",
      });
      setAlerts(response.data);
      setError("");
    } catch {
      setError("Failed to load threat alerts.");
    }
  }, [environmentId]);

  useEffect(() => {
    loadAlerts();
  }, [loadAlerts]);

  return (
    <div className="space-y-6">
      <Typography variant="h4" className="font-bold text-slate-900 tracking-tight">
        Threat Alerts
      </Typography>
      <Typography variant="body2" className="text-slate-500">
        Layer 4 simulated log detections (SSH brute force, port scan, suspicious exec). Falco-backed{" "}
        <code>threat_alerts</code> rows appear in generated HTML reports when present.
      </Typography>

      {error ? <Alert severity="error">{error}</Alert> : null}

      <div className="flex flex-wrap gap-3">
        <TextField
          select
          label="Project"
          value={projectId}
          onChange={(e) => setProjectId(e.target.value)}
          size="small"
          sx={{ minWidth: 200 }}
        >
          <MenuItem value="">All projects</MenuItem>
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
          sx={{ minWidth: 200 }}
          disabled={!projectId}
        >
          <MenuItem value="">Select environment</MenuItem>
          {environments.map((env) => (
            <MenuItem key={env.id} value={env.id}>
              {env.target}
            </MenuItem>
          ))}
        </TextField>
      </div>

      <Card className="bg-white border-slate-200 shadow-sm">
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow className="bg-slate-50">
                <TableCell>Severity</TableCell>
                <TableCell>Rule</TableCell>
                <TableCell>Resource</TableCell>
                <TableCell>Evidence</TableCell>
                <TableCell>Recommendation</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={5} align="center">
                    <CircularProgress size={24} />
                  </TableCell>
                </TableRow>
              ) : !environmentId ? (
                <TableRow>
                  <TableCell colSpan={5} align="center">
                    Select a project and environment.
                  </TableCell>
                </TableRow>
              ) : alerts.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} align="center">
                    No simulated log alerts. Run a post-deployment scan after deploy.
                  </TableCell>
                </TableRow>
              ) : (
                alerts.map((alert) => (
                  <TableRow key={alert.id} hover>
                    <TableCell>
                      <Chip label={alert.severity} color={severityColor(alert.severity)} size="small" />
                    </TableCell>
                    <TableCell className="font-mono text-xs">{alert.rule_id}</TableCell>
                    <TableCell>{alert.resource}</TableCell>
                    <TableCell>{alert.evidence ?? "—"}</TableCell>
                    <TableCell>{alert.recommendation ?? "—"}</TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Card>
    </div>
  );
}
