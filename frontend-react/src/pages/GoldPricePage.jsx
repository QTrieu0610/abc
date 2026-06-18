import { useCallback, useEffect, useMemo, useState } from "react";
import { ShieldCheck } from "lucide-react";
import {
  getAvailableGoldDates,
  getCurrentGoldPrices,
  getGoldPricesByDate,
  getGoldTrends,
} from "../api/goldPriceApi";
import PriceTrendChart from "../components/charts/PriceTrendChart";
import DatePicker from "../components/common/DatePicker";
import EmptyState from "../components/common/EmptyState";
import ErrorState from "../components/common/ErrorState";
import LoadingState from "../components/common/LoadingState";
import RefreshButton from "../components/common/RefreshButton";
import GoldPriceCard from "../components/gold-price/GoldPriceCard";
import GoldPriceTable from "../components/gold-price/GoldPriceTable";
import GoldSummaryCard from "../components/gold-price/GoldSummaryCard";
import { useAutoRefresh } from "../hooks/useAutoRefresh";
import { formatVNDWithUnit, toInputDate } from "../utils/format";
import { getSourceStatuses, normalizeGoldPriceResponse } from "../utils/goldMapper";

function findCompanyRecord(records, company) {
  const upper = company.toUpperCase();
  const sourceRecords = records.filter((record) => record.company?.toUpperCase() === upper);
  return (
    sourceRecords.find((record) => record.goldType?.toLowerCase().includes("sjc 1l")) ||
    sourceRecords.find((record) => record.goldType?.toLowerCase().includes("sjc")) ||
    sourceRecords[0] ||
    null
  );
}

function buildFeedCards(records, statuses) {
  const preferred = [
    {
      company: "SJC",
      label: "WEBGIA/SJC FEED",
      title: "SJC Reference Price",
      record: findCompanyRecord(records, "SJC"),
      status: statuses.sjc,
    },
    {
      company: "DOJI",
      label: "OFFICIAL DOJI FEED",
      title: "DOJI Market Price",
      record: findCompanyRecord(records, "DOJI"),
      status: statuses.doji,
    },
    {
      company: "PNJ",
      label: "OFFICIAL PNJ FEED",
      title: "PNJ Retail Price",
      record: findCompanyRecord(records, "PNJ"),
      status: statuses.pnj,
    },
  ];

  if (preferred.some((card) => card.record)) return preferred;

  return [0, 1, 2].map((index) => ({
    company: records[index]?.company || "Unknown",
    label: records[index]?.source || "BACKEND FEED",
    title: records[index] ? `${records[index].company} Price` : "No data available",
    record: records[index] || null,
    status: records[index] ? "ok" : "empty",
  }));
}

function buildSummary(records) {
  const priced = records.filter((record) => record.buy !== null || record.sell !== null);
  const withBuy = priced.filter((record) => record.buy !== null);
  const withSell = priced.filter((record) => record.sell !== null);
  const withSpread = priced.filter((record) => record.spread !== null && record.spread !== undefined);
  const sjc = findCompanyRecord(records, "SJC");
  const doji = findCompanyRecord(records, "DOJI");
  const pnj = findCompanyRecord(records, "PNJ");

  const bestBuy = withBuy.reduce((best, record) => (!best || record.buy > best.buy ? record : best), null);
  const bestSell = withSell.reduce((best, record) => (!best || record.sell > best.sell ? record : best), null);
  const lowestSpread = withSpread.reduce(
    (best, record) => (!best || record.spread < best.spread ? record : best),
    null
  );

  const gap = (left, right) => {
    if (!left || !right || left.sell === null || right.sell === null) return null;
    return left.sell - right.sell;
  };

  const describe = (record) =>
    record ? `${record.company} - ${record.region || "N/A"} - ${record.goldType || "N/A"}` : "Insufficient data";

  const sjcDojiGap = gap(sjc, doji);
  const sjcPnjGap = gap(sjc, pnj);

  return [
    {
      label: "Best Buy",
      value: bestBuy ? formatVNDWithUnit(bestBuy.buy) : "N/A",
      detail: describe(bestBuy),
      tone: "green",
    },
    {
      label: "Best Sell",
      value: bestSell ? formatVNDWithUnit(bestSell.sell) : "N/A",
      detail: describe(bestSell),
      tone: "green",
    },
    {
      label: "Lowest Spread",
      value: lowestSpread ? formatVNDWithUnit(lowestSpread.spread) : "N/A",
      detail: describe(lowestSpread),
      tone: "cyan",
    },
    {
      label: "SJC vs DOJI Gap",
      value: sjcDojiGap === null ? "N/A" : formatVNDWithUnit(sjcDojiGap),
      detail: doji ? describe(doji) : "Insufficient data",
      tone: "cyan",
    },
    {
      label: "SJC vs PNJ Gap",
      value: sjcPnjGap === null ? "N/A" : formatVNDWithUnit(sjcPnjGap),
      detail: pnj ? describe(pnj) : "Insufficient data",
      tone: "cyan",
    },
  ];
}

export default function GoldPricePage() {
  const [selectedDate, setSelectedDate] = useState("");
  const [availableDates, setAvailableDates] = useState([]);
  const [datesError, setDatesError] = useState(null);
  const [trends, setTrends] = useState(null);

  useEffect(() => {
    let cancelled = false;
    getAvailableGoldDates()
      .then((result) => {
        if (cancelled) return;
        const dates = Array.isArray(result?.dates) ? result.dates : [];
        setAvailableDates(dates);
        if (dates[0]) setSelectedDate(dates[0]);
      })
      .catch((error) => setDatesError(error));

    getGoldTrends({
      company: "SJC",
      period: "monthly",
      gold_type: "SJC 1L",
      location: "National",
    })
      .then((result) => {
        if (!cancelled) setTrends(result);
      })
      .catch(() => {
        if (!cancelled) setTrends(null);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const fetchGold = useCallback(() => {
    return selectedDate ? getGoldPricesByDate(selectedDate) : getCurrentGoldPrices();
  }, [selectedDate]);

  const { data, loading, refreshing, error, refresh } = useAutoRefresh(fetchGold, 30000);
  const records = useMemo(() => normalizeGoldPriceResponse(data), [data]);
  const statuses = useMemo(() => getSourceStatuses(data), [data]);
  const feedCards = useMemo(() => buildFeedCards(records, statuses), [records, statuses]);
  const summary = useMemo(() => buildSummary(records), [records]);
  const maxDate = availableDates[0] || toInputDate();

  return (
    <div className="space-y-5">
      <div className="rounded-lg border border-line bg-panel p-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <ShieldCheck className="h-4 w-4 text-cyan" aria-hidden="true" />
            <h2 className="text-sm font-bold text-white">View SJC + DOJI + PNJ Prices By Date</h2>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <DatePicker
              value={selectedDate}
              onChange={setSelectedDate}
              max={maxDate}
              disabled={refreshing}
            />
            <RefreshButton onClick={refresh} refreshing={refreshing} />
          </div>
        </div>
        {datesError && (
          <p className="mt-3 text-xs text-amber-300">
            Available date endpoint returned an error. The dashboard can still request current prices.
          </p>
        )}
      </div>

      {loading ? (
        <LoadingState title="Loading gold price data..." />
      ) : error ? (
        <ErrorState error={error} onRetry={refresh} />
      ) : (
        <>
          <div className="grid gap-4 xl:grid-cols-3">
            {feedCards.map((card) => (
              <GoldPriceCard
                key={`${card.company}-${card.title}`}
                label={card.label}
                title={card.title}
                record={card.record}
                status={card.status}
              />
            ))}
          </div>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
            {summary.map((item) => (
              <GoldSummaryCard key={item.label} {...item} />
            ))}
          </div>

          {records.length ? (
            <GoldPriceTable records={records} />
          ) : (
            <EmptyState title="No gold price data available." message="Run crawler first or choose another available date." />
          )}

          <PriceTrendChart trends={trends} />
        </>
      )}
    </div>
  );
}
