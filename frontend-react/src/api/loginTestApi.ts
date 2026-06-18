import { apiRequest, buildQuery } from "./client";

export interface LoginTestPayload {
  target_type: "demo" | "github" | "custom";
  target_url?: string;
  username: string;
  password: string;
  profile_name?: string;
}

export interface LoginTestJob {
  job_id: string;
  status?: string;
  target_type?: string;
  target_label?: string;
  target_url?: string;
  profile_name?: string;
  created_at?: string;
  started_at?: string;
  ended_at?: string;
  html_length?: number;
  output_file?: string;
  latest_signal?: string;
  log_count?: number;
  username_provided?: boolean;
}

export interface LoginTestLog {
  timestamp?: string;
  level?: string;
  message?: string;
  signal_type?: string;
}

export interface LoginTestsResponse {
  timestamp?: string;
  count?: number;
  jobs?: LoginTestJob[];
}

export interface LoginTestLogsResponse {
  job_id?: string;
  count?: number;
  logs?: LoginTestLog[];
}

export function startLoginTest(payload: LoginTestPayload) {
  return apiRequest<LoginTestJob>("/api/login-tests", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getLoginTests() {
  return apiRequest<LoginTestsResponse>("/api/login-tests");
}

export function getLoginTest(jobId: string) {
  return apiRequest<LoginTestJob>(`/api/login-tests/${jobId}`);
}

export function getLoginTestLogs(jobId: string) {
  return apiRequest<LoginTestLogsResponse>(`/api/login-tests/${jobId}/logs${buildQuery({})}`);
}
