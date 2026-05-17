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
import { useParams } from "react-router-dom";

import client from "../api/client";

type Environment = {
  id: string;
  project_id: string;
  target: "dev" | "local-k8s";
  status: string;
};

export default function EnvironmentDetail() {
  const { projectId } = useParams();
  const [target, setTarget] = useState<"dev" | "local-k8s">("local-k8s");
  const [status, setStatus] = useState<"pending" | "active" | "failed">("pending");
  const [environments, setEnvironments] = useState<Environment[]>([]);
  const [fileByEnv, setFileByEnv] = useState<Record<string, File | null>>({});
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const loadEnvironments = useCallback(async () => {
    if (!projectId) return;
    try {
      const response = await client.get<Environment[]>(`/api/projects/${projectId}/environments`);
      setEnvironments(response.data);
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
      setMessage(`File stored successfully at: ${response.data.files_ref}`);
      setError("");
    } catch {
      setError("Failed to upload template archive.");
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" mb={3}>
        Environments
      </Typography>

      {message ? <Alert severity="success" sx={{ mb: 2 }}>{message}</Alert> : null}
      {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}

      {environments.length === 0 ? (
        <Box component="form" onSubmit={handleCreateEnvironment} sx={{ mb: 3 }}>
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
        <Typography variant="body2" color="text.secondary" mb={3}>
          This project already has its single MVP environment.
        </Typography>
      )}

      <Grid2 container spacing={2}>
        {environments.map((environment) => (
          <Grid2 size={{ xs: 12, md: 6 }} key={environment.id}>
            <Card>
              <CardContent>
                <Typography variant="h6" mb={1}>
                  {environment.target}
                </Typography>
                <Typography variant="body2" color="text.secondary" mb={2}>
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
                </Stack>
              </CardContent>
            </Card>
          </Grid2>
        ))}
      </Grid2>
    </Box>
  );
}
