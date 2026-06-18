import { apiRequest } from "./client";

export interface SessionRecord {
  session_name?: string;
  source?: string;
  topic?: string;
  login_status?: string;
  last_used?: string;
  mfa_required?: string;
  session_file?: string;
  status?: string;
  cookie_count?: number;
  origin_count?: number;
  domains?: string[];
  message?: string;
}

export interface SessionsResponse {
  timestamp?: string;
  count?: number;
  sessions?: SessionRecord[];
  security?: string;
}

export function getSessions() {
  return apiRequest<SessionsResponse>("/api/sessions");
}
