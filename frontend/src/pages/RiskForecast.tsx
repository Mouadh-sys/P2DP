import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Grid2,
  List,
  ListItem,
  ListItemText,
  Stack,
  Typography,
} from "@mui/material";
import { useCallback, useEffect, useState } from "react";
import { Link as RouterLink, useParams } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import client from "../api/client";

type RiskFactor = {
  key: string;
  label: string;
  weight: number;
  contribution: number;
  impact: string;
  recommendation: string;
  findings: string[];
};

type RiskAssessment = {
  id: string;
  env_id: string;
  score: number;
  risk_class: "LOW" | "MEDIUM" | "HIGH";
  factors: RiskFactor[];
  top_factors: RiskFactor[];
  recommendations: string[];
  timestamp: string;
};

function riskChipColor(riskClass: string): "success" | "warning" | "error" {
  switch (riskClass) {
    case "HIGH":
      return "error";
    case "MEDIUM":
      return "warning";
    default:
      return "success";
  }
}

function formatRiskClass(riskClass: string) {
  return riskClass.charAt(0) + riskClass.slice(1).toLowerCase();
}

export default function RiskForecast() {
  const { projectId, environmentId } = useParams();
  const [assessment, setAssessment] = useState<RiskAssessment | null>(null);
  const [loading, setLoading] = useState(true);
  const [computing, setComputing] = useState(false);
  const [error, setError] = useState("");

  const loadLatest = useCallback(async () => {
    if (!environmentId) return;
    try {
      const response = await client.get<RiskAssessment>(
        `/api/environments/${environmentId}/risk-assessments/latest`
      );
      setAssessment(response.data);
      setError("");
    } catch {
      setAssessment(null);
      setError("No risk assessment yet. Run a scan, then compute risk.");
    } finally {
      setLoading(false);
    }
  }, [environmentId]);

  useEffect(() => {
    loadLatest();
  }, [loadLatest]);

  const handleCompute = async () => {
    if (!environmentId) return;
    setComputing(true);
    try {
      const response = await client.post<RiskAssessment>(
        `/api/environments/${environmentId}/risk-assessments`
      );
      setAssessment(response.data);
      setError("");
    } catch {
      setError("Failed to compute risk assessment.");
    } finally {
      setComputing(false);
    }
  };

  const chartData =
    assessment?.factors.map((factor) => ({
      name: factor.label,
      contribution: factor.contribution,
    })) ?? [];

  return (
    <Box sx={{ p: 3 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">Risk Forecast</Typography>
        <Stack direction="row" spacing={1}>
          {projectId && environmentId ? (
            <Button
              component={RouterLink}
              to={`/projects/${projectId}/environments/${environmentId}/findings`}
              variant="outlined"
            >
              View findings
            </Button>
          ) : null}
          <Button variant="contained" onClick={handleCompute} disabled={computing}>
            {computing ? "Computing…" : "Compute risk"}
          </Button>
        </Stack>
      </Stack>

      {error ? <Alert severity="info" sx={{ mb: 2 }}>{error}</Alert> : null}

      {loading ? (
        <Box display="flex" justifyContent="center" py={6}>
          <CircularProgress />
        </Box>
      ) : assessment ? (
        <Grid2 container spacing={3}>
          <Grid2 size={{ xs: 12, md: 4 }}>
            <Card>
              <CardContent>
                <Typography variant="overline" color="text.secondary">
                  Risk score
                </Typography>
                <Typography variant="h2" fontWeight={700} mb={1}>
                  {Math.round(assessment.score)}
                </Typography>
                <Chip
                  label={formatRiskClass(assessment.risk_class)}
                  color={riskChipColor(assessment.risk_class)}
                />
                <Typography variant="body2" color="text.secondary" mt={2}>
                  Assessed at {new Date(assessment.timestamp).toLocaleString()}
                </Typography>
              </CardContent>
            </Card>
          </Grid2>

          <Grid2 size={{ xs: 12, md: 8 }}>
            <Card sx={{ height: "100%" }}>
              <CardContent>
                <Typography variant="h6" mb={2}>
                  Contribution by factor
                </Typography>
                {chartData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={280}>
                    <BarChart data={chartData} layout="vertical" margin={{ left: 24, right: 16 }}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis type="number" domain={[0, 100]} />
                      <YAxis type="category" dataKey="name" width={180} tick={{ fontSize: 12 }} />
                      <Tooltip />
                      <Bar dataKey="contribution" fill="#1976d2" radius={[0, 4, 4, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <Typography color="text.secondary">No risk factors triggered.</Typography>
                )}
              </CardContent>
            </Card>
          </Grid2>

          <Grid2 size={{ xs: 12, md: 6 }}>
            <Card>
              <CardContent>
                <Typography variant="h6" mb={2}>
                  Top risk factors
                </Typography>
                <List dense>
                  {assessment.top_factors.length > 0 ? (
                    assessment.top_factors.map((factor) => (
                      <ListItem key={factor.key} alignItems="flex-start" sx={{ px: 0 }}>
                        <ListItemText
                          primary={`${factor.label} (+${factor.contribution})`}
                          secondary={factor.impact}
                        />
                      </ListItem>
                    ))
                  ) : (
                    <ListItem sx={{ px: 0 }}>
                      <ListItemText primary="No contributing factors detected." />
                    </ListItem>
                  )}
                </List>
              </CardContent>
            </Card>
          </Grid2>

          <Grid2 size={{ xs: 12, md: 6 }}>
            <Card>
              <CardContent>
                <Typography variant="h6" mb={2}>
                  Recommendations
                </Typography>
                <List dense>
                  {assessment.recommendations.map((item) => (
                    <ListItem key={item} sx={{ px: 0 }}>
                      <ListItemText primary={item} />
                    </ListItem>
                  ))}
                </List>
              </CardContent>
            </Card>
          </Grid2>

          <Grid2 size={{ xs: 12 }}>
            <Card>
              <CardContent>
                <Typography variant="h6" mb={2}>
                  All contributing factors
                </Typography>
                <Stack spacing={2}>
                  {assessment.factors.map((factor) => (
                    <Box key={factor.key} border={1} borderColor="divider" borderRadius={1} p={2}>
                      <Stack direction="row" justifyContent="space-between" mb={1}>
                        <Typography fontWeight={600}>{factor.label}</Typography>
                        <Chip size="small" label={`+${factor.contribution}`} />
                      </Stack>
                      <Typography variant="body2" color="text.secondary" mb={1}>
                        {factor.impact}
                      </Typography>
                      <Typography variant="body2" mb={1}>
                        {factor.recommendation}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        Related findings: {factor.findings.join(", ") || "—"}
                      </Typography>
                    </Box>
                  ))}
                </Stack>
              </CardContent>
            </Card>
          </Grid2>
        </Grid2>
      ) : null}
    </Box>
  );
}
