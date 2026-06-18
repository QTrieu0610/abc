import EmptyState from "../components/common/EmptyState";
import LogViewer from "../components/common/LogViewer";
import RefreshButton from "../components/common/RefreshButton";

const copy = {
  "crawl-jobs": {
    title: "Crawl Jobs",
    subtitle: "Backend crawl job endpoint is not connected yet.",
    message: "TODO: Backend needed: GET /crawl-jobs or GET /crawler/jobs",
  },
  sessions: {
    title: "Sessions & Identities",
    subtitle: "Sessions endpoint is not connected yet.",
    message: "TODO: Backend needed: GET /sessions or GET /crawler-sessions with safe metadata only.",
  },
  "blocking-signals": {
    title: "Blocking Signals",
    subtitle: "Blocking signals endpoint is not connected yet.",
    message: "TODO: Backend needed: GET /blocking-signals or GET /crawler/blocking-signals",
  },
  hitl: {
    title: "HITL Review",
    subtitle: "HITL review endpoint is not connected yet.",
    message: "TODO: Backend needed: GET /hitl/cases and POST actions for resolve/retry/pause.",
    warning: "Continue only when this crawl is authorized and compliant with the target website policy.",
  },
  notifications: {
    title: "Notifications",
    subtitle: "No notification endpoint is exposed yet.",
    message: "TODO: Backend needed: GET /notifications",
  },
  "audit-logs": {
    title: "Audit Logs",
    subtitle: "Audit logs endpoint is not connected yet.",
    message: "TODO: Backend needed: GET /logs or GET /audit-logs",
    logViewer: true,
  },
};

export default function EndpointMissingPage({ page }) {
  const current = copy[page] || copy["crawl-jobs"];

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">{current.title}</h1>
          <p className="mt-1 text-sm text-sky-200">{current.subtitle}</p>
        </div>
        <RefreshButton refreshing={false} onClick={() => undefined} />
      </div>
      {current.warning && (
        <div className="rounded-lg border border-amber-400/25 bg-amber-400/10 p-4 text-sm font-medium text-amber-100">
          {current.warning}
        </div>
      )}
      {current.logViewer ? (
        <LogViewer rows={[]} />
      ) : (
        <EmptyState title={current.subtitle} message={current.message} />
      )}
    </div>
  );
}
