import { Typography, Card, CardContent } from '@mui/material';

export default function ReportsPage() {
  return (
    <div className="space-y-6">
      <Typography variant="h4" className="font-bold text-slate-900 tracking-tight">Reports</Typography>
      <Card className="bg-white border-slate-200 shadow-sm">
        <CardContent>
          <Typography variant="h6" className="text-slate-800 font-bold mb-2">Compliance & Audit Reports</Typography>
          <Typography variant="body2" className="text-slate-500 text-xs">
            Generate and export SOC2, PCI-DSS, and custom security posture reports.
          </Typography>
        </CardContent>
      </Card>
    </div>
  );
}
