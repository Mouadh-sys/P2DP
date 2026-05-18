import { Typography, Card, CardContent, Button } from '@mui/material';
import { UploadCloud } from 'lucide-react';

export default function UploadTemplatePage() {
  return (
    <div className="space-y-6">
      <Typography variant="h4" className="font-bold text-slate-900 tracking-tight">Upload IaC Template</Typography>
      <Card className="bg-white border-slate-200 border-dashed border-2 shadow-none">
        <CardContent className="flex flex-col items-center justify-center py-16 text-center">
          <div className="w-16 h-16 bg-slate-50 flex items-center justify-center mb-4 rounded-full border border-slate-100 shadow-sm">
            <UploadCloud size={24} className="text-indigo-600" />
          </div>
          <Typography variant="h6" className="text-slate-800 font-bold mb-2 text-sm uppercase tracking-wider">Drag and drop your Terraform or Kubernetes YAML</Typography>
          <Typography variant="body2" className="text-slate-500 mb-6 max-w-md mx-auto text-xs">
            Uploaded templates will be automatically scanned by Checkov and Conftest before appearing in the findings queue.
          </Typography>
          <Button variant="contained" color="primary">Select Files</Button>
        </CardContent>
      </Card>
    </div>
  );
}
