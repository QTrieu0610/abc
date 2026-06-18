const classes = {
  info: "border-cyan-400/30 bg-cyan-400/10 text-cyan-200",
  low: "border-emerald-400/30 bg-emerald-400/10 text-emerald-300",
  medium: "border-amber-400/30 bg-amber-400/10 text-amber-300",
  high: "border-orange-400/30 bg-orange-400/10 text-orange-300",
  critical: "border-red-400/30 bg-red-400/10 text-red-300",
};

export default function SeverityBadge({ severity = "info" }) {
  const key = String(severity).toLowerCase();
  return (
    <span className={`rounded px-2 py-1 text-[11px] font-semibold uppercase ${classes[key] || classes.info}`}>
      {severity}
    </span>
  );
}
