import {
  Activity,
  Bell,
  CalendarClock,
  Database,
  Gauge,
  LineChart,
  RadioTower,
  Server,
  ShieldAlert,
  TimerReset,
  UserCheck,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { getCrawlJobs } from "../api/crawlJobApi";
import { getHealth } from "../api/crawlerApi";
import { getBlockingSignals } from "../api/blockingApi";
import { getHousePrices } from "../api/extractedDataApi";
import {
  getAvailableGoldDates,
  getCurrentGoldPrices,
  getGoldTrends,
  getSourceMomentum,
} from "../api/goldPriceApi";
import { getHitlCases } from "../api/hitlApi";
import { getLoginTests } from "../api/loginTestApi";
import { getSessions } from "../api/sessionApi";
import PriceTrendChart from "../components/charts/PriceTrendChart";
import EmptyState from "../components/common/EmptyState";
import ErrorState from "../components/common/ErrorState";
import LoadingState from "../components/common/LoadingState";
import MetricCard from "../components/common/MetricCard";
import RefreshButton from "../components/common/RefreshButton";
import StatusBadge from "../components/common/StatusBadge";
import DataTable from "../components/tables/DataTable";
import { useAutoRefresh } from "../hooks/useAutoRefresh";
import { formatDateTime, formatVNDWithUnit } from "../utils/format";
import { getSourceStatuses, normalizeGoldPriceResponse } from "../utils/goldMapper";

async function settle(name, promise) {
  try {
    return { name, status: "fulfilled", value: await promise };
  } catch (error) {
    return { name, status: "rejected", reason: error };
  }
}

function Panel({ title, action, children, className = "" }) {
  return (
    <section className={`overflow-hidden rounded-lg border border-line bg-panel shadow-glow ${className}`}>
      <div className="flex min-h-14 items-center justify-between border-b border-line px-4">
        <h2 className="text-sm font-bold text-white">{title}</h2>
        {action}
      </div>
      <div className="p-4">{children}</div>
    </section>
  );
}

function CompactMetric({ label, value, detail, icon: Icon, status }) {
  return (
    <MetricCard
      label={label}
      value={value}
      detail={detail}
      icon={Icon}
      status={status}
    />
  );
}

function SourceStatusPanel({ sourceRows }) {
  const total = sourceRows.length;
  const ok = sourceRows.filter((row) => row.status === "ok").length;
  const failed = sourceRows.filter((row) => row.status === "failed").length;
  const empty = sourceRows.filter((row) => row.status === "empty").length;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-5">
        <div className="relative flex h-28 w-28 shrink-0 items-center justify-center rounded-full border-[14px] border-sky-500/20">
          <div className="absolute inset-[-14px] rounded-full border-[14px] border-t-emerald-400 border-r-cyan border-b-amber-400/50 border-l-red-400/40" />
          <div className="text-center">
            <div className="text-2xl font-bold text-white">{total}</div>
            <div className="text-[10px] uppercase text-muted">sources</div>
          </div>
        </div>
        <div className="min-w-0 flex-1 space-y-2 text-sm">
          <div className="flex justify-between gap-3 text-sky-100">
            <span>OK</span>
            <span className="font-semibold text-emerald-300">{ok}</span>
          </div>
          <div className="flex justify-between gap-3 text-sky-100">
            <span>Empty</span>
            <span className="font-semibold text-amber-300">{empty}</span>
          </div>
          <div className="flex justify-between gap-3 text-sky-100">
            <span>Failed</span>
            <span className="font-semibold text-red-300">{failed}</span>
          </div>
        </div>
      </div>
      <div className="grid gap-2">
        {sourceRows.map((row) => (
          <div key={row.id} className="flex items-center justify-between rounded-md border border-line bg-panelSoft px-3 py-2">
            <span className="text-xs font-semibold text-sky-100">{row.source}</span>
            <StatusBadge status={row.status} />
          </div>
        ))}
      </div>
    </div>
  );
}

function MomentumMiniPanel({ momentum }) {
  const summary = momentum?.summary || {};
  const total = summary.total ?? 0;

  return (
    <div className="space-y-4">
      <div className="flex items-end justify-between">
        <div>
          <div className="text-3xl font-bold text-white">{total}</div>
          <div className="text-xs uppercase text-muted">tracked sources</div>
        </div>
        <div className="text-right text-xs font-semibold text-emerald-300">
          {summary.sources_up ?? 0} up
        </div>
      </div>
      <div className="space-y-3">
        <div className="flex items-center justify-between text-sm text-sky-100">
          <span>Sources down</span>
          <span className="font-bold text-red-300">{summary.sources_down ?? 0}</span>
        </div>
        <div className="flex items-center justify-between text-sm text-sky-100">
          <span>Unchanged</span>
          <span className="font-bold text-slate-300">{summary.unchanged ?? 0}</span>
        </div>
        <div className="flex items-center justify-between text-sm text-sky-100">
          <span>No previous row</span>
          <span className="font-bold text-amber-300">{summary.missing_comparison ?? 0}</span>
        </div>
      </div>
    </div>
  );
}

function NotConnectedCard({ title, message }) {
  return (
    <EmptyState title={title} message={message} />
  );
}

function normalizeHousePriceResponse(data) {
  const sources = ["batdongsan", "alonhadat"];
  return sources.flatMap((source) => {
    const payload = data?.[source];
    const rows = Array.isArray(payload?.results) ? payload.results : [];
    return rows.map((row, index) => ({
      id: `${source}-${row.url || row.title || index}`,
      source,
      title: row.title || "Untitled listing",
      price: row.price ?? null,
      priceText: row.price_text || null,
      areaM2: row.area_m2 ?? null,
      pricePerM2: row.price_per_m2 ?? null,
      location: row.location || "N/A",
      url: row.url || null,
    }));
  });
}

function getHouseSourceStatuses(data) {
  return {
    batdongsan: data?.batdongsan?.status || "empty",
    alonhadat: data?.alonhadat?.status || "empty",
  };
}

function hasCloudflareChallenge(payload) {
  return ["batdongsan", "alonhadat"].some((source) => {
    const message = String(payload?.[source]?.error || payload?.[source]?.message || "").toLowerCase();
    return message.includes("cloudflare") || message.includes("challenge");
  });
}

function median(values) {
  const numbers = values.filter((value) => Number.isFinite(Number(value))).map(Number).sort((a, b) => a - b);
  if (!numbers.length) return null;
  const middle = Math.floor(numbers.length / 2);
  return numbers.length % 2 ? numbers[middle] : (numbers[middle - 1] + numbers[middle]) / 2;
}

const topicOptions = [
  { value: "gold-price", label: "Gold Price" },
  { value: "house-price", label: "House Price" },
];

export default function OverviewPage() {
  const [selectedTopic, setSelectedTopic] = useState("gold-price");

  const fetchOverview = useCallback(async () => {
    if (selectedTopic === "house-price") {
      const housePricesResult = await settle("housePrices", getHousePrices({ max_pages: 1, use_browser_fallback: true }));
      const results = await Promise.all([
        settle("health", getHealth()),
        housePricesResult,
        settle("availableDates", Promise.resolve(null)),
        settle("trends", Promise.resolve(null)),
        settle("sourceMomentum", Promise.resolve(null)),
        settle("hitlCases", getHitlCases()),
        settle("blockingSignals", getBlockingSignals()),
        settle("loginTests", getLoginTests()),
        settle("crawlJobs", getCrawlJobs(false)),
        settle("sessions", getSessions()),
      ]);

      return Object.fromEntries(results.map((result) => [result.name, result]));
    }

    const topicRequests =
      [
        settle("currentPrices", getCurrentGoldPrices()),
        settle("availableDates", getAvailableGoldDates()),
        settle(
          "trends",
          getGoldTrends({
            company: "SJC",
            period: "monthly",
            gold_type: "SJC 1L",
            location: "National",
          })
        ),
        settle("sourceMomentum", getSourceMomentum("main")),
      ];

    const results = await Promise.all([
      settle("health", getHealth()),
      ...topicRequests,
      settle("hitlCases", getHitlCases()),
      settle("blockingSignals", getBlockingSignals()),
      settle("loginTests", getLoginTests()),
      settle("crawlJobs", getCrawlJobs(false)),
      settle("sessions", getSessions()),
    ]);

    return Object.fromEntries(results.map((result) => [result.name, result]));
  }, [selectedTopic]);

  const { data, loading, refreshing, error, refresh } = useAutoRefresh(
    fetchOverview,
    selectedTopic === "house-price" ? 0 : 10000,
    selectedTopic !== "house-price"
  );
  const health = data?.health?.status === "fulfilled" ? data.health.value : null;
  const currentPrices = data?.currentPrices?.status === "fulfilled" ? data.currentPrices.value : null;
  const housePrices = data?.housePrices?.status === "fulfilled" ? data.housePrices.value : null;
  const availableDates = data?.availableDates?.status === "fulfilled" ? data.availableDates.value : null;
  const trends = data?.trends?.status === "fulfilled" ? data.trends.value : null;
  const sourceMomentum =
    data?.sourceMomentum?.status === "fulfilled" ? data.sourceMomentum.value : null;
  const hitlCases = data?.hitlCases?.status === "fulfilled" ? data.hitlCases.value : null;
  const blockingSignals = data?.blockingSignals?.status === "fulfilled" ? data.blockingSignals.value : null;
  const loginTests = data?.loginTests?.status === "fulfilled" ? data.loginTests.value : null;
  const crawlJobs = data?.crawlJobs?.status === "fulfilled" ? data.crawlJobs.value : null;
  const sessions = data?.sessions?.status === "fulfilled" ? data.sessions.value : null;
  const isHouseTopic = selectedTopic === "house-price";
  const selectedTopicLabel = topicOptions.find((topic) => topic.value === selectedTopic)?.label || "Gold Price";
  const topicPayload = isHouseTopic ? housePrices : currentPrices;
  const records = useMemo(
    () => (isHouseTopic ? normalizeHousePriceResponse(housePrices) : normalizeGoldPriceResponse(currentPrices)),
    [currentPrices, housePrices, isHouseTopic]
  );
  const sourceStatuses = useMemo(
    () => (isHouseTopic ? getHouseSourceStatuses(housePrices) : getSourceStatuses(currentPrices)),
    [currentPrices, housePrices, isHouseTopic]
  );
  const caseRows = Array.isArray(hitlCases?.cases) ? hitlCases.cases.slice(0, 4) : [];
  const blockingRows = Array.isArray(blockingSignals?.signals) ? blockingSignals.signals : [];
  const openBlockingRows = blockingRows.filter((signal) => signal.status === "open");
  const houseCloudflareOpen = isHouseTopic && hasCloudflareChallenge(housePrices) && openBlockingRows.length === 0 ? 1 : 0;
  const totalBlockingOpen = openBlockingRows.length + houseCloudflareOpen;
  const totalReviewOpen = Number(hitlCases?.open_count || 0) + totalBlockingOpen;
  const totalReviewCount = Number(hitlCases?.count || 0) + blockingRows.length + houseCloudflareOpen;
  const loginRows = Array.isArray(loginTests?.jobs) ? loginTests.jobs.slice(0, 4) : [];
  const crawlJobRows = Array.isArray(crawlJobs?.jobs) ? crawlJobs.jobs : [];
  const houseMedianPrice = useMemo(() => median(records.map((record) => record.price)), [records]);
  const houseMedianPricePerM2 = useMemo(() => median(records.map((record) => record.pricePerM2)), [records]);

  const sourceRows = Object.entries(sourceStatuses).map(([source, status]) => ({
    id: source,
    source: source.toUpperCase(),
    topic: selectedTopicLabel,
    status,
    message:
      topicPayload?.[source]?.error ||
      (status === "ok" ? "Backend source returned records." : "No source records returned."),
  }));

  const anyEndpointSucceeded = Boolean(
    health || currentPrices || housePrices || availableDates || trends || sourceMomentum || hitlCases || blockingSignals || loginTests || crawlJobs || sessions
  );
  const lastCrawlTime = topicPayload?.timestamp ? formatDateTime(topicPayload.timestamp) : "Not connected";
  const serviceSummary = health?.services
    ? Object.entries(health.services).map(([name, status]) => `${name}: ${status}`).join(" | ")
    : "GET /api/health";

  useEffect(() => {
    if (selectedTopic !== "house-price") {
      refresh();
    }
  }, [refresh, selectedTopic]);

  return (
    <div className="space-y-5 pb-12">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Crawler Operations Center</h1>
          <p className="mt-1 text-sm text-sky-200">
            Authorized crawling, session monitoring, blocking detection, and human review.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={selectedTopic}
            onChange={(event) => setSelectedTopic(event.target.value)}
            className="h-10 rounded-md border border-line bg-panelSoft px-3 text-sm font-semibold text-sky-100 transition hover:border-cyan/40 focus:border-cyan/60 focus:outline-none"
            aria-label="Overview data topic"
          >
            {topicOptions.map((topic) => (
              <option key={topic.value} value={topic.value}>
                {topic.label}
              </option>
            ))}
          </select>
          <RefreshButton onClick={refresh} refreshing={refreshing} />
        </div>
      </div>

      {loading ? (
        <LoadingState title="Loading crawler overview..." />
      ) : error && !anyEndpointSucceeded ? (
        <ErrorState error={error} onRetry={refresh} />
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">
            <CompactMetric
              label="Backend API"
              value={health?.status || "Not connected"}
              detail={serviceSummary}
              icon={Server}
              status={<StatusBadge status={health?.status || "not_connected"} />}
            />
            <CompactMetric
              label="Current Feed"
              value={topicPayload ? "Connected" : "Not connected"}
              detail={lastCrawlTime}
              icon={Activity}
              status={<StatusBadge status={topicPayload ? "ok" : "not_connected"} />}
            />
            <CompactMetric
              label="Extracted Records"
              value={topicPayload ? records.length : "Not connected"}
              detail={`Derived from ${selectedTopicLabel.toLowerCase()} payload.`}
              icon={Database}
            />
            <CompactMetric
              label={isHouseTopic ? "Median Price" : "Available Dates"}
              value={
                isHouseTopic
                  ? formatVNDWithUnit(houseMedianPrice)
                  : availableDates?.count ?? availableDates?.dates?.length ?? "Not connected"
              }
              detail={isHouseTopic ? "Parsed from current listings" : "GET /api/available-dates"}
              icon={CalendarClock}
            />
            <CompactMetric
              label="HITL Reviews"
              value={hitlCases || blockingSignals || houseCloudflareOpen ? totalReviewOpen : "Not connected"}
              detail={
                hitlCases || blockingSignals || houseCloudflareOpen
                  ? `${totalReviewCount} total cases, ${totalBlockingOpen} blocking`
                  : "GET /api/hitl/cases + /api/blocking-signals"
              }
              icon={RadioTower}
              status={<StatusBadge status={hitlCases || blockingSignals || houseCloudflareOpen ? (totalReviewOpen ? "open" : "resolved") : "not_connected"} />}
            />
            <CompactMetric
              label="Rate Limit Usage"
              value="Not connected"
              detail="TODO: GET /crawler/rate-limits"
              icon={TimerReset}
              status={<StatusBadge status="not_connected" />}
            />
          </div>

          <section className="grid gap-5 xl:grid-cols-[1fr_320px]">
            <Panel
              title={isHouseTopic ? "House Price Snapshot" : "Gold Price Trend"}
              action={
                <span className="text-xs text-muted">
                  {isHouseTopic ? "Backend /api/house-prices" : "Backend /api/analytics/trends"}
                </span>
              }
            >
              {!isHouseTopic && trends ? (
                <PriceTrendChart trends={trends} />
              ) : isHouseTopic && records.length ? (
                <DataTable
                  columns={[
                    {
                      key: "title",
                      header: "Listing",
                      render: (row) => (
                        <div className="max-w-xl">
                          {row.url ? (
                            <a className="font-semibold text-sky-100 hover:text-cyan" href={row.url} target="_blank" rel="noreferrer">
                              {row.title}
                            </a>
                          ) : (
                            <span className="font-semibold text-sky-100">{row.title}</span>
                          )}
                          <div className="mt-1 text-xs text-muted">{row.location}</div>
                        </div>
                      ),
                    },
                    { key: "source", header: "Source", render: (row) => row.source.toUpperCase() },
                    { key: "price", header: "Price", align: "right", render: (row) => formatVNDWithUnit(row.price) },
                    { key: "pricePerM2", header: "VND / m2", align: "right", render: (row) => formatVNDWithUnit(row.pricePerM2) },
                  ]}
                  rows={records.slice(0, 8)}
                  maxHeight="320px"
                />
              ) : (
                <NotConnectedCard
                  title={isHouseTopic ? "No house price records available yet." : "No historical trend data available yet."}
                  message={isHouseTopic ? "Refresh this topic after the backend crawler is running." : "Historical chart appears only when /api/analytics/trends returns backend data."}
                />
              )}
            </Panel>

            <div className="space-y-5">
              <Panel title="Source Status">
                <SourceStatusPanel sourceRows={sourceRows} />
              </Panel>
              <Panel title="Price Changes">
                {isHouseTopic ? (
                  <div className="space-y-4">
                    <div>
                      <div className="text-3xl font-bold text-white">{formatVNDWithUnit(houseMedianPricePerM2)}</div>
                      <div className="text-xs uppercase text-muted">median vnd / m2</div>
                    </div>
                    <div className="space-y-3">
                      <div className="flex items-center justify-between text-sm text-sky-100">
                        <span>Listings</span>
                        <span className="font-bold text-emerald-300">{records.length}</span>
                      </div>
                      <div className="flex items-center justify-between text-sm text-sky-100">
                        <span>With area</span>
                        <span className="font-bold text-slate-300">{records.filter((record) => record.areaM2).length}</span>
                      </div>
                      <div className="flex items-center justify-between text-sm text-sky-100">
                        <span>With price</span>
                        <span className="font-bold text-amber-300">{records.filter((record) => record.price).length}</span>
                      </div>
                    </div>
                  </div>
                ) : sourceMomentum ? (
                  <MomentumMiniPanel momentum={sourceMomentum} />
                ) : (
                  <NotConnectedCard
                    title="Price changes endpoint is not connected."
                    message="Requires GET /api/analytics/source-momentum."
                  />
                )}
              </Panel>
            </div>
          </section>

          <section className="grid gap-5 xl:grid-cols-2">
            <Panel title="Blocking Signals">
              {blockingRows.length ? (
                <DataTable
                  columns={[
                    { key: "reason", header: "Reason" },
                    { key: "source", header: "Source" },
                    { key: "severity", header: "Severity" },
                    { key: "status", header: "Status", render: (row) => <StatusBadge status={row.status} /> },
                    { key: "message", header: "Message" },
                  ]}
                  rows={blockingRows.slice(0, 5).map((signal, index) => ({
                    id: signal.signal_id || `${signal.source || "signal"}-${index}`,
                    ...signal,
                  }))}
                  maxHeight="280px"
                />
              ) : (
                <NotConnectedCard
                  title="No blocking signals detected."
                  message="Cloudflare, captcha, access denied, timeout, and browser errors will appear here."
                />
              )}
            </Panel>
            <Panel title="Recent Notifications" action={<span className="text-xs text-cyan">0 total</span>}>
              <NotConnectedCard
                title="No notification endpoint is exposed yet."
                message="TODO: Backend needed: GET /notifications"
              />
            </Panel>
          </section>

          <section className="grid gap-5 xl:grid-cols-[1fr_440px]">
            <Panel title="Active Crawl Jobs" action={<span className="text-xs text-cyan">{crawlJobRows.length} jobs</span>}>
              <DataTable
                columns={[
                  { key: "job_name", header: "Job Name" },
                  { key: "target_site", header: "Target Site" },
                  { key: "profile", header: "Profile" },
                  { key: "status", header: "Status", render: (row) => <StatusBadge status={row.status} /> },
                  { key: "progress", header: "Progress", align: "right" },
                ]}
                rows={crawlJobRows.map((job, index) => ({
                  id: `${job.source || job.job_name || "job"}-${index}`,
                  ...job,
                }))}
                emptyMessage="No crawl job snapshot is available yet."
                maxHeight="360px"
              />
            </Panel>
            <div className="space-y-5">
              <Panel title="HITL Queue" action={<span className="text-xs text-cyan">{hitlCases?.open_count ?? 0} open</span>}>
                {caseRows.length ? (
                  <DataTable
                    columns={[
                      { key: "reason", header: "Reason" },
                      { key: "source", header: "Source" },
                      { key: "status", header: "Status", render: (row) => <StatusBadge status={row.status} /> },
                    ]}
                    rows={caseRows.map((item) => ({ id: item.case_id, ...item }))}
                    maxHeight="260px"
                  />
                ) : (
                  <NotConnectedCard
                    title="No HITL cases."
                    message="MFA, Captcha, access denied, timeout, and browser-error cases will appear here when backend login tests detect them."
                  />
                )}
              </Panel>
              <Panel title="Recent Activity">
                {loginRows.length ? (
                  <DataTable
                    columns={[
                      { key: "target_label", header: "Target" },
                      { key: "status", header: "Status", render: (row) => <StatusBadge status={row.status} /> },
                      { key: "created_at", header: "Created", render: (row) => formatDateTime(row.created_at) },
                    ]}
                    rows={loginRows.map((job) => ({ id: job.job_id, ...job }))}
                    maxHeight="260px"
                  />
                ) : (
                  <NotConnectedCard
                    title="No login-test activity yet."
                    message="Start a login test from HITL Review to populate recent activity."
                  />
                )}
              </Panel>
            </div>
          </section>

          <Panel title="Source Health Records">
            <DataTable
              columns={[
                { key: "source", header: "Source" },
                { key: "topic", header: "Topic" },
                { key: "status", header: "Status", render: (row) => <StatusBadge status={row.status} /> },
                { key: "message", header: "Message" },
              ]}
              rows={sourceRows}
            />
          </Panel>

          <section className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
            <CompactMetric
              label="Active Sessions"
              value={sessions?.count ?? sessions?.sessions?.length ?? "Not connected"}
              detail={sessions ? "Safe session metadata only." : "GET /api/sessions"}
              icon={UserCheck}
              status={<StatusBadge status={sessions ? "available" : "not_connected"} />}
            />
            <CompactMetric
              label="Blocking Signals"
              value={blockingSignals ? openBlockingRows.length : "Not connected"}
              detail={blockingSignals ? `${blockingRows.length} total detected` : "GET /api/blocking-signals"}
              icon={ShieldAlert}
              status={<StatusBadge status={blockingSignals ? (openBlockingRows.length ? "open" : "resolved") : "not_connected"} />}
            />
            <CompactMetric
              label="Notification Count"
              value="0"
              detail="No notification endpoint is exposed by FastAPI yet."
              icon={Bell}
            />
            <CompactMetric
              label="Crawler Activity"
              value="Not connected"
              detail="TODO: Backend needed: GET /crawler/activity?window=24h"
              icon={LineChart}
              status={<StatusBadge status="not_connected" />}
            />
          </section>
        </>
      )}
    </div>
  );
}
