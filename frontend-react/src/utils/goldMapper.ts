import type { GoldPriceRecord } from "../types/gold";
import type { GoldPricesResponse, SourcePayload } from "../api/goldPriceApi";

function toNumber(value: unknown): number | null {
  const numeric = Number(value);
  return Number.isFinite(numeric) && numeric > 0 ? numeric : null;
}

export function mapBackendGoldRecord(raw: any): GoldPriceRecord {
  const buy = toNumber(raw.buy ?? raw.buy_price ?? raw.buyPrice ?? raw.mua);
  const sell = toNumber(raw.sell ?? raw.sell_price ?? raw.sellPrice ?? raw.ban);

  return {
    company:
      raw.company ??
      raw.brand ??
      raw.source_name ??
      raw.source ??
      "Unknown",
    region: raw.region ?? raw.location ?? raw.area ?? "N/A",
    goldType:
      raw.gold_type ??
      raw.goldType ??
      raw.type ??
      raw.product_name ??
      "N/A",
    buy,
    sell,
    spread:
      raw.spread !== undefined
        ? toNumber(raw.spread)
        : buy !== null && sell !== null
          ? sell - buy
          : null,
    timestamp: raw.timestamp ?? raw.date ?? raw.created_at ?? raw.updated_at,
    source: raw.source ?? raw.url ?? raw.website,
  };
}

function expandFlatRecord(raw: any, companyName: string, timestamp?: string): GoldPriceRecord[] {
  const buyKeys = Object.keys(raw || {}).filter(k => k.startsWith("buy_"));
  const records: GoldPriceRecord[] = [];
  
  // Custom display mapping for SJC types to keep existing visuals clean
  const sjcDisplayNames: Record<string, string> = {
    "1l": "SJC 1L",
    "nhan1c": "SJC Ring 1C",
    "nutrang_9999": "SJC Jewelry 24K",
    "nutrang_99": "SJC Jewelry 99%",
    "nutrang_75": "SJC Jewelry 18K",
  };

  for (const buyKey of buyKeys) {
    const suffix = buyKey.substring(4);
    const sellKey = `sell_${suffix}`;
    const buy = toNumber(raw[buyKey]);
    const sell = toNumber(raw[sellKey]);
    
    if (buy !== null || sell !== null) {
      const typeDisplay = sjcDisplayNames[suffix] || suffix.toUpperCase();
      records.push({
        company: companyName.toUpperCase() === "SJC" ? "SJC" : companyName.toUpperCase(),
        region: "National",
        goldType: typeDisplay,
        buy,
        sell,
        spread: buy !== null && sell !== null ? sell - buy : null,
        timestamp: raw.timestamp ?? timestamp,
        source: companyName.toUpperCase(),
      });
    }
  }
  return records;
}

function mapSourceRecords(
  sourceKey: string,
  source?: SourcePayload,
  timestamp?: string
): GoldPriceRecord[] {
  const records = Array.isArray(source?.results) ? source.results : [];

  // Dynamic flat keys detection
  const hasFlatKeys = records.some(r => r && typeof r === "object" && Object.keys(r).some(k => k.startsWith("buy_")));

  if (hasFlatKeys) {
    return records.flatMap((record) => expandFlatRecord(record, sourceKey, timestamp));
  }

  return records.map((record: any) => ({
    ...mapBackendGoldRecord({
      ...record,
      company: record.company ?? sourceKey.toUpperCase(),
      timestamp: record.timestamp ?? timestamp,
      source: record.source ?? sourceKey.toUpperCase(),
    }),
  }));
}

export function normalizeGoldPriceResponse(data?: GoldPricesResponse): GoldPriceRecord[] {
  if (!data || typeof data !== "object") return [];
  const records: GoldPriceRecord[] = [];
  for (const [key, payload] of Object.entries(data)) {
    if (key === 'timestamp' || key === 'error') continue;
    records.push(...mapSourceRecords(key as any, payload as SourcePayload, data.timestamp));
  }
  return records;
}

export function getSourceStatuses(data?: any) {
  const statuses: Record<string, string> = {};
  if (!data) return statuses;
  for (const [key, payload] of Object.entries(data)) {
    if (key === 'timestamp' || key === 'error') continue;
    statuses[key] = (payload as SourcePayload)?.status || "empty";
  }
  return statuses;
}
