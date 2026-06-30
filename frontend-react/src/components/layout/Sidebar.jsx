import {
  Bell,
  ChevronLeft,
  Database,
  FileText,
  Gauge,
  Home,
  Moon,
  RadioTower,
  Settings,
  ShieldAlert,
  ShieldCheck,
  UserCheck,
} from "lucide-react";
import { NavLink } from "react-router-dom";
import { useCallback } from "react";
import { getHitlCases } from "../../api/hitlApi";
import { useAutoRefresh } from "../../hooks/useAutoRefresh";

export default function Sidebar({ collapsed, onToggle }) {
  const fetchHitl = useCallback(() => getHitlCases(), []);
  const { data } = useAutoRefresh(fetchHitl, 15000);
  const hitlCount = Number(data?.open_count || 0);
  const items = [
    { label: "Overview", to: "/overview", icon: Home },
    { label: "Manage Sources", to: "/manage-sources", icon: Database },
    { label: "Crawl Jobs", to: "/crawl-jobs", icon: Gauge },
    { label: "Sessions & Identities", to: "/sessions", icon: UserCheck },
    { label: "Blocking Signals", to: "/blocking-signals", icon: ShieldAlert },
    { label: "HITL Review", to: "/hitl", icon: RadioTower, count: hitlCount },
    { label: "Extracted Data", to: "/extracted-data", icon: Database },
    { label: "Notifications", to: "/notifications", icon: Bell, count: 0 },
    { label: "Audit Logs", to: "/audit-logs", icon: FileText },
    { label: "Settings", to: "/settings", icon: Settings },
  ];

  return (
    <aside
      className={`fixed inset-y-0 left-0 z-40 flex border-r border-line bg-sidebar transition-all duration-200 ${collapsed ? "w-[76px]" : "w-[260px]"}`}
    >
      <div className="flex w-full flex-col">
        <NavLink to="/overview" className="flex h-[70px] items-center gap-3 border-b border-line px-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-sky-500 text-white">
            <ShieldCheck className="h-5 w-5" aria-hidden="true" />
          </div>
          {!collapsed && (
            <div className="min-w-0">
              <div className="truncate text-sm font-bold text-white">Adaptive Anti-Bot</div>
              <div className="truncate text-xs text-sky-200/80">AI Crawler</div>
            </div>
          )}
        </NavLink>

        <nav className="flex-1 space-y-1 overflow-y-auto px-2 py-4">
          {items.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `group flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition ${
                  isActive
                    ? "bg-sky-500/20 text-cyan"
                    : "text-sky-100 hover:bg-sky-500/10 hover:text-white"
                }`
              }
            >
              <item.icon className="h-4 w-4 shrink-0" aria-hidden="true" />
              {!collapsed && <span className="truncate">{item.label}</span>}
              {!collapsed && item.count > 0 && (
                <span className="ml-auto rounded-full bg-indigo-500 px-2 py-0.5 text-xs font-bold text-white">
                  {item.count}
                </span>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="space-y-1 border-t border-line px-2 py-4">
          <button
            type="button"
            className="flex w-full items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium text-sky-100 hover:bg-sky-500/10 hover:text-white"
          >
            <Moon className="h-4 w-4" aria-hidden="true" />
            {!collapsed && <span>Light Mode</span>}
          </button>
          <button
            type="button"
            onClick={onToggle}
            className="flex w-full items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium text-sky-100 hover:bg-sky-500/10 hover:text-white"
          >
            <ChevronLeft className={`h-4 w-4 transition ${collapsed ? "rotate-180" : ""}`} aria-hidden="true" />
            {!collapsed && <span>Collapse</span>}
          </button>
        </div>
      </div>
    </aside>
  );
}
