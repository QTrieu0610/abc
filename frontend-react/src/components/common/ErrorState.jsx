import { AlertTriangle } from "lucide-react";

export default function ErrorState({ error, title = "Unable to load data", onRetry }) {
  const message =
    error?.status === 0
      ? "Backend API is not reachable. Please start FastAPI server."
      : error?.status === 404
        ? "This backend endpoint is not connected yet."
        : error?.message || "Unexpected response from backend.";

  return (
    <div className="rounded-lg border border-red-400/25 bg-red-500/10 p-6">
      <div className="flex items-start gap-3">
        <AlertTriangle className="mt-0.5 h-5 w-5 text-red-300" aria-hidden="true" />
        <div>
          <h3 className="font-semibold text-red-100">{title}</h3>
          <p className="mt-1 text-sm text-red-200/80">{message}</p>
          {onRetry && (
            <button
              type="button"
              onClick={() => onRetry()}
              className="mt-4 rounded border border-red-300/30 px-3 py-1.5 text-sm font-semibold text-red-100 hover:bg-red-300/10"
            >
              Retry
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
