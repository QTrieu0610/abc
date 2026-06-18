export default function GoldSummaryCard({ label, value, detail, tone = "green" }) {
  const tones = {
    green: "text-emerald-300",
    cyan: "text-cyan",
    amber: "text-amber-300",
    red: "text-red-300",
    muted: "text-slate-300",
  };

  return (
    <article className="rounded-lg border border-line bg-panel p-4">
      <div className={`text-[11px] font-semibold uppercase tracking-wide ${tones[tone] || tones.green}`}>
        + {label}
      </div>
      <div className="mt-3 text-xl font-bold text-white">{value}</div>
      {detail && <div className="mt-2 text-xs leading-5 text-muted">{detail}</div>}
    </article>
  );
}
