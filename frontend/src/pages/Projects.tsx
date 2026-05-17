import {
  Alert,
  Box,
  Button,
  Card,
  CardActionArea,
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

export default function Projects() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]);
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [error, setError] = useState("");

  const loadProjects = async () => {
    try {
      const response = await client.get<Project[]>("/api/projects");
      setProjects(response.data);
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
              <CardActionArea onClick={() => navigate(`/projects/${project.id}/environments`)}>
                <CardContent>
                  <Typography variant="h6">{project.name}</Typography>
                  <Typography color="text.secondary" variant="body2">
                    Owner: {project.owner_id}
                  </Typography>
                </CardContent>
              </CardActionArea>
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
