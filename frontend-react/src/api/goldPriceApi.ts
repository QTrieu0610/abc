import { apiRequest, buildQuery } from "./client";

export interface SourcePayload {
  status?: string;
  results?: unknown[];
  error?: string | null;
}

export interface GoldPricesResponse {
  timestamp?: string;
  sjc?: SourcePayload;
  doji?: SourcePayload;
  pnj?: SourcePayload;
}

export interface AvailableDatesResponse {
  dates?: string[];
  count?: number;
}

export interface TrendsResponse {
  period?: string;
  days?: number;
  trends?: {
    dates?: string[];
    buy_prices?: number[];
    sell_prices?: number[];
  };
  moving_average?: unknown;
}

export interface SourceMomentumResponse {
  scope?: string;
  compare?: string;
  items?: unknown[];
  summary?: {
    sources_up?: number;
    sources_down?: number;
    unchanged?: number;
    missing_comparison?: number;
    total?: number;
  };
}

export function getCurrentGoldPrices() {
  return apiRequest<GoldPricesResponse>("/api/current-prices?save_to_csv=false");
}

export function getGoldPricesByDate(date: string) {
  return apiRequest<GoldPricesResponse>(`/api/prices-by-date${buildQuery({ date })}`);
}

export function getAvailableGoldDates() {
  return apiRequest<AvailableDatesResponse>("/api/available-dates");
}

export function getGoldTrends(params: {
  company: string;
  period?: string;
  gold_type?: string;
  location?: string;
}) {
  return apiRequest<TrendsResponse>(`/api/analytics/trends${buildQuery(params)}`);
}

export function getSourceMomentum(scope = "main") {
  return apiRequest<SourceMomentumResponse>(
    `/api/analytics/source-momentum${buildQuery({ scope, compare: "previous" })}`
  );
}

export function updateHistoricalGoldData() {
  return apiRequest<unknown>("/api/update-historical-data", { method: "POST" });
}
