import EmptyState from "./EmptyState";
import { formatDateTime } from "../../utils/format";

const levelClasses = {
  error: "text-red-300",
  warning: "text-amber-300",
  info: "text-sky-200",
};

export default function LogViewer({
  rows = [],
  emptyTitle = "Audit logs endpoint is not connected yet.",
  emptyMessage = "TODO: Backend needed: GET /logs or GET /audit-logs",
  maxHeight = "360px",
}) {
  if (!rows.length) {
    return (
      <EmptyState
        title={emptyTitle}
        message={emptyMessage}
      />
    );
  }

  return (
    <div
      className="overflow-auto rounded-lg border border-line bg-[#040b14] p-4 font-mono text-xs text-slate-300"
      style={{ maxHeight }}
    >
      <div className="space-y-2">
        {rows.map((row, index) => {
          const level = String(row.level || "info").toLowerCase();
          return (
            <div key={`${row.timestamp || "log"}-${index}`} className="grid gap-2 md:grid-cols-[130px_80px_1fr]">
              <span className="text-slate-500">{formatDateTime(row.timestamp)}</span>
              <span className={levelClasses[level] || levelClasses.info}>{level.toUpperCase()}</span>
              <span className="whitespace-pre-wrap break-words text-slate-200">
                {row.message || JSON.stringify(row)}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
