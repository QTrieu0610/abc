export interface GoldPriceRecord {
  company: string;
  region?: string;
  goldType: string;
  buy: number | null;
  sell: number | null;
  spread?: number | null;
  timestamp?: string;
  source?: string;
}

export interface GoldSummaryItem {
  label: string;
  value: string;
  detail?: string;
  tone?: "green" | "cyan" | "amber" | "red" | "muted";
}
