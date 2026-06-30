import { RefreshCw } from "lucide-react";

export default function RefreshButton({ onClick, refreshing, label = "Refresh" }) {
  return (
    <button
      type="button"
      onClick={() => onClick?.({ isUserAction: true })}
      disabled={refreshing}
      className="inline-flex h-10 items-center gap-2 rounded-md border border-line bg-panelSoft px-3 text-sm font-semibold text-sky-100 transition hover:border-cyan/40 hover:text-white disabled:opacity-60"
    >
      <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} aria-hidden="true" />
      {label}
    </button>
  );
}
