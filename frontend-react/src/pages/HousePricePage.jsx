import { useCallback, useMemo, useState } from "react";
import { Building2, Database, Gauge, Home, SquareStack } from "lucide-react";
import { getHousePrices } from "../api/extractedDataApi";
import EmptyState from "../components/common/EmptyState";
import ErrorState from "../components/common/ErrorState";
import LoadingState from "../components/common/LoadingState";
import MetricCard from "../components/common/MetricCard";
import RefreshButton from "../components/common/RefreshButton";
import CustomCrawlerForm from "../components/common/CustomCrawlerForm";
import DataTable from "../components/tables/DataTable";
import { useAutoRefresh } from "../hooks/useAutoRefresh";
import { formatDateTime, formatVNDWithUnit } from "../utils/format";

function flattenListings(data) {
  if (!data || typeof data !== "object") return [];
  const rows = [];
  for (const [sourceKey, payload] of Object.entries(data)) {
    if (sourceKey === "timestamp" || sourceKey === "error") continue;
    const records = Array.isArray(payload?.results) ? payload.results : [];
    records.forEach((row, index) => {
      rows.push({
        id: `${sourceKey}-${row.url || row.title || index}`,
        sourceKey,
        sourceStatus: payload?.status || "unknown",
        ...row,
      });
    });
  }
  return rows;
}

function median(values) {
  const numbers = values.filter((value) => Number.isFinite(Number(value))).map(Number).sort((a, b) => a - b);
  if (!numbers.length) return null;
  const middle = Math.floor(numbers.length / 2);
  return numbers.length % 2 ? numbers[middle] : (numbers[middle - 1] + numbers[middle]) / 2;
}

function buildSummary(records, data) {
  const sourcePayloads = data && typeof data === "object" ? Object.entries(data).filter(([key]) => key !== "timestamp" && key !== "error").map(([_, p]) => p) : [];
  const healthySources = sourcePayloads.filter((payload) => payload?.status === "ok").length;
  const priced = records.filter((record) => record.price);
  const withArea = records.filter((record) => record.area_m2);
  const medianPrice = median(priced.map((record) => record.price));
  const medianPricePerM2 = median(records.map((record) => record.price_per_m2));

  return [
    {
      label: "Listings",
      value: records.length,
      detail: "Current parsed records",
      icon: Database,
    },
    {
      label: "Sources OK",
      value: `${healthySources}/${sourcePayloads.length || 2}`,
      detail: "Crawler source status",
      icon: Gauge,
    },
    {
      label: "Median Price",
      value: formatVNDWithUnit(medianPrice),
      detail: `${priced.length} listings with price`,
      icon: Home,
    },
    {
      label: "Median / m2",
      value: formatVNDWithUnit(medianPricePerM2),
      detail: `${withArea.length} listings with area`,
      icon: SquareStack,
    },
  ];
}

function sourceMessage(data) {
  const failed = ["batdongsan", "alonhadat"]
    .map((key) => ({ key, payload: data?.[key] }))
    .filter(({ payload }) => payload && payload.status !== "ok" && payload.error);

  if (!failed.length) return null;
  return failed.map(({ key, payload }) => `${key}: ${payload.error}`).join(" | ");
}

export default function HousePricePage() {
  const [browserFallback, setBrowserFallback] = useState(true);
  const [maxPages, setMaxPages] = useState(1);

  const fetchHousePrices = useCallback(
    (isUserAction) => getHousePrices(isUserAction, { max_pages: maxPages, use_browser_fallback: browserFallback }),
    [browserFallback, maxPages]
  );

  const { data, loading, refreshing, error, refresh } = useAutoRefresh(fetchHousePrices, 60000);
  const records = useMemo(() => flattenListings(data), [data]);
  const summary = useMemo(() => buildSummary(records, data), [records, data]);
  const warning = sourceMessage(data);

  const columns = [
    {
      key: "title",
      header: "Listing",
      render: (row) => (
        <div className="max-w-xl">
          {row.url ? (
            <a className="font-semibold text-sky-100 hover:text-cyan" href={row.url} target="_blank" rel="noreferrer">
              {row.title || "Untitled listing"}
            </a>
          ) : (
            <span className="font-semibold text-sky-100">{row.title || "Untitled listing"}</span>
          )}
          <div className="mt-1 text-xs text-muted">{row.location || "Location unavailable"}</div>
        </div>
      ),
    },
    {
      key: "source",
      header: "Source",
      render: (row) => row.source || row.sourceKey,
    },
    {
      key: "price",
      header: "Price",
      align: "right",
      render: (row) => row.price ? formatVNDWithUnit(row.price) : row.price_text || "N/A",
    },
    {
      key: "area_m2",
      header: "Area",
      align: "right",
      render: (row) => row.area_m2 ? `${row.area_m2} m2` : row.area_text || "N/A",
    },
    {
      key: "price_per_m2",
      header: "VND / m2",
      align: "right",
      render: (row) => formatVNDWithUnit(row.price_per_m2),
    },
  ];

  return (
    <div className="space-y-5">
      <CustomCrawlerForm type="real_estate" placeholder="Enter URL to extract real estate listings (e.g., https://alonhadat.com.vn/...)" />

      <div className="rounded-lg border border-line bg-panel p-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-center gap-3">
            <Building2 className="h-4 w-4 text-cyan" aria-hidden="true" />
            <h2 className="text-sm font-bold text-white">Current House Price Listings</h2>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={maxPages}
              onChange={(event) => setMaxPages(Number(event.target.value))}
              className="h-10 rounded-md border border-line bg-panelSoft px-3 text-sm font-semibold text-sky-100"
            >
              <option value={1}>1 page</option>
              <option value={2}>2 pages</option>
              <option value={3}>3 pages</option>
            </select>
            <label className="inline-flex h-10 items-center gap-2 rounded-md border border-line bg-panelSoft px-3 text-sm font-semibold text-sky-100">
              <input
                type="checkbox"
                checked={browserFallback}
                onChange={(event) => setBrowserFallback(event.target.checked)}
                className="h-4 w-4 accent-cyan"
              />
              Browser fallback
            </label>
            <RefreshButton onClick={refresh} refreshing={refreshing} />
          </div>
        </div>
        {warning && <p className="mt-3 text-xs text-amber-300">{warning}</p>}
      </div>

      {loading ? (
        <LoadingState title="Loading house price data..." />
      ) : error ? (
        <ErrorState error={error} onRetry={refresh} />
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {summary.map((item) => (
              <MetricCard key={item.label} {...item} />
            ))}
          </div>

          {records.length ? (
            <DataTable columns={columns} rows={records} maxHeight="560px" />
          ) : (
            <EmptyState title="No house price data available." message="Refresh the topic or enable browser fallback." />
          )}

          <p className="text-xs text-muted">Last update: {formatDateTime(data?.timestamp)}</p>
        </>
      )}
    </div>
  );
}
