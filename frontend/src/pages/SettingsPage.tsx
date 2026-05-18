import { Typography, Card, CardContent } from '@mui/material';

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <Typography variant="h4" className="font-bold text-slate-900 tracking-tight">Settings</Typography>
      <Card className="bg-white border-slate-200 shadow-sm">
        <CardContent>
          <Typography variant="h6" className="text-slate-800 font-bold">Platform Configuration</Typography>
          <Typography variant="body2" className="text-slate-500 mt-2">
            Configure Git integrations, Checkov rulesets, ArgoCD endpoints, and Falco settings.
          </Typography>
        </CardContent>
      </Card>
    </div>
  );
}
