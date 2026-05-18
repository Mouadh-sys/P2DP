import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  MenuItem,
  Paper,
  Stack,
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
import { Link as RouterLink, useParams, useSearchParams } from "react-router-dom";

import client from "../api/client";

type Finding = {
  id: string;
  env_id: string;
  layer: string;
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

export default function Findings() {
  const { projectId, environmentId } = useParams();
  const [searchParams] = useSearchParams();
  const templateVersionId = searchParams.get("templateVersionId");
  const scanId = searchParams.get("scanId");

  const [findings, setFindings] = useState<Finding[]>([]);
  const [severity, setSeverity] = useState("");
  const [engine, setEngine] = useState("");
  const [scanStatus, setScanStatus] = useState<ScanStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadFindings = useCallback(async () => {
    if (!environmentId) return;
    try {
      const params: Record<string, string> = {};
      if (severity) params.severity = severity;
      if (engine) params.engine = engine;
      const response = await client.get<Finding[]>(`/api/findings/environments/${environmentId}`, { params });
      setFindings(response.data);
      setError("");
    } catch {
      setError("Failed to load findings.");
    } finally {
      setLoading(false);
    }
  }, [environmentId, severity, engine]);

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

  return (
    <Box sx={{ p: 3 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">Misconfiguration Findings</Typography>
        <Stack direction="row" spacing={1}>
          {projectId && environmentId ? (
            <>
              <Button component={RouterLink} to={`/projects/${projectId}/environments`} variant="outlined">
                Back to environment
              </Button>
              <Button
                component={RouterLink}
                to={`/projects/${projectId}/environments/${environmentId}/risk`}
                variant="outlined"
              >
                Risk forecast
              </Button>
            </>
          ) : null}
        </Stack>
      </Stack>

      {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}

      {scanStatus ? (
        <Alert
          severity={scanStatus.status === "FAILED" ? "error" : scanStatus.status === "SUCCESS" ? "success" : "info"}
          sx={{ mb: 2 }}
          icon={scanInProgress ? <CircularProgress size={18} /> : undefined}
        >
          Scan status: {scanStatus.status}
          {scanStatus.findings_count > 0 ? ` — ${scanStatus.findings_count} finding(s) in environment` : ""}
          {scanStatus.error_message ? ` — ${scanStatus.error_message}` : ""}
        </Alert>
      ) : null}

      <Stack direction={{ xs: "column", sm: "row" }} spacing={2} mb={3}>
        <TextField
          select
          label="Severity"
          value={severity}
          onChange={(e) => setSeverity(e.target.value)}
          sx={{ minWidth: 160 }}
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
          sx={{ minWidth: 160 }}
        >
          <MenuItem value="">All</MenuItem>
          {ENGINES.filter(Boolean).map((value) => (
            <MenuItem key={value} value={value}>
              {value}
            </MenuItem>
          ))}
        </TextField>
      </Stack>

      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Severity</TableCell>
              <TableCell>Engine</TableCell>
              <TableCell>Rule</TableCell>
              <TableCell>Resource</TableCell>
              <TableCell>Evidence</TableCell>
              <TableCell>Recommendation</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={6} align="center">
                  <CircularProgress size={24} />
                </TableCell>
              </TableRow>
            ) : findings.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} align="center">
                  No findings match the selected filters.
                </TableCell>
              </TableRow>
            ) : (
              findings.map((finding) => (
                <TableRow key={finding.id} hover>
                  <TableCell>
                    <Chip label={finding.severity} color={severityColor(finding.severity)} size="small" />
                  </TableCell>
                  <TableCell>{finding.engine}</TableCell>
                  <TableCell>{finding.rule_id}</TableCell>
                  <TableCell>{finding.resource}</TableCell>
                  <TableCell>{finding.evidence ?? "—"}</TableCell>
                  <TableCell>{finding.recommendation ?? "—"}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}
