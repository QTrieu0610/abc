import { AlertTriangle, KeyRound, Play, ShieldCheck } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { getHitlCases } from "../api/hitlApi";
import { getLoginTestLogs, getLoginTests, startLoginTest } from "../api/loginTestApi";
import EmptyState from "../components/common/EmptyState";
import ErrorState from "../components/common/ErrorState";
import LoadingState from "../components/common/LoadingState";
import LogViewer from "../components/common/LogViewer";
import RefreshButton from "../components/common/RefreshButton";
import SeverityBadge from "../components/common/SeverityBadge";
import StatusBadge from "../components/common/StatusBadge";
import DataTable from "../components/tables/DataTable";
import { useAutoRefresh } from "../hooks/useAutoRefresh";
import { formatDateTime } from "../utils/format";

function Panel({ title, action, children }) {
  return (
    <section className="overflow-hidden rounded-lg border border-line bg-panel shadow-glow">
      <div className="flex min-h-14 items-center justify-between border-b border-line px-4">
        <h2 className="text-sm font-bold text-white">{title}</h2>
        {action}
      </div>
      <div className="p-4">{children}</div>
    </section>
  );
}

function Field({ label, children }) {
  return (
    <label className="block">
      <span className="mb-2 block text-xs font-semibold uppercase tracking-wide text-sky-300">{label}</span>
      {children}
    </label>
  );
}

const inputClass =
  "w-full rounded-md border border-line bg-[#071626] px-3 py-2 text-sm text-white outline-none transition placeholder:text-slate-500 focus:border-cyan";

function isRunning(job) {
  return ["queued", "running"].includes(String(job?.status || "").toLowerCase());
}

export default function HitlReviewPage() {
  const [form, setForm] = useState({
    target_type: "demo",
    target_url: "",
    username: "student",
    password: "",
    profile_name: "default",
  });
  const [selectedJobId, setSelectedJobId] = useState(null);
  const [submitError, setSubmitError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const fetchDashboard = useCallback(async () => {
    const [cases, tests] = await Promise.all([getHitlCases(), getLoginTests()]);
    return { cases, tests };
  }, []);

  const {
    data,
    loading,
    refreshing,
    error,
    refresh,
  } = useAutoRefresh(fetchDashboard, 15000);

  const jobs = useMemo(() => (Array.isArray(data?.tests?.jobs) ? data.tests.jobs : []), [data]);
  const cases = useMemo(() => (Array.isArray(data?.cases?.cases) ? data.cases.cases : []), [data]);
  const selectedJob = jobs.find((job) => job.job_id === selectedJobId) || jobs[0] || null;
  const logInterval = selectedJob && isRunning(selectedJob) ? 2000 : 15000;

  const fetchLogs = useCallback(async () => {
    if (!selectedJob?.job_id) return { logs: [] };
    return getLoginTestLogs(selectedJob.job_id);
  }, [selectedJob?.job_id]);

  const {
    data: logData,
    loading: logLoading,
    error: logError,
    refresh: refreshLogs,
  } = useAutoRefresh(fetchLogs, logInterval, Boolean(selectedJob?.job_id));

  useEffect(() => {
    if (!selectedJobId && jobs[0]?.job_id) {
      setSelectedJobId(jobs[0].job_id);
    }
  }, [jobs, selectedJobId]);

  async function handleSubmit(event) {
    event.preventDefault();
    setSubmitError(null);
    setSubmitting(true);
    try {
      const payload = {
        target_type: form.target_type,
        username: form.username,
        password: form.password,
        profile_name: form.profile_name || "default",
      };
      if (form.target_type === "custom") {
        payload.target_url = form.target_url;
      }
      const job = await startLoginTest(payload);
      setSelectedJobId(job.job_id);
      setForm((current) => ({ ...current, password: "" }));
      await refresh();
      await refreshLogs();
    } catch (nextError) {
      setSubmitError(nextError);
    } finally {
      setSubmitting(false);
    }
  }

  const openCases = data?.cases?.open_count ?? cases.filter((item) => item.status === "open").length;
  const logs = Array.isArray(logData?.logs) ? logData.logs : [];

  return (
    <div className="space-y-5 pb-10">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">HITL Review</h1>
          <p className="mt-1 text-sm text-sky-200">
            Login tests, MFA/Captcha review, and safe backend logs for authorized crawling.
          </p>
        </div>
        <RefreshButton onClick={refresh} refreshing={refreshing} />
      </div>

      <div className="rounded-lg border border-amber-400/25 bg-amber-400/10 p-4 text-sm font-medium text-amber-100">
        Continue only when this crawl is authorized and compliant with the target website policy.
        Credentials are handled by backend only. Human approval is required for MFA or captcha.
      </div>

      {loading ? (
        <LoadingState title="Loading HITL dashboard..." />
      ) : error ? (
        <ErrorState error={error} onRetry={refresh} />
      ) : (
        <>
          <section className="grid gap-5 xl:grid-cols-[420px_1fr]">
            <Panel
              title="Start Login Test"
              action={<ShieldCheck className="h-4 w-4 text-emerald-300" aria-hidden="true" />}
            >
              <form className="space-y-4" onSubmit={handleSubmit}>
                <Field label="Target">
                  <select
                    className={inputClass}
                    value={form.target_type}
                    onChange={(event) => setForm((current) => ({ ...current, target_type: event.target.value }))}
                  >
                    <option value="demo">Demo Login</option>
                    <option value="github">GitHub Login</option>
                    <option value="custom">Custom URL</option>
                  </select>
                </Field>
                {form.target_type === "custom" && (
                  <Field label="Custom URL">
                    <input
                      className={inputClass}
                      value={form.target_url}
                      onChange={(event) => setForm((current) => ({ ...current, target_url: event.target.value }))}
                      placeholder="https://example.com/login"
                      type="url"
                    />
                  </Field>
                )}
                <Field label="Username">
                  <input
                    className={inputClass}
                    value={form.username}
                    onChange={(event) => setForm((current) => ({ ...current, username: event.target.value }))}
                    autoComplete="username"
                  />
                </Field>
                <Field label="Password">
                  <input
                    className={inputClass}
                    value={form.password}
                    onChange={(event) => setForm((current) => ({ ...current, password: event.target.value }))}
                    placeholder="Used for this run only"
                    type="password"
                    autoComplete="current-password"
                  />
                </Field>
                <Field label="Profile">
                  <input
                    className={inputClass}
                    value={form.profile_name}
                    onChange={(event) => setForm((current) => ({ ...current, profile_name: event.target.value }))}
                    placeholder="default"
                  />
                </Field>
                {submitError && (
                  <div className="rounded-md border border-red-400/25 bg-red-400/10 p-3 text-sm text-red-200">
                    {submitError.message}
                  </div>
                )}
                <button
                  type="submit"
                  disabled={submitting || !form.username || !form.password}
                  className="inline-flex w-full items-center justify-center gap-2 rounded-md border border-cyan/40 bg-cyan px-4 py-2.5 text-sm font-bold text-slate-950 transition hover:bg-sky-300 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <Play className="h-4 w-4" aria-hidden="true" />
                  {submitting ? "Starting..." : "Start Login Test"}
                </button>
              </form>
            </Panel>

            <Panel
              title="HITL Cases"
              action={<span className="text-xs font-semibold text-amber-300">{openCases} open</span>}
            >
              {cases.length ? (
                <DataTable
                  columns={[
                    { key: "reason", header: "Reason" },
                    { key: "source", header: "Source" },
                    { key: "severity", header: "Severity", render: (row) => <SeverityBadge severity={row.severity} /> },
                    { key: "status", header: "Status", render: (row) => <StatusBadge status={row.status} /> },
                    { key: "updated_at", header: "Updated", render: (row) => formatDateTime(row.updated_at) },
                    { key: "message", header: "Message" },
                  ]}
                  rows={cases.map((item) => ({ id: item.case_id, ...item }))}
                  maxHeight="360px"
                />
              ) : (
                <EmptyState
                  title="No HITL cases."
                  message="MFA, Captcha, access denied, timeout, and browser-error cases will appear here when backend login tests detect them."
                />
              )}
            </Panel>
          </section>

          <section className="grid gap-5 xl:grid-cols-[1fr_460px]">
            <Panel title="Login Test Jobs" action={<span className="text-xs text-cyan">{jobs.length} total</span>}>
              {jobs.length ? (
                <DataTable
                  columns={[
                    {
                      key: "target_label",
                      header: "Target",
                      render: (row) => (
                        <button
                          type="button"
                          className="text-left font-semibold text-cyan hover:text-sky-200"
                          onClick={() => setSelectedJobId(row.job_id)}
                        >
                          {row.target_label || row.target_url}
                        </button>
                      ),
                    },
                    { key: "status", header: "Status", render: (row) => <StatusBadge status={row.status} /> },
                    { key: "profile_name", header: "Profile" },
                    { key: "latest_signal", header: "Latest Signal" },
                    { key: "html_length", header: "HTML", align: "right" },
                    { key: "created_at", header: "Created", render: (row) => formatDateTime(row.created_at) },
                  ]}
                  rows={jobs.map((job) => ({ id: job.job_id, ...job }))}
                  maxHeight="420px"
                />
              ) : (
                <EmptyState
                  title="No login tests yet."
                  message="Start a login test to see backend job status and HITL signals."
                />
              )}
            </Panel>

            <Panel
              title="Selected Job Log"
              action={
                selectedJob ? (
                  <StatusBadge status={selectedJob.status} />
                ) : (
                  <span className="text-xs text-muted">No job selected</span>
                )
              }
            >
              {selectedJob ? (
                <div className="space-y-4">
                  <div className="grid gap-3 rounded-lg border border-line bg-panelSoft p-3 text-xs text-sky-100">
                    <div className="flex items-center gap-2">
                      <KeyRound className="h-4 w-4 text-cyan" aria-hidden="true" />
                      <span className="font-semibold text-white">{selectedJob.target_label}</span>
                    </div>
                    <div className="break-all text-muted">{selectedJob.target_url}</div>
                    <div className="grid gap-2 sm:grid-cols-2">
                      <span>Started: {formatDateTime(selectedJob.started_at)}</span>
                      <span>Ended: {formatDateTime(selectedJob.ended_at)}</span>
                    </div>
                  </div>
                  {logLoading ? (
                    <LoadingState title="Loading job logs..." />
                  ) : logError ? (
                    <ErrorState error={logError} onRetry={refreshLogs} />
                  ) : (
                    <LogViewer
                      rows={logs}
                      maxHeight="380px"
                      emptyTitle="No logs for this job yet."
                      emptyMessage="Backend log entries will appear here while the login test runs."
                    />
                  )}
                </div>
              ) : (
                <EmptyState title="No job selected." message="Start or select a login test to view live logs." />
              )}
            </Panel>
          </section>

          <div className="flex items-start gap-3 rounded-lg border border-line bg-panel p-4 text-sm text-sky-100">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-300" aria-hidden="true" />
            <p>
              Password values are never returned by API responses. Do not paste credentials unless this crawl is
              authorized and compliant with the target website policy.
            </p>
          </div>
        </>
      )}
    </div>
  );
}
