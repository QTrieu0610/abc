import { apiRequest, buildQuery } from "./client";

export const extractedDataTopics = [
  "gold-price",
  "house-price",
  "stock-price",
  "crypto-price",
  "forex-rate",
  "commodity-price",
];

export interface HousePriceListing {
  datetime?: number;
  source?: string;
  property_type?: string;
  title?: string;
  price?: number | null;
  price_text?: string | null;
  area_m2?: number | null;
  area_text?: string | null;
  price_per_m2?: number | null;
  location?: string | null;
  url?: string | null;
}

export interface HousePriceSourcePayload {
  status?: string;
  results?: HousePriceListing[];
  error?: string | null;
}

export interface HousePricesResponse {
  timestamp?: string;
  topic?: string;
  saved_records?: number;
  data_file?: string;
  batdongsan?: HousePriceSourcePayload;
  alonhadat?: HousePriceSourcePayload;
}

export function getHousePrices(
  params: { max_pages?: number; use_browser_fallback?: boolean; save_to_csv?: boolean } = {}
) {
  return apiRequest<HousePricesResponse>(
    `/api/house-prices${buildQuery({
      max_pages: params.max_pages ?? 1,
      use_browser_fallback: params.use_browser_fallback ?? true,
      save_to_csv: params.save_to_csv ?? true,
    })}`
  );
}
