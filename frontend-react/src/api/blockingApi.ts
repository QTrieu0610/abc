import { apiRequest } from "./client";

export interface BlockingSignal {
  signal_id?: string;
  job_id?: string;
  topic?: string;
  source?: string;
  signal_type?: string;
  reason?: string;
  severity?: string;
  status?: string;
  message?: string;
  action?: string;
  created_at?: string;
  updated_at?: string;
}

export interface BlockingSignalsResponse {
  timestamp?: string;
  count?: number;
  open_count?: number;
  signals?: BlockingSignal[];
}

export function getBlockingSignals() {
  return apiRequest<BlockingSignalsResponse>("/api/blocking-signals");
}
