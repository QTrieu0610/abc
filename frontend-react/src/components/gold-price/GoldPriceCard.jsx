import StatusBadge from "../common/StatusBadge";
import { formatVND } from "../../utils/format";

const accentByCompany = {
  SJC: "from-red-500/20 to-cyan-400/5 text-red-200",
  DOJI: "from-indigo-500/20 to-cyan-400/5 text-indigo-200",
  PNJ: "from-emerald-500/20 to-cyan-400/5 text-emerald-200",
};

export default function GoldPriceCard({ label, title, record, status }) {
  const company = record?.company || "Unknown";
  const accent = accentByCompany[company] || "from-slate-500/20 to-cyan-400/5 text-slate-200";

  return (
    <article className="rounded-lg border border-line bg-panel p-4 shadow-glow">
      <div className="flex items-start gap-3">
        <div className={`rounded-md bg-gradient-to-br ${accent} p-2`}>
          <span className="block h-4 w-4 rounded-sm border border-current" />
        </div>
        <div className="min-w-0">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-sky-300">{label}</p>
          <h3 className="mt-1 text-sm font-bold text-white">{title}</h3>
        </div>
      </div>

      <div className="mt-5 space-y-3">
        <div className="rounded-md bg-panelSoft p-3">
          <div className="text-[10px] font-semibold uppercase text-sky-300">Buy</div>
          <div className="mt-1 text-xl font-bold text-white">{formatVND(record?.buy)}</div>
        </div>
        <div className="rounded-md bg-panelSoft p-3">
          <div className="text-[10px] font-semibold uppercase text-sky-300">Sell</div>
          <div className="mt-1 text-xl font-bold text-white">{formatVND(record?.sell)}</div>
        </div>
      </div>

      <div className="mt-4 flex items-center gap-2 text-xs text-muted">
        <StatusBadge status={status || (record ? "ok" : "empty")} />
        <span className="truncate">
          {record ? `${record.region || "N/A"} - ${record.goldType || "N/A"}` : "No data available"}
        </span>
      </div>
    </article>
  );
}
