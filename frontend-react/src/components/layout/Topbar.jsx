import { Bell, Search, Settings } from "lucide-react";
import { Link } from "react-router-dom";

export default function Topbar({ collapsed }) {
  return (
    <header
      className={`fixed right-0 top-0 z-30 h-[70px] border-b border-line bg-[#071322]/95 backdrop-blur transition-all duration-200 ${collapsed ? "left-[76px]" : "left-[260px]"}`}
    >
      <div className="flex h-full items-center justify-between gap-4 px-5">
        <button
          type="button"
          className="inline-flex h-9 items-center gap-2 rounded-md border border-line bg-panelSoft px-3 text-sm font-semibold text-sky-100"
        >
          <span className="h-2 w-2 rounded-full bg-emerald-400" />
          Production
          <span className="text-muted">v</span>
        </button>

        <div className="hidden min-w-[280px] max-w-lg flex-1 items-center md:flex">
          <label className="relative w-full">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
            <input
              type="search"
              placeholder="Search jobs, sessions, signals..."
              className="h-9 w-full rounded-md border border-line bg-panelSoft pl-10 pr-3 text-sm text-sky-100 outline-none placeholder:text-muted focus:border-cyan/50"
            />
          </label>
        </div>

        <div className="flex items-center gap-2">
          <Link
            to="/notifications"
            className="relative rounded-md p-2 text-sky-100 hover:bg-sky-500/10 hover:text-white"
            aria-label="Notifications"
          >
            <Bell className="h-4 w-4" />
          </Link>
          <Link
            to="/settings"
            className="rounded-md p-2 text-sky-100 hover:bg-sky-500/10 hover:text-white"
            aria-label="Settings"
          >
            <Settings className="h-4 w-4" />
          </Link>
          <div className="ml-2 hidden items-center gap-3 border-l border-line pl-4 sm:flex">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-sky-500/20 text-sm font-bold text-cyan">
              AD
            </div>
            <div>
              <div className="text-sm font-semibold text-white">admin</div>
              <div className="text-xs text-muted">admin@crawler.local</div>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
