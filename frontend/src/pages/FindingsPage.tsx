import {
  Alert,
  Button,
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
import { Download, Filter } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link as RouterLink, useParams, useSearchParams } from "react-router-dom";

import client from "../api/client";

type Finding = {
  id: string;
  env_id: string;
  layer: string;
  phase: string;
  engine: string;
  rule_id: string;
  severity: string;
  resource: string;
  evidence: string | null;
  recommendation: string | null;
};

type ScanStatus = {
  id: string;
  status: string;
  findings_count: number;
  error_message: string | null;
};

const SEVERITIES = ["", "LOW", "MEDIUM", "HIGH", "CRITICAL"] as const;
const ENGINES = ["", "trivy", "checkov", "policies"] as const;
const PHASES = ["", "PRE_DEPLOYMENT", "POST_DEPLOYMENT"] as const;

function severityColor(severity: string): "default" | "success" | "warning" | "error" {
  switch (severity) {
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

export default function FindingsPage() {
  const { projectId, environmentId } = useParams();
  const [searchParams] = useSearchParams();
  const templateVersionId = searchParams.get("templateVersionId");
  const scanId = searchParams.get("scanId");

  const [findings, setFindings] = useState<Finding[]>([]);
  const [severity, setSeverity] = useState("");
  const [engine, setEngine] = useState("");
  const [phase, setPhase] = useState("");
  const [scanStatus, setScanStatus] = useState<ScanStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadFindings = useCallback(async () => {
    if (!environmentId) return;
    try {
      const params: Record<string, string> = {};
      if (severity) params.severity = severity;
      if (engine) params.engine = engine;
      if (phase) params.phase = phase;
      const response = await client.get<Finding[]>(`/api/findings/environments/${environmentId}`, { params });
      setFindings(response.data);
      setError("");
    } catch {
      setError("Failed to load findings.");
    } finally {
      setLoading(false);
    }
  }, [environmentId, severity, engine, phase]);

  const pollScanStatus = useCallback(async () => {
    if (!templateVersionId || !scanId) return null;
    const response = await client.get<ScanStatus>(
      `/api/template-versions/${templateVersionId}/scan/${scanId}`
    );
    setScanStatus(response.data);
    return response.data.status;
  }, [templateVersionId, scanId]);

  useEffect(() => {
    loadFindings();
  }, [loadFindings]);

  useEffect(() => {
    if (!scanId || !templateVersionId) return;

    let active = true;
    const poll = async () => {
      const status = await pollScanStatus();
      if (!active) return;
      if (status === "SUCCESS" || status === "FAILED") {
        await loadFindings();
        return;
      }
      window.setTimeout(poll, 2000);
    };

    poll();
    return () => {
      active = false;
    };
  }, [scanId, templateVersionId, pollScanStatus, loadFindings]);

  const scanInProgress = scanStatus?.status === "PENDING" || scanStatus?.status === "RUNNING";

  if (!environmentId) {
    return (
      <Alert severity="info">
        Open a project environment to view findings.{" "}
        <Button component={RouterLink} to="/projects" size="small">
          Go to projects
        </Button>
      </Alert>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <Typography variant="h4" className="font-bold text-slate-900 tracking-tight">
            Security Findings
          </Typography>
          <Typography variant="body1" className="text-slate-500 mt-1 text-sm font-medium">
            Cross-layer misconfigurations and vulnerabilities
          </Typography>
        </div>
        <div className="flex flex-wrap gap-2">
          {projectId ? (
            <Button
              variant="outlined"
              component={RouterLink}
              to={`/projects/${projectId}/environments`}
            >
              Back to environment
            </Button>
          ) : null}
          {projectId && environmentId ? (
            <Button
              variant="outlined"
              component={RouterLink}
              to={`/projects/${projectId}/environments/${environmentId}/risk`}
            >
              Risk forecast
            </Button>
          ) : null}
        </div>
      </div>

      {error ? <Alert severity="error">{error}</Alert> : null}

      {scanStatus ? (
        <Alert
          severity={scanStatus.status === "FAILED" ? "error" : scanStatus.status === "SUCCESS" ? "success" : "info"}
          icon={scanInProgress ? <CircularProgress size={18} /> : undefined}
        >
          Scan status: {scanStatus.status}
          {scanStatus.findings_count > 0 ? ` — ${scanStatus.findings_count} finding(s)` : ""}
          {scanStatus.error_message ? ` — ${scanStatus.error_message}` : ""}
        </Alert>
      ) : null}

      <div className="flex flex-wrap gap-3">
        <TextField
          select
          label="Severity"
          value={severity}
          onChange={(e) => setSeverity(e.target.value)}
          size="small"
          sx={{ minWidth: 140 }}
        >
          <MenuItem value="">All</MenuItem>
          {SEVERITIES.filter(Boolean).map((value) => (
            <MenuItem key={value} value={value}>
              {value}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          select
          label="Engine"
          value={engine}
          onChange={(e) => setEngine(e.target.value)}
          size="small"
          sx={{ minWidth: 140 }}
        >
          <MenuItem value="">All</MenuItem>
          {ENGINES.filter(Boolean).map((value) => (
            <MenuItem key={value} value={value}>
              {value}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          select
          label="Phase"
          value={phase}
          onChange={(e) => setPhase(e.target.value)}
          size="small"
          sx={{ minWidth: 180 }}
        >
          <MenuItem value="">All</MenuItem>
          {PHASES.filter(Boolean).map((value) => (
            <MenuItem key={value} value={value}>
              {value === "PRE_DEPLOYMENT" ? "Pre-deployment" : "Post-deployment"}
            </MenuItem>
          ))}
        </TextField>
        <Button variant="outlined" startIcon={<Filter size={14} />} disabled>
          Filter
        </Button>
        <Button variant="contained" startIcon={<Download size={14} />} disabled>
          Export CSV
        </Button>
      </div>

      <Card className="bg-white border-slate-200 shadow-sm">
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow className="bg-slate-50">
                <TableCell className="text-slate-400 font-bold text-[10px] uppercase">Severity</TableCell>
                <TableCell className="text-slate-400 font-bold text-[10px] uppercase">Phase</TableCell>
                <TableCell className="text-slate-400 font-bold text-[10px] uppercase">Engine</TableCell>
                <TableCell className="text-slate-400 font-bold text-[10px] uppercase">Rule</TableCell>
                <TableCell className="text-slate-400 font-bold text-[10px] uppercase">Resource</TableCell>
                <TableCell className="text-slate-400 font-bold text-[10px] uppercase">Evidence</TableCell>
                <TableCell className="text-slate-400 font-bold text-[10px] uppercase">Recommendation</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={7} align="center">
                    <CircularProgress size={24} />
                  </TableCell>
                </TableRow>
              ) : findings.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} align="center">
                    No findings match the selected filters.
                  </TableCell>
                </TableRow>
              ) : (
                findings.map((finding) => (
                  <TableRow key={finding.id} hover>
                    <TableCell>
                      <Chip label={finding.severity} color={severityColor(finding.severity)} size="small" />
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={finding.phase === "POST_DEPLOYMENT" ? "Post" : "Pre"}
                        size="small"
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell>{finding.engine}</TableCell>
                    <TableCell className="font-mono text-xs">{finding.rule_id}</TableCell>
                    <TableCell>{finding.resource}</TableCell>
                    <TableCell>{finding.evidence ?? "—"}</TableCell>
                    <TableCell>{finding.recommendation ?? "—"}</TableCell>
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
