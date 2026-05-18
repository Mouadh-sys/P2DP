import {
  Alert,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Grid2,
  LinearProgress,
  List,
  ListItem,
  ListItemText,
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

export default function RiskForecastPage() {
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

  if (!environmentId) {
    return (
      <Alert severity="info">
        Open a project environment to view risk forecast.{" "}
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
            Risk Forecast
          </Typography>
          <Typography variant="body1" className="text-slate-500 mt-1 text-sm font-medium">
            Multi-layer risk calculation from live findings
          </Typography>
        </div>
        <div className="flex flex-wrap gap-2">
          {projectId ? (
            <Button
              variant="outlined"
              component={RouterLink}
              to={`/projects/${projectId}/environments/${environmentId}/findings`}
            >
              View findings
            </Button>
          ) : null}
          <Button variant="contained" onClick={handleCompute} disabled={computing}>
            {computing ? "Computing…" : "Compute risk"}
          </Button>
        </div>
      </div>

      {error ? <Alert severity="info">{error}</Alert> : null}

      {loading ? (
        <div className="flex justify-center py-12">
          <CircularProgress />
        </div>
      ) : assessment ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Card className="bg-white border-slate-200 flex flex-col justify-center items-center p-6 text-center shadow-sm">
            <Typography variant="h2" className="font-bold text-slate-900 tracking-tighter">
              {Math.round(assessment.score)}
            </Typography>
            <Chip
              label={formatRiskClass(assessment.risk_class)}
              color={riskChipColor(assessment.risk_class)}
              sx={{ mt: 1 }}
            />
            <Typography variant="body2" className="text-slate-500 text-xs mt-3">
              Assessed at {new Date(assessment.timestamp).toLocaleString()}
            </Typography>
          </Card>

          <Card className="bg-white border-slate-200 lg:col-span-2 shadow-sm">
            <CardContent>
              <Typography variant="h6" className="font-bold text-slate-700 mb-4 text-xs tracking-wider uppercase">
                Contribution by factor
              </Typography>
              {chartData.length > 0 ? (
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={chartData} layout="vertical" margin={{ left: 24, right: 16 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis type="number" domain={[0, 100]} />
                    <YAxis type="category" dataKey="name" width={180} tick={{ fontSize: 12 }} />
                    <Tooltip />
                    <Bar dataKey="contribution" fill="#4f46e5" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <Typography color="text.secondary">No risk factors triggered.</Typography>
              )}
            </CardContent>
          </Card>

          <Card className="bg-white border-slate-200 shadow-sm">
            <CardContent>
              <Typography variant="h6" className="font-bold text-slate-700 mb-4 text-xs tracking-wider uppercase">
                Top risk factors
              </Typography>
              <div className="space-y-4">
                {assessment.top_factors.length > 0 ? (
                  assessment.top_factors.map((factor) => (
                    <div key={factor.key}>
                      <div className="flex justify-between mb-1 text-xs">
                        <Typography variant="body2" className="text-slate-700 font-bold text-xs">
                          {factor.label}
                        </Typography>
                        <Typography variant="body2" className="text-slate-500 font-mono text-[10px]">
                          +{factor.contribution}
                        </Typography>
                      </div>
                      <LinearProgress
                        variant="determinate"
                        value={Math.min(factor.contribution, 100)}
                        sx={{ height: 4, borderRadius: 2 }}
                      />
                      <Typography variant="caption" color="text.secondary">
                        {factor.impact}
                      </Typography>
                    </div>
                  ))
                ) : (
                  <Typography color="text.secondary">No contributing factors detected.</Typography>
                )}
              </div>
            </CardContent>
          </Card>

          <Card className="bg-white border-slate-200 shadow-sm">
            <CardContent>
              <Typography variant="h6" className="font-bold text-slate-700 mb-4 text-xs tracking-wider uppercase">
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

          <Grid2 size={{ xs: 12 }}>
            <Card className="bg-white border-slate-200 shadow-sm">
              <CardContent>
                <Typography variant="h6" className="font-bold text-slate-700 mb-4 text-xs tracking-wider uppercase">
                  All contributing factors
                </Typography>
                <div className="space-y-3">
                  {assessment.factors.map((factor) => (
                    <div key={factor.key} className="border border-slate-200 rounded-lg p-3">
                      <div className="flex justify-between mb-1">
                        <Typography fontWeight={600}>{factor.label}</Typography>
                        <Chip size="small" label={`+${factor.contribution}`} />
                      </div>
                      <Typography variant="body2" color="text.secondary">
                        {factor.impact}
                      </Typography>
                      <Typography variant="body2" sx={{ mt: 1 }}>
                        {factor.recommendation}
                      </Typography>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </Grid2>
        </div>
      ) : null}
    </div>
  );
}
