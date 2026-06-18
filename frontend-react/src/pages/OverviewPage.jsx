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
import { useCallback, useMemo } from "react";
import { getCrawlJobs } from "../api/crawlJobApi";
import { getHealth } from "../api/crawlerApi";
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
import { formatDateTime } from "../utils/format";
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

export default function OverviewPage() {
  const fetchOverview = useCallback(async () => {
    const results = await Promise.all([
      settle("health", getHealth()),
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
      settle("hitlCases", getHitlCases()),
      settle("loginTests", getLoginTests()),
      settle("crawlJobs", getCrawlJobs(false)),
      settle("sessions", getSessions()),
    ]);

    return Object.fromEntries(results.map((result) => [result.name, result]));
  }, []);

  const { data, loading, refreshing, error, refresh } = useAutoRefresh(fetchOverview, 10000);
  const health = data?.health?.status === "fulfilled" ? data.health.value : null;
  const currentPrices = data?.currentPrices?.status === "fulfilled" ? data.currentPrices.value : null;
  const availableDates = data?.availableDates?.status === "fulfilled" ? data.availableDates.value : null;
  const trends = data?.trends?.status === "fulfilled" ? data.trends.value : null;
  const sourceMomentum =
    data?.sourceMomentum?.status === "fulfilled" ? data.sourceMomentum.value : null;
  const hitlCases = data?.hitlCases?.status === "fulfilled" ? data.hitlCases.value : null;
  const loginTests = data?.loginTests?.status === "fulfilled" ? data.loginTests.value : null;
  const crawlJobs = data?.crawlJobs?.status === "fulfilled" ? data.crawlJobs.value : null;
  const sessions = data?.sessions?.status === "fulfilled" ? data.sessions.value : null;
  const records = useMemo(() => normalizeGoldPriceResponse(currentPrices), [currentPrices]);
  const sourceStatuses = useMemo(() => getSourceStatuses(currentPrices), [currentPrices]);
  const caseRows = Array.isArray(hitlCases?.cases) ? hitlCases.cases.slice(0, 4) : [];
  const loginRows = Array.isArray(loginTests?.jobs) ? loginTests.jobs.slice(0, 4) : [];
  const crawlJobRows = Array.isArray(crawlJobs?.jobs) ? crawlJobs.jobs : [];

  const sourceRows = Object.entries(sourceStatuses).map(([source, status]) => ({
    id: source,
    source: source.toUpperCase(),
    topic: "Gold Price",
    status,
    message:
      currentPrices?.[source]?.error ||
      (status === "ok" ? "Backend source returned records." : "No source records returned."),
  }));

  const anyEndpointSucceeded = Boolean(
    health || currentPrices || availableDates || trends || sourceMomentum || hitlCases || loginTests || crawlJobs || sessions
  );
  const lastCrawlTime = currentPrices?.timestamp ? formatDateTime(currentPrices.timestamp) : "Not connected";
  const serviceSummary = health?.services
    ? Object.entries(health.services).map(([name, status]) => `${name}: ${status}`).join(" | ")
    : "GET /api/health";

  return (
    <div className="space-y-5 pb-12">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Crawler Operations Center</h1>
          <p className="mt-1 text-sm text-sky-200">
            Authorized crawling, session monitoring, blocking detection, and human review.
          </p>
        </div>
        <RefreshButton onClick={refresh} refreshing={refreshing} />
      </div>

      {loading ? (
        <LoadingState title="Loading crawler overview..." />
      ) : error && !anyEndpointSucceeded ? (
        <ErrorState error={error} onRetry={refresh} />
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
            <CompactMetric
              label="Backend API"
              value={health?.status || "Not connected"}
              detail={serviceSummary}
              icon={Server}
              status={<StatusBadge status={health?.status || "not_connected"} />}
            />
            <CompactMetric
              label="Current Feed"
              value={currentPrices ? "Connected" : "Not connected"}
              detail={lastCrawlTime}
              icon={Activity}
              status={<StatusBadge status={currentPrices ? "ok" : "not_connected"} />}
            />
            <CompactMetric
              label="Extracted Records"
              value={currentPrices ? records.length : "Not connected"}
              detail="Derived from real current price payload."
              icon={Database}
            />
            <CompactMetric
              label="Available Dates"
              value={availableDates?.count ?? availableDates?.dates?.length ?? "Not connected"}
              detail="GET /api/available-dates"
              icon={CalendarClock}
            />
            <CompactMetric
              label="HITL Reviews"
              value={hitlCases ? hitlCases.open_count ?? 0 : "Not connected"}
              detail={hitlCases ? `${hitlCases.count ?? 0} total cases` : "GET /api/hitl/cases"}
              icon={RadioTower}
              status={<StatusBadge status={hitlCases ? (hitlCases.open_count ? "open" : "resolved") : "not_connected"} />}
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
              title="Gold Price Trend"
              action={<span className="text-xs text-muted">Backend /api/analytics/trends</span>}
            >
              {trends ? (
                <PriceTrendChart trends={trends} />
              ) : (
                <NotConnectedCard
                  title="No historical trend data available yet."
                  message="Historical chart appears only when /api/analytics/trends returns backend data."
                />
              )}
            </Panel>

            <div className="space-y-5">
              <Panel title="Source Status">
                <SourceStatusPanel sourceRows={sourceRows} />
              </Panel>
              <Panel title="Price Changes">
                {sourceMomentum ? (
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
              <NotConnectedCard
                title="Blocking signals endpoint is not connected yet."
                message="TODO: Backend needed: GET /blocking-signals or GET /crawler/blocking-signals"
              />
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
              value="Not connected"
              detail="TODO: Backend needed: GET /blocking-signals"
              icon={ShieldAlert}
              status={<StatusBadge status="not_connected" />}
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
