import { useState } from "react";
import { Globe, Loader2 } from "lucide-react";

export default function CustomCrawlerForm({ type, placeholder }) {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleCrawl = async (e) => {
    e.preventDefault();
    if (!url) return;
    
    setLoading(true);
    setResult(null);
    setError(null);
    
    try {
      const response = await fetch("/api/crawl-url", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url, type })
      });
      
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Crawl failed");
      
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rounded-lg border border-line bg-panel p-4">
      <div className="flex items-center gap-3 mb-3">
        <Globe className="h-4 w-4 text-indigo-400" aria-hidden="true" />
        <h2 className="text-sm font-bold text-white">Crawl Custom URL (AI-Powered)</h2>
      </div>
      <form onSubmit={handleCrawl} className="flex gap-2">
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder={placeholder}
          className="flex-1 rounded-md border border-line bg-sidebar px-3 py-2 text-sm text-white focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          required
        />
        <button
          type="submit"
          disabled={loading || !url}
          className="flex items-center gap-2 rounded-md bg-indigo-500 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-600 disabled:opacity-50"
        >
          {loading && <Loader2 className="h-4 w-4 animate-spin" />}
          {loading ? "Crawling..." : "Start Crawl"}
        </button>
      </form>
      
      {error && (
        <div className="mt-3 text-xs text-red-400 p-2 bg-red-400/10 rounded">
          Error: {error}
        </div>
      )}
      
      {result && (
        <div className="mt-3">
          <h3 className="text-xs font-semibold text-green-400 mb-1">Crawl Successful!</h3>
          <pre className="text-xs text-sky-200/80 bg-black/30 p-2 rounded max-h-60 overflow-y-auto whitespace-pre-wrap">
            {JSON.stringify(result.result, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
