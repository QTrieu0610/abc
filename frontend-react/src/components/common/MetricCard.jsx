export default function MetricCard({ label, value, detail, icon: Icon, status }) {
  return (
    <div className="min-w-0 overflow-hidden rounded-lg border border-line bg-panel p-4 shadow-glow">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-sky-300">{label}</p>
          <p className="mt-3 whitespace-normal text-2xl font-bold leading-tight text-white">{value}</p>
        </div>
        {Icon && (
          <div className="shrink-0 rounded-md border border-cyan-400/10 bg-cyan-400/10 p-2 text-cyan">
            <Icon className="h-4 w-4" aria-hidden="true" />
          </div>
        )}
      </div>
      {detail && <p className="mt-3 whitespace-normal text-xs text-muted">{detail}</p>}
      {status && <div className="mt-3">{status}</div>}
    </div>
  );
}
