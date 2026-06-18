import { useState } from "react";
import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import Topbar from "./Topbar";

export default function AppLayout() {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="min-h-screen bg-app text-slate-100">
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed((value) => !value)} />
      <Topbar collapsed={collapsed} />
      <main
        className={`min-h-screen pt-[70px] transition-all duration-200 ${collapsed ? "pl-[76px]" : "pl-[260px]"}`}
      >
        <div className="mx-auto max-w-[1480px] px-5 py-6">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
