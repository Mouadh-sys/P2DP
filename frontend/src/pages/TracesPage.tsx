import { Typography, Card, CardContent } from '@mui/material';

export default function TracesPage() {
  return (
    <div className="space-y-6">
      <Typography variant="h4" className="font-bold text-slate-900 tracking-tight">Traces</Typography>
      <Card className="bg-white border-slate-200 shadow-sm">
        <CardContent>
          <Typography variant="h6" className="text-slate-800 font-bold mb-2">Distributed Traces</Typography>
          <Typography variant="body2" className="text-slate-500 text-xs">
            OpenTelemetry and Jaeger trace integration goes here.
          </Typography>
        </CardContent>
      </Card>
    </div>
  );
}
