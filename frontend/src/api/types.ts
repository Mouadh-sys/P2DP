export type Project = {
  id: string;
  name: string;
  owner_id: string;
  created_at: string;
};

export type Environment = {
  id: string;
  project_id: string;
  target: string;
  status: string;
};

export type TemplateVersion = {
  id: string;
  env_id: string;
  files_ref: string;
  created_at: string;
};

export type DeploymentRun = {
  deployment_id: string;
  env_id: string;
  status: string;
  git_commit: string | null;
  trace_id: string | null;
  logs_ref: string | null;
  started_at: string;
  finished_at: string | null;
};

export type Finding = {
  id: string;
  env_id: string;
  layer: string;
  phase: string;
  engine: string;
  rule_id: string;
  severity: string;
  resource: string;
  evidence: string | null;
  recommendation: string | null;
};

export type ScanQueued = {
  scan_id: string;
  task_id: string;
  status: string;
};

export type ScanStatus = {
  id: string;
  template_version_id: string;
  env_id: string;
  status: string;
  task_id: string | null;
  error_message: string | null;
  findings_count: number;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
};

export type RiskAssessment = {
  id: string;
  env_id: string;
  score: number;
  risk_class: string;
  factors: RiskFactor[];
  top_factors: RiskFactor[];
  recommendations: string[];
  timestamp: string;
};

export type RiskFactor = {
  key: string;
  label: string;
  weight: number;
  contribution: number;
  impact: string;
  recommendation: string;
  findings: string[];
};

export type ReportCreated = {
  report_id: string;
  env_id: string;
  download_url: string;
};

export type PostDeploymentScanQueued = {
  status: string;
  task_id: string;
  env_id: string;
};
