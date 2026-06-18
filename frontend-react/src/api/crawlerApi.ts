import { apiRequest } from "./client";

export interface HealthResponse {
  status?: string;
  timestamp?: string;
  services?: Record<string, string>;
}

export interface RootResponse {
  name?: string;
  version?: string;
  status?: string;
  docs?: string;
  endpoints?: Record<string, string>;
}

export function getApiInfo() {
  return apiRequest<RootResponse>("/");
}

export function getHealth() {
  return apiRequest<HealthResponse>("/api/health");
}
