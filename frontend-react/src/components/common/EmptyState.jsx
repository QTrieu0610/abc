import { Database } from "lucide-react";

export default function EmptyState({ title, message, children }) {
  return (
    <div className="rounded-lg border border-dashed border-line bg-panel/55 p-8 text-center">
      <Database className="mx-auto h-9 w-9 text-muted" aria-hidden="true" />
      <h3 className="mt-4 text-base font-semibold text-white">{title}</h3>
      {message && <p className="mx-auto mt-2 max-w-xl text-sm text-muted">{message}</p>}
      {children && <div className="mt-5">{children}</div>}
    </div>
  );
}
