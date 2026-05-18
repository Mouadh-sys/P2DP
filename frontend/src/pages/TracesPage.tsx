import {
  Alert,
  Card,
  CircularProgress,
  Link,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import { useCallback, useEffect, useState } from "react";

import { environmentsApi, projectsApi } from "../api/endpoints";
import { jaegerTraceUrl } from "../api/jaeger";
import type { DeploymentRun } from "../api/types";

type TraceRow = {
  projectName: string;
  environmentTarget: string;
  deployment: DeploymentRun;
};

export default function TracesPage() {
  const [rows, setRows] = useState<TraceRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const projectsResponse = await projectsApi.list();
      const collected: TraceRow[] = [];

      for (const project of projectsResponse.data) {
        const envsResponse = await projectsApi.listEnvironments(project.id);
        for (const env of envsResponse.data) {
          try {
            const depResponse = await environmentsApi.latestDeployment(env.id);
            if (depResponse.data.trace_id) {
              collected.push({
                projectName: project.name,
                environmentTarget: env.target,
                deployment: depResponse.data,
              });
            }
          } catch {
            // No deployment yet for this environment
          }
        }
      }

      setRows(collected);
      setError("");
    } catch {
      setError("Failed to load deployment traces.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const jaegerBase = import.meta.env.VITE_JAEGER_UI_URL ?? "http://localhost:16686";

  return (
    <div className="space-y-6">
      <Typography variant="h4" className="font-bold text-slate-900 tracking-tight">
        Traces
      </Typography>
      <Typography variant="body2" className="text-slate-500">
        OpenTelemetry trace IDs from recent deployments (view in Jaeger at {jaegerBase}).
      </Typography>

      {error ? <Alert severity="error">{error}</Alert> : null}

      <Card className="bg-white border-slate-200 shadow-sm">
        {loading ? (
          <div className="flex justify-center py-12">
            <CircularProgress />
          </div>
        ) : rows.length === 0 ? (
          <Typography className="p-6 text-slate-500 text-sm">
            No deployments with trace IDs yet. Deploy an environment to generate traces.
          </Typography>
        ) : (
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow className="bg-slate-50">
                  <TableCell>Project</TableCell>
                  <TableCell>Environment</TableCell>
                  <TableCell>Deployment</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Trace ID</TableCell>
                  <TableCell>Jaeger</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {rows.map((row) => (
                  <TableRow key={row.deployment.deployment_id} hover>
                    <TableCell>{row.projectName}</TableCell>
                    <TableCell>{row.environmentTarget}</TableCell>
                    <TableCell className="font-mono text-xs">{row.deployment.deployment_id}</TableCell>
                    <TableCell>{row.deployment.status}</TableCell>
                    <TableCell className="font-mono text-xs">{row.deployment.trace_id}</TableCell>
                    <TableCell>
                      <Link
                        href={jaegerTraceUrl(row.deployment.trace_id!)}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        Open in Jaeger
                      </Link>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Card>
    </div>
  );
}
