import { Alert, Button, Card, CardContent, CircularProgress, Typography } from "@mui/material";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { projectsApi } from "../api/endpoints";

type Project = { id: string; name: string };
type Environment = { id: string; project_id: string; target: string; status: string };

export default function EnvironmentPage() {
  const navigate = useNavigate();
  const [rows, setRows] = useState<Array<{ project: Project; environment: Environment }>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const load = async () => {
      try {
        const projectsResponse = await projectsApi.list();
        const pairs = await Promise.all(
          projectsResponse.data.map(async (project) => {
            const envResponse = await projectsApi.listEnvironments(project.id);
            return envResponse.data.map((environment) => ({ project, environment }));
          })
        );
        setRows(pairs.flat());
        setError("");
      } catch {
        setError("Failed to load deployments.");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  return (
    <div className="space-y-6">
      <Typography variant="h4" className="font-bold text-slate-900 tracking-tight">
        Deployments
      </Typography>

      {error ? <Alert severity="error">{error}</Alert> : null}

      {loading ? (
        <div className="flex justify-center py-12">
          <CircularProgress />
        </div>
      ) : rows.length === 0 ? (
        <Alert severity="info">
          No environments yet. Create a project and environment first.{" "}
          <Button size="small" onClick={() => navigate("/projects")}>
            Go to projects
          </Button>
        </Alert>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {rows.map(({ project, environment }) => (
            <Card key={environment.id} className="bg-white border-slate-200 shadow-sm">
              <CardContent>
                <Typography variant="h6" className="text-slate-800 font-bold mb-2">
                  {project.name} / {environment.target}
                </Typography>
                <Typography variant="body2" className="text-slate-500 mb-4 text-xs">
                  Status: {environment.status}
                </Typography>
                <Button
                  variant="contained"
                  onClick={() => navigate(`/projects/${project.id}/environments`)}
                >
                  Manage environment
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
