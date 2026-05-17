import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Grid2,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import client from "../api/client";

type Project = {
  id: string;
  name: string;
  owner_id: string;
};

type Environment = {
  id: string;
  project_id: string;
  target: "dev" | "local-k8s";
  status: string;
};

export default function Projects() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]);
  const [environmentsByProject, setEnvironmentsByProject] = useState<Record<string, Environment[]>>({});
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [error, setError] = useState("");

  const loadProjects = async () => {
    try {
      const projectsResponse = await client.get<Project[]>("/api/projects");
      setProjects(projectsResponse.data);
      const environmentResponses = await Promise.allSettled(
        projectsResponse.data.map(async (project) => {
          const response = await client.get<Environment[]>(`/api/projects/${project.id}/environments`);
          return [project.id, response.data] as const;
        })
      );
      setEnvironmentsByProject(
        Object.fromEntries(
          environmentResponses
            .filter((result): result is PromiseFulfilledResult<readonly [string, Environment[]]> => result.status === "fulfilled")
            .map((result) => result.value)
        )
      );
      setError("");
    } catch {
      setError("Failed to load projects.");
    }
  };

  useEffect(() => {
    loadProjects();
  }, []);

  const handleCreate = async (event: FormEvent) => {
    event.preventDefault();
    try {
      await client.post("/api/projects", { name });
      setName("");
      setOpen(false);
      await loadProjects();
    } catch {
      setError("Failed to create project.");
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">Projects</Typography>
        <Button variant="contained" onClick={() => setOpen(true)}>
          Create New Project
        </Button>
      </Stack>

      {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}

      <Grid2 container spacing={2}>
        {projects.map((project) => (
          <Grid2 size={{ xs: 12, sm: 6, md: 4 }} key={project.id}>
            <Card>
              <CardContent>
                <Typography variant="h6" mb={1}>
                  {project.name}
                </Typography>
                <Typography variant="body2" color="text.secondary" mb={2}>
                  Environments:{" "}
                  {environmentsByProject[project.id]?.length
                    ? environmentsByProject[project.id].map((env) => env.target).join(", ")
                    : "none"}
                </Typography>
                <Button variant="outlined" onClick={() => navigate(`/projects/${project.id}/environments`)}>
                  Open project
                </Button>
              </CardContent>
            </Card>
          </Grid2>
        ))}
      </Grid2>

      <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="sm">
        <Box component="form" onSubmit={handleCreate}>
          <DialogTitle>Create New Project</DialogTitle>
          <DialogContent>
            <TextField
              autoFocus
              margin="dense"
              label="Project name"
              fullWidth
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setOpen(false)}>Cancel</Button>
            <Button type="submit" variant="contained">
              Create
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
    </Box>
  );
}
