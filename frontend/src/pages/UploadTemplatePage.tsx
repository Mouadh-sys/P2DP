import { Alert, Button, Card, CardContent, Typography } from "@mui/material";
import { UploadCloud } from "lucide-react";
import { Link as RouterLink } from "react-router-dom";

export default function UploadTemplatePage() {
  return (
    <div className="space-y-6">
      <Typography variant="h4" className="font-bold text-slate-900 tracking-tight">
        Upload IaC Template
      </Typography>
      <Alert severity="info">
        Template upload is performed on the environment page (per project). Open a project, create an environment,
        then use <strong>Upload Template</strong> on the environment card.
      </Alert>
      <Card className="bg-white border-slate-200 border-dashed border-2 shadow-none">
        <CardContent className="flex flex-col items-center justify-center py-16 text-center">
          <div className="w-16 h-16 bg-slate-50 flex items-center justify-center mb-4 rounded-full border border-slate-100 shadow-sm">
            <UploadCloud size={24} className="text-indigo-600" />
          </div>
          <Typography variant="h6" className="text-slate-800 font-bold mb-2 text-sm uppercase tracking-wider">
            ZIP archive (.tf, .yaml, Dockerfile)
          </Typography>
          <Typography variant="body2" className="text-slate-500 mb-6 max-w-md mx-auto text-xs">
            Uploaded templates are scanned by Trivy, Checkov, and Conftest before deployment.
          </Typography>
          <Button variant="contained" color="primary" component={RouterLink} to="/projects">
            Go to projects
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
