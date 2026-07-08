export type Project = {
  id: number;
  project_name: string;
  company_name: string;
  industry: string;
  audit_objective: string;
  audit_period: string;
  focus_areas: string;
  file_count?: number;
  checklist_count?: number;
  updated_at: string;
};

export type ModelConfig = {
  id: number;
  config_name: string;
  config_type: "chat" | "embedding";
  provider: string;
  base_url: string;
  api_key: string;
  model: string;
  temperature: number;
  max_tokens: number;
  embedding_dimension?: number;
  embedding_batch_size: number;
  timeout_seconds: number;
  is_default: number;
};

export type AuditFile = {
  id: number;
  project_id: number;
  original_name: string;
  file_type: string;
  file_size: number;
  parse_status: string;
  parse_error?: string;
  created_at: string;
};

export type ChecklistItem = {
  id: number;
  question_id: string;
  module: string;
  interview_role: string;
  interview_question: string;
  expected_answer: string;
  source_file: string;
  source_location: string;
  evidence_quote: string;
  confidence: string;
  follow_up_question: string;
  risk_hint: string;
};

export type MissingPolicyItem = {
  id: number;
  module: string;
  issue: string;
  risk: string;
  suggested_interview_question: string;
  suggested_policy_improvement: string;
};

export type TaskLog = {
  id: number;
  task_type: string;
  status: string;
  message: string;
  progress_current: number;
  progress_total: number;
  progress_percent: number;
  created_at: string;
};
