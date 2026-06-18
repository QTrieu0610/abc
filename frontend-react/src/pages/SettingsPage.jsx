import { useCallback } from "react";
import { API_BASE_URL } from "../api/client";
import { getHealth } from "../api/crawlerApi";
import EmptyState from "../components/common/EmptyState";
import ErrorState from "../components/common/ErrorState";
import LoadingState from "../components/common/LoadingState";
import RefreshButton from "../components/common/RefreshButton";
import StatusBadge from "../components/common/StatusBadge";
import { useAutoRefresh } from "../hooks/useAutoRefresh";
import { formatDateTime } from "../utils/format";

export default function SettingsPage() {
  const fetchHealth = useCallback(() => getHealth(), []);
  const { data, loading, refreshing, error, refresh } = useAutoRefresh(fetchHealth, 30000);

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Settings</h1>
          <p className="mt-1 text-sm text-sky-200">Frontend connection and compliance status.</p>
        </div>
        <RefreshButton onClick={refresh} refreshing={refreshing} />
      </div>

      <div className="rounded-lg border border-line bg-panel p-5">
        <div className="text-[11px] font-semibold uppercase tracking-wide text-sky-300">API Base URL</div>
        <div className="mt-2 rounded-md border border-line bg-panelSoft px-3 py-2 font-mono text-sm text-white">
          {API_BASE_URL}
        </div>
      </div>

      {loading ? (
        <LoadingState title="Checking backend health..." />
      ) : error ? (
        <ErrorState error={error} onRetry={refresh} />
      ) : (
        <div className="rounded-lg border border-line bg-panel p-5">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-white">Backend Health</h2>
            <StatusBadge status={data?.status || "not_connected"} />
          </div>
          <p className="mt-2 text-sm text-muted">Last check: {formatDateTime(data?.timestamp)}</p>
          <div className="mt-4 grid gap-3 md:grid-cols-3">
            {Object.entries(data?.services || {}).map(([name, status]) => (
              <div key={name} className="rounded-md border border-line bg-panelSoft p-3">
                <div className="text-xs uppercase text-sky-300">{name}</div>
                <div className="mt-2"><StatusBadge status={status} /></div>
              </div>
            ))}
          </div>
        </div>
      )}

      <EmptyState
        title="Safety and compliance"
        message="Authorized crawling only. Credentials are handled by backend only. Human approval is required for MFA or captcha. Respect target website policies and configured rate limits."
      />
    </div>
  );
}
