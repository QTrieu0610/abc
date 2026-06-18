import { useCallback } from "react";
import { getSessions } from "../api/sessionApi";
import EmptyState from "../components/common/EmptyState";
import ErrorState from "../components/common/ErrorState";
import LoadingState from "../components/common/LoadingState";
import RefreshButton from "../components/common/RefreshButton";
import StatusBadge from "../components/common/StatusBadge";
import DataTable from "../components/tables/DataTable";
import { useAutoRefresh } from "../hooks/useAutoRefresh";
import { formatDateTime } from "../utils/format";

export default function SessionsPage() {
  const fetchSessions = useCallback(() => getSessions(), []);
  const { data, loading, refreshing, error, refresh } = useAutoRefresh(fetchSessions, 15000);
  const sessions = Array.isArray(data?.sessions) ? data.sessions : [];

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Sessions & Identities</h1>
          <p className="mt-1 text-sm text-sky-200">
            Safe crawler session metadata. Credentials and cookie values stay on the backend.
          </p>
        </div>
        <RefreshButton onClick={refresh} refreshing={refreshing} />
      </div>

      {loading ? (
        <LoadingState title="Loading safe session metadata..." />
      ) : error ? (
        <ErrorState error={error} onRetry={refresh} />
      ) : sessions.length ? (
        <>
          <div className="rounded-lg border border-emerald-400/20 bg-emerald-400/10 p-4 text-sm text-emerald-100">
            {data?.security || "Cookie values, tokens, and credentials are never displayed."}
          </div>
          <DataTable
            columns={[
              { key: "session_name", header: "Session Name" },
              { key: "topic", header: "Source / Topic" },
              { key: "login_status", header: "Login Status", render: (row) => <StatusBadge status={row.login_status} /> },
              { key: "last_used", header: "Last Used", render: (row) => formatDateTime(row.last_used) },
              { key: "mfa_required", header: "MFA Required" },
              { key: "session_file", header: "Session File" },
              { key: "status", header: "Status", render: (row) => <StatusBadge status={row.status} /> },
              { key: "cookie_count", header: "Cookies", align: "right" },
              { key: "source", header: "Domains" },
            ]}
            rows={sessions.map((session, index) => ({
              id: `${session.session_file || session.session_name || "session"}-${index}`,
              ...session,
            }))}
            maxHeight="520px"
          />
        </>
      ) : (
        <EmptyState
          title="No crawler session metadata available."
          message="No JSON session files were found in the backend sessions directory."
        />
      )}
    </div>
  );
}
