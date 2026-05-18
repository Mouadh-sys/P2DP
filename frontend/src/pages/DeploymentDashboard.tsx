import { Typography, Card, CardContent, Button, Chip, LinearProgress } from '@mui/material';
import { 
  GitCommit, 
  Server, 
  ShieldAlert, 
  Activity, 
  CheckCircle2, 
  Clock, 
  AlertTriangle,
  ArrowRight,
  GitMerge,
  RotateCcw
} from 'lucide-react';
import { AreaChart, Area, XAxis, Tooltip as RechartsTooltip, ResponsiveContainer, CartesianGrid, YAxis } from 'recharts';

const mockRiskData = [
  { time: '08:00', score: 32 },
  { time: '09:00', score: 35 },
  { time: '10:00', score: 85 }, // simulated bad deployment
  { time: '11:00', score: 40 }, // remediated
  { time: '12:00', score: 42 },
  { time: '13:00', score: 38 },
];

export default function DeploymentDashboard() {
  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <Typography variant="h4" className="font-bold text-slate-900 tracking-tight">Deployment Control Center</Typography>
          <Typography variant="body1" className="text-slate-500 mt-1 text-sm font-medium">prod-cluster-us-east • Argo CD synced</Typography>
        </div>
        <div className="flex space-x-3">
          <Button variant="outlined" color="primary" startIcon={<RotateCcw size={14} />}>
            Rollback
          </Button>
          <Button variant="contained" color="primary" startIcon={<GitMerge size={14} />} href="/upload">
            Deploy Manifest
          </Button>
        </div>
      </div>

      {/* Top Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Current Risk Score" value="38" icon={<Activity size={20} className="text-amber-600" />} trend="Medium Risk" color="warning" />
        <StatCard title="Critical Findings" value="2" icon={<ShieldAlert size={20} className="text-rose-600" />} trend="Requires action" color="error" />
        <StatCard title="Threat Alerts (24h)" value="14" icon={<AlertTriangle size={20} className="text-amber-600" />} trend="3 unresolved" color="warning" />
        <StatCard title="Overall Health" value="98%" icon={<CheckCircle2 size={20} className="text-emerald-600" />} trend="All systems nominal" color="success" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 align-top">
        {/* Main Content Area */}
        <div className="lg:col-span-2 space-y-6">
          <Card className="bg-white border-slate-200">
            <CardContent>
              <Typography variant="h6" className="font-bold text-slate-700 mb-4 text-xs tracking-wider uppercase">Risk Velocity</Typography>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={mockRiskData}>
                    <defs>
                      <linearGradient id="colorScore" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.4}/>
                        <stop offset="95%" stopColor="#f59e0b" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                    <XAxis dataKey="time" stroke="#64748b" fontSize={10} tickLine={false} axisLine={false} />
                    <YAxis stroke="#64748b" fontSize={10} tickLine={false} axisLine={false} />
                    <RechartsTooltip 
                      contentStyle={{ backgroundColor: '#ffffff', borderColor: '#e2e8f0', color: '#0f172a', borderRadius: '8px', fontSize: '12px', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                      itemStyle={{ color: '#f59e0b' }}
                    />
                    <Area type="monotone" dataKey="score" stroke="#f59e0b" strokeWidth={2} fillOpacity={1} fill="url(#colorScore)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-white border-slate-200">
            <CardContent>
              <div className="flex justify-between items-center mb-4">
                <Typography variant="h6" className="font-bold text-slate-700 text-xs tracking-wider uppercase">Recent Deployments</Typography>
              </div>
              <div className="space-y-3">
                {[
                  { hash: 'a1b2c3d', msg: 'fix: updated ingress rules', status: 'Healthy', time: '10 min ago', color: 'success' },
                  { hash: 'e4f5g6h', msg: 'feat: add metrics sidecar', status: 'Syncing', time: '1 hour ago', color: 'info' },
                  { hash: 'i7j8k9l', msg: 'chore: bump redis version', status: 'Failed', time: '3 hours ago', color: 'error' },
                ].map((dep, i) => (
                  <div key={i} className="flex items-center justify-between p-2 rounded bg-slate-50 border border-slate-100 transition-colors hover:bg-slate-100">
                    <div className="flex items-center space-x-3">
                      <div className="w-8 h-8 rounded bg-white flex items-center justify-center border border-slate-200 shadow-sm">
                        <GitCommit size={16} className="text-indigo-600" />
                      </div>
                      <div>
                        <div className="flex items-center space-x-2">
                          <Typography variant="body2" className="text-slate-900 font-bold text-xs">{dep.msg}</Typography>
                          <span className="text-[10px] font-mono text-slate-500 bg-slate-200 px-1 rounded">{dep.hash}</span>
                        </div>
                        <Typography variant="caption" className="text-slate-500 flex items-center mt-0.5 text-[10px]">
                          <Clock size={10} className="mr-1" /> {dep.time}
                        </Typography>
                      </div>
                    </div>
                    <Chip label={dep.status} color={dep.color as any} size="small" variant="filled" sx={{ height: '20px', fontSize: '10px', fontWeight: 'bold' }} />
                  </div>
                ))}
            </div>
            </CardContent>
          </Card>
        </div>

        {/* Sidebar panels */}
        <div className="space-y-6">
          <Card className="bg-white border-slate-200">
            <CardContent>
              <Typography variant="h6" className="font-bold text-slate-700 mb-4 flex items-center text-xs tracking-wider uppercase">
                <Server size={14} className="mr-2 text-indigo-600" /> Environment Pipeline
              </Typography>
              <div className="space-y-4 pt-2 relative before:absolute before:inset-0 before:ml-4 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-slate-200 before:to-transparent">
                <PipelineStep state="success" label="IaC Validation" sublabel="Conftest / Checkov" />
                <PipelineStep state="warning" label="Vulnerability Scan" sublabel="Trivy - 2 High" />
                <PipelineStep state="success" label="Approval Gate" sublabel="Auto-approved" />
                <PipelineStep state="in-progress" label="GitOps Sync" sublabel="Argo CD (Running)" />
                <PipelineStep state="pending" label="Runtime Monitor" sublabel="Falco / OpenTelemetry" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-rose-50 border-rose-100">
            <CardContent>
              <Typography variant="h6" className="font-bold text-slate-700 mb-2 flex items-center text-rose-600 text-xs tracking-wider uppercase">
                <AlertTriangle size={14} className="mr-2" /> Top Threats
              </Typography>
              <div className="space-y-2 mt-3">
                <div className="p-2 bg-white border border-rose-100 rounded flex justify-between items-center shadow-sm">
                  <div>
                    <Typography variant="body2" className="text-slate-900 font-bold text-xs">Excessive Role Permissions</Typography>
                    <Typography variant="caption" className="text-slate-500 text-[10px]">Namespace: kube-system</Typography>
                  </div>
                  <Button size="small" color="error" sx={{ minWidth: '40px', p: '2px 8px' }}>View</Button>
                </div>
                <div className="p-2 bg-white border border-rose-100 rounded flex justify-between items-center shadow-sm">
                  <div>
                    <Typography variant="body2" className="text-slate-900 font-bold text-xs">Suspicious Shell Execution</Typography>
                    <Typography variant="caption" className="text-slate-500 text-[10px]">Pod: frontend-app-xyz</Typography>
                  </div>
                  <Button size="small" color="error" sx={{ minWidth: '40px', p: '2px 8px' }}>View</Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

function StatCard({ title, value, icon, trend, color }: any) {
  return (
    <Card className="bg-white border border-slate-200 shadow-sm">
      <CardContent className="p-4 flex flex-col justify-between">
        <div className="flex justify-between items-start mb-2">
          <div>
            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">{title}</p>
            <Typography variant="h4" className="text-slate-900 font-bold">{value}</Typography>
          </div>
          <div className="w-8 h-8 bg-slate-50 rounded flex items-center justify-center border border-slate-100">
            {icon}
          </div>
        </div>
        <div className="mt-1 flex items-center text-xs">
          <Typography variant="caption" color={color} className="font-bold italic mr-2">{trend}</Typography>
        </div>
      </CardContent>
    </Card>
  );
}

function PipelineStep({ state, label, sublabel }: any) {
  const getIcon = () => {
    switch (state) {
      case 'success': return <div className="w-3 h-3 rounded-full bg-emerald-500" />;
      case 'warning': return <div className="w-3 h-3 rounded-full bg-amber-500" />;
      case 'in-progress': return <div className="w-3 h-3 rounded-full bg-indigo-500 animate-pulse" />;
      default: return <div className="w-3 h-3 rounded-full border-2 border-slate-300 bg-white" />;
    }
  };

  return (
    <div className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active text-xs">
      <div className="flex items-center justify-center w-8 h-8 rounded-full border-2 border-slate-200 bg-white z-10 shadow-sm">
        {getIcon()}
      </div>
      <div className="w-[calc(100%-3rem)] md:w-[calc(50%-2rem)] p-2 rounded bg-white border border-slate-200 shadow-sm ml-3 md:ml-0 md:mr-3 group-odd:md:mr-0 group-odd:md:ml-3">
        <div className="flex items-center justify-between">
          <Typography variant="body2" className="font-bold text-slate-800 text-xs">{label}</Typography>
        </div>
        <Typography variant="caption" className="text-slate-500 text-[10px]">{sublabel}</Typography>
        {state === 'in-progress' && (
          <LinearProgress className="mt-1.5 h-1 rounded bg-indigo-100" sx={{ '& .MuiLinearProgress-bar': { backgroundColor: '#4f46e5' } }} />
        )}
      </div>
    </div>
  );
}
