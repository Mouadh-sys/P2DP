import { 
  Typography, 
  Card, 
  Table, 
  TableBody, 
  TableCell, 
  TableContainer, 
  TableHead, 
  TableRow, 
  Chip,
  Button
} from '@mui/material';
import { AlertOctagon, CheckCircle, Clock } from 'lucide-react';

const mockAlerts = [
  { id: 'ALT-8219', time: '2 mins ago', source: 'Falco', type: 'Terminal Exec', severity: 'Critical', evidence: 'bash executed in pod/payment-api-4z', status: 'Open' },
  { id: 'ALT-8218', time: '15 mins ago', source: 'KubeAudit', type: 'Privilege Escalation', severity: 'High', evidence: 'ServiceAccount requested cluster-admin', status: 'Investigating' },
  { id: 'ALT-8217', time: '1 hour ago', source: 'NetworkPolicy', type: 'Denied Traffic', severity: 'Low', evidence: 'Ingress from 10.0.0.5 blocked', status: 'Resolved' },
  { id: 'ALT-8216', time: '3 hours ago', source: 'Falco', type: 'File Deletion', severity: 'Medium', evidence: 'rm -rf /var/logs in pod/nginx', status: 'Open' },
];

const getStatusColor = (status: string) => {
  switch (status) {
    case 'Open': return 'error';
    case 'Investigating': return 'warning';
    case 'Resolved': return 'success';
    default: return 'default';
  }
};

export default function ThreatAlertsPage() {
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <Typography variant="h4" className="font-bold text-slate-900 tracking-tight">Threat Alerts</Typography>
          <Typography variant="body1" className="text-slate-500 mt-1 text-sm font-medium">Runtime detections and security events</Typography>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <Card className="bg-rose-50 border-rose-200 p-4 flex items-center shadow-sm">
          <AlertOctagon size={32} className="text-rose-600 mr-4" />
          <div>
            <Typography variant="h5" className="text-slate-900 font-bold">2</Typography>
            <Typography variant="body2" className="text-slate-600 text-xs font-medium uppercase tracking-wider">Open Critical Alerts</Typography>
          </div>
        </Card>
        <Card className="bg-amber-50 border-amber-200 p-4 flex items-center shadow-sm">
          <Clock size={32} className="text-amber-600 mr-4" />
          <div>
            <Typography variant="h5" className="text-slate-900 font-bold">1</Typography>
            <Typography variant="body2" className="text-slate-600 text-xs font-medium uppercase tracking-wider">Investigating</Typography>
          </div>
        </Card>
        <Card className="bg-emerald-50 border-emerald-200 p-4 flex items-center shadow-sm">
          <CheckCircle size={32} className="text-emerald-600 mr-4" />
          <div>
            <Typography variant="h5" className="text-slate-900 font-bold">14</Typography>
            <Typography variant="body2" className="text-slate-600 text-xs font-medium uppercase tracking-wider">Resolved Today</Typography>
          </div>
        </Card>
      </div>

      <Card className="bg-white border-slate-200 shadow-sm">
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow className="bg-slate-50">
                <TableCell className="text-slate-400 font-bold border-b border-slate-200 text-[10px] uppercase tracking-wider">Timestamp</TableCell>
                <TableCell className="text-slate-400 font-bold border-b border-slate-200 text-[10px] uppercase tracking-wider">Alert ID</TableCell>
                <TableCell className="text-slate-400 font-bold border-b border-slate-200 text-[10px] uppercase tracking-wider">Source / Type</TableCell>
                <TableCell className="text-slate-400 font-bold border-b border-slate-200 text-[10px] uppercase tracking-wider">Severity</TableCell>
                <TableCell className="text-slate-400 font-bold border-b border-slate-200 text-[10px] uppercase tracking-wider">Evidence</TableCell>
                <TableCell className="text-slate-400 font-bold border-b border-slate-200 text-[10px] uppercase tracking-wider">Status</TableCell>
                <TableCell className="text-slate-400 font-bold border-b border-slate-200 text-[10px] uppercase tracking-wider w-24">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody className="text-xs divide-y divide-slate-100">
              {mockAlerts.map((row) => (
                <TableRow key={row.id} className="hover:bg-slate-50 transition-colors">
                  <TableCell className="text-slate-600 border-b border-slate-100 whitespace-nowrap text-xs">{row.time}</TableCell>
                  <TableCell className="text-slate-700 font-mono text-[10px] border-b border-slate-100">{row.id}</TableCell>
                  <TableCell className="border-b border-slate-100">
                    <div className="text-slate-800 font-bold text-xs">{row.type}</div>
                    <div className="text-slate-500 text-[10px]">{row.source}</div>
                  </TableCell>
                  <TableCell className="border-b border-slate-100">
                    <Chip 
                      label={row.severity} 
                      size="small" 
                      color={row.severity === 'Critical' ? 'error' : row.severity === 'High' ? 'warning' : row.severity === 'Medium' ? 'info' : 'default'} 
                      sx={{ height: '20px', fontSize: '10px', fontWeight: 'bold' }} 
                    />
                  </TableCell>
                  <TableCell className="text-slate-600 text-xs border-b border-slate-100">{row.evidence}</TableCell>
                  <TableCell className="border-b border-slate-100">
                    <Chip label={row.status} size="small" variant="filled" color={getStatusColor(row.status) as any} sx={{ height: '20px', fontSize: '10px', fontWeight: 'bold' }} />
                  </TableCell>
                  <TableCell className="border-b border-slate-100">
                    <Button size="small" variant="text" color="primary" sx={{ minWidth: '40px', p: '2px 8px' }}>View</Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Card>
    </div>
  );
}
