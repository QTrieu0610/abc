const toneClasses = {
  ok: "border-emerald-400/30 bg-emerald-400/10 text-emerald-300",
  healthy: "border-emerald-400/30 bg-emerald-400/10 text-emerald-300",
  running: "border-emerald-400/30 bg-emerald-400/10 text-emerald-300",
  queued: "border-cyan-400/30 bg-cyan-400/10 text-cyan-200",
  open: "border-amber-400/30 bg-amber-400/10 text-amber-300",
  blocked: "border-amber-400/30 bg-amber-400/10 text-amber-300",
  skipped: "border-amber-400/30 bg-amber-400/10 text-amber-300",
  resolved: "border-emerald-400/30 bg-emerald-400/10 text-emerald-300",
  completed: "border-indigo-400/30 bg-indigo-400/10 text-indigo-300",
  available: "border-emerald-400/30 bg-emerald-400/10 text-emerald-300",
  stored: "border-emerald-400/30 bg-emerald-400/10 text-emerald-300",
  idle: "border-slate-400/30 bg-slate-400/10 text-slate-300",
  empty: "border-slate-400/30 bg-slate-400/10 text-slate-300",
  unavailable: "border-amber-400/30 bg-amber-400/10 text-amber-300",
  failed: "border-red-400/30 bg-red-400/10 text-red-300",
  error: "border-red-400/30 bg-red-400/10 text-red-300",
  not_connected: "border-cyan-400/25 bg-cyan-400/10 text-cyan-200",
};

export default function StatusBadge({ status = "empty", label }) {
  const key = String(status).toLowerCase().replace(/\s+/g, "_");
  return (
    <span
      className={`inline-flex items-center gap-1 rounded px-2 py-1 text-[11px] font-semibold uppercase tracking-wide ${toneClasses[key] || toneClasses.empty}`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {label || String(status).replace(/_/g, " ")}
    </span>
  );
}
