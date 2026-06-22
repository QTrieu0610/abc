import { ShieldAlert, ShieldCheck, TimerReset } from "lucide-react";
import { useCallback, useMemo } from "react";
import { getBlockingSignals } from "../api/blockingApi";
import EmptyState from "../components/common/EmptyState";
import ErrorState from "../components/common/ErrorState";
import LoadingState from "../components/common/LoadingState";
import MetricCard from "../components/common/MetricCard";
import RefreshButton from "../components/common/RefreshButton";
import SeverityBadge from "../components/common/SeverityBadge";
import StatusBadge from "../components/common/StatusBadge";
import DataTable from "../components/tables/DataTable";
import { useAutoRefresh } from "../hooks/useAutoRefresh";
import { formatDateTime } from "../utils/format";

function latestUpdated(signals) {
  const dates = signals.map((signal) => signal.updated_at || signal.created_at).filter(Boolean).sort();
  return dates.length ? dates[dates.length - 1] : null;
}

export default function BlockingSignalsPage() {
  const fetchSignals = useCallback(() => getBlockingSignals(), []);
  const { data, loading, refreshing, error, refresh } = useAutoRefresh(fetchSignals, 15000);
  const signals = useMemo(() => (Array.isArray(data?.signals) ? data.signals : []), [data]);
  const openSignals = signals.filter((signal) => signal.status === "open");
  const latest = latestUpdated(signals);

  const columns = [
    { key: "reason", header: "Reason" },
    { key: "source", header: "Source" },
    { key: "signal_type", header: "Signal Type" },
    { key: "severity", header: "Severity", render: (row) => <SeverityBadge severity={row.severity} /> },
    { key: "status", header: "Status", render: (row) => <StatusBadge status={row.status} /> },
    { key: "updated_at", header: "Updated", render: (row) => formatDateTime(row.updated_at) },
    { key: "message", header: "Message" },
    { key: "action", header: "Action" },
  ];

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Blocking Signals</h1>
          <p className="mt-1 text-sm text-sky-200">
            Captcha, MFA, access-denied, timeout, and browser events detected by backend jobs.
          </p>
        </div>
        <RefreshButton onClick={refresh} refreshing={refreshing} />
      </div>

      {loading ? (
        <LoadingState title="Loading blocking signals..." />
      ) : error ? (
        <ErrorState error={error} onRetry={refresh} />
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-3">
            <MetricCard
              label="Open Signals"
              value={data?.open_count ?? openSignals.length}
              detail="Need human review"
              icon={ShieldAlert}
              status={<StatusBadge status={openSignals.length ? "open" : "resolved"} />}
            />
            <MetricCard
              label="Total Signals"
              value={data?.count ?? signals.length}
              detail="Detected by backend"
              icon={ShieldCheck}
            />
            <MetricCard
              label="Last Update"
              value={latest ? formatDateTime(latest) : "No signals"}
              detail="Auto-refreshes every 15s"
              icon={TimerReset}
            />
          </div>

          {signals.length ? (
            <DataTable
              columns={columns}
              rows={signals.map((signal, index) => ({
                id: signal.signal_id || `${signal.job_id || "signal"}-${index}`,
                ...signal,
              }))}
              maxHeight="620px"
            />
          ) : (
            <EmptyState
              title="No blocking signals detected."
              message="Signals will appear here when backend jobs detect MFA, captcha, Cloudflare, access denied, timeout, or browser errors."
            />
          )}

          <p className="text-xs text-muted">Last refresh: {formatDateTime(data?.timestamp)}</p>
        </>
      )}
    </div>
  );
}
