import { apiRequest } from "./client";

export interface HitlCase {
  case_id: string;
  job_id?: string;
  topic?: string;
  source?: string;
  reason?: string;
  signal_type?: string;
  severity?: string;
  message?: string;
  status?: string;
  created_at?: string;
  updated_at?: string;
  action?: string;
}

export interface HitlCasesResponse {
  timestamp?: string;
  count?: number;
  open_count?: number;
  cases?: HitlCase[];
  warning?: string;
}

export function getHitlCases() {
  return apiRequest<HitlCasesResponse>("/api/hitl/cases");
}
