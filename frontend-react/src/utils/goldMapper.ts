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

function expandSjcRecord(raw: any, timestamp?: string): GoldPriceRecord[] {
  const definitions = [
    ["buy_1l", "sell_1l", "SJC 1L"],
    ["buy_nhan1c", "sell_nhan1c", "SJC Ring 1C"],
    ["buy_nutrang_9999", "sell_nutrang_9999", "SJC Jewelry 24K"],
    ["buy_nutrang_99", "sell_nutrang_99", "SJC Jewelry 99%"],
    ["buy_nutrang_75", "sell_nutrang_75", "SJC Jewelry 18K"],
  ];

  return definitions
    .map(([buyKey, sellKey, goldType]) => {
      const buy = toNumber(raw[buyKey]);
      const sell = toNumber(raw[sellKey]);
      if (buy === null && sell === null) return null;
      return {
        company: "SJC",
        region: "National",
        goldType,
        buy,
        sell,
        spread: buy !== null && sell !== null ? sell - buy : null,
        timestamp: raw.timestamp ?? timestamp,
        source: "WEBGIA/SJC",
      };
    })
    .filter(Boolean) as GoldPriceRecord[];
}

function mapSourceRecords(
  sourceKey: "sjc" | "doji" | "pnj",
  source?: SourcePayload,
  timestamp?: string
): GoldPriceRecord[] {
  const records = Array.isArray(source?.results) ? source.results : [];

  if (sourceKey === "sjc") {
    return records.flatMap((record) => expandSjcRecord(record, timestamp));
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
  return [
    ...mapSourceRecords("sjc", data.sjc, data.timestamp),
    ...mapSourceRecords("doji", data.doji, data.timestamp),
    ...mapSourceRecords("pnj", data.pnj, data.timestamp),
  ];
}

export function getSourceStatuses(data?: GoldPricesResponse) {
  return {
    sjc: data?.sjc?.status || "empty",
    doji: data?.doji?.status || "empty",
    pnj: data?.pnj?.status || "empty",
  };
}
