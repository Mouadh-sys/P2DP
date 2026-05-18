import {
  Alert,
  Button,
  Card,
  CardContent,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  TextField,
  Typography,
} from "@mui/material";
import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { projectsApi } from "../api/endpoints";

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

export default function ProjectsPage() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]);
  const [environmentsByProject, setEnvironmentsByProject] = useState<Record<string, Environment[]>>({});
  const [open, setOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Project | null>(null);
  const [name, setName] = useState("");
  const [error, setError] = useState("");

  const loadProjects = async () => {
    try {
      const projectsResponse = await projectsApi.list();
      setProjects(projectsResponse.data);
      const environmentResponses = await Promise.allSettled(
        projectsResponse.data.map(async (project) => {
          const response = await projectsApi.listEnvironments(project.id);
          return [project.id, response.data] as const;
        })
      );
      setEnvironmentsByProject(
        Object.fromEntries(
          environmentResponses
            .filter(
              (result): result is PromiseFulfilledResult<readonly [string, Environment[]]> =>
                result.status === "fulfilled"
            )
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
      await projectsApi.create(name);
      setName("");
      setOpen(false);
      await loadProjects();
    } catch {
      setError("Failed to create project.");
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await projectsApi.delete(deleteTarget.id);
      setDeleteTarget(null);
      await loadProjects();
    } catch {
      setError("Failed to delete project.");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <Typography variant="h4" className="font-bold text-slate-900 tracking-tight">
          Projects
        </Typography>
        <Button variant="contained" onClick={() => setOpen(true)}>
          Create New Project
        </Button>
      </div>

      {error ? <Alert severity="error">{error}</Alert> : null}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {projects.map((project) => (
          <Card key={project.id} className="bg-white border-slate-200 shadow-sm">
            <CardContent>
              <Typography variant="h6" className="text-slate-800 font-bold mb-2">
                {project.name}
              </Typography>
              <Typography variant="body2" className="text-slate-500 mb-4 text-xs">
                Environments:{" "}
                {environmentsByProject[project.id]?.length
                  ? environmentsByProject[project.id].map((env) => env.target).join(", ")
                  : "none"}
              </Typography>
              <div className="flex flex-wrap gap-2">
                <Button variant="outlined" onClick={() => navigate(`/projects/${project.id}/environments`)}>
                  Open project
                </Button>
                <Button variant="outlined" color="error" onClick={() => setDeleteTarget(project)}>
                  Delete
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Dialog open={Boolean(deleteTarget)} onClose={() => setDeleteTarget(null)} fullWidth maxWidth="sm">
        <DialogTitle>Delete project</DialogTitle>
        <DialogContent>
          <Typography>
            Delete &quot;{deleteTarget?.name}&quot;? This removes its environment and uploaded templates.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteTarget(null)}>Cancel</Button>
          <Button variant="contained" color="error" onClick={handleDelete}>
            Delete
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="sm">
        <form onSubmit={handleCreate}>
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
        </form>
      </Dialog>
    </div>
  );
}
