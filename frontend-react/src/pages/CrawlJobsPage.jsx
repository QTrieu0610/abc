import { useCallback } from "react";
import { getCrawlJobs } from "../api/crawlJobApi";
import EmptyState from "../components/common/EmptyState";
import ErrorState from "../components/common/ErrorState";
import LoadingState from "../components/common/LoadingState";
import RefreshButton from "../components/common/RefreshButton";
import StatusBadge from "../components/common/StatusBadge";
import DataTable from "../components/tables/DataTable";
import { useAutoRefresh } from "../hooks/useAutoRefresh";
import { formatDateTime } from "../utils/format";

function ProgressBar({ value = 0 }) {
  const numeric = Math.max(0, Math.min(100, Number(value) || 0));
  return (
    <div className="flex items-center justify-end gap-3">
      <div className="h-2 w-28 rounded-full bg-sky-950">
        <div className="h-full rounded-full bg-sky-500" style={{ width: `${numeric}%` }} />
      </div>
      <span className="w-10 text-right font-semibold text-sky-100">{numeric}%</span>
    </div>
  );
}

export default function CrawlJobsPage() {
  const fetchJobs = useCallback(() => getCrawlJobs(false), []);
  const { data, loading, refreshing, error, refresh } = useAutoRefresh(fetchJobs, 15000);
  const jobs = Array.isArray(data?.jobs) ? data.jobs : [];

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Crawl Jobs</h1>
          <p className="mt-1 text-sm text-sky-200">
            Real crawler source jobs derived from the latest backend source payload.
          </p>
        </div>
        <RefreshButton onClick={refresh} refreshing={refreshing} />
      </div>

      {loading ? (
        <LoadingState title="Loading crawler jobs..." />
      ) : error ? (
        <ErrorState error={error} onRetry={refresh} />
      ) : jobs.length ? (
        <DataTable
          columns={[
            { key: "job_name", header: "Job Name" },
            { key: "target_site", header: "Target Site" },
            { key: "profile", header: "Profile" },
            { key: "status", header: "Status", render: (row) => <StatusBadge status={row.status} /> },
            { key: "records", header: "Records", align: "right" },
            { key: "progress", header: "Progress", align: "right", render: (row) => <ProgressBar value={row.progress} /> },
            { key: "last_run", header: "Last Run", render: (row) => formatDateTime(row.last_run) },
            { key: "message", header: "Message" },
          ]}
          rows={jobs.map((job, index) => ({
            id: `${job.source || job.job_name || "job"}-${index}`,
            ...job,
          }))}
          maxHeight="560px"
        />
      ) : (
        <EmptyState
          title="No crawler jobs available."
          message="The backend is reachable, but it has no crawler job snapshot yet."
        />
      )}
    </div>
  );
}
