import { useCallback, useEffect, useRef, useState } from "react";

export function useAutoRefresh(fetcher, intervalMs, enabled = true) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const fetcherRef = useRef(fetcher);

  useEffect(() => {
    fetcherRef.current = fetcher;
  }, [fetcher]);

  const refresh = useCallback(async ({ silent = false, isUserAction = false } = {}) => {
    if (!silent) setRefreshing(true);
    setError(null);
    try {
      const result = await fetcherRef.current(isUserAction);
      setData(result);
      return result;
    } catch (nextError) {
      setError(nextError);
      return null;
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    if (!enabled) return undefined;
    let cancelled = false;

    const run = async (silent = false) => {
      if (cancelled || document.hidden) return;
      await refresh({ silent });
    };

    run(false);
    
    // Auto-refresh disabled by user request - only manual refresh via the refresh() function
    // const id = window.setInterval(() => run(true), intervalMs);
    
    const handleVisibility = () => {
      // Optional: you can also disable fetch on visibility change if the user wants strict manual-only
      // if (!document.hidden) run(true);
    };

    document.addEventListener("visibilitychange", handleVisibility);
    return () => {
      cancelled = true;
      // window.clearInterval(id);
      document.removeEventListener("visibilitychange", handleVisibility);
    };
  }, [enabled, intervalMs, refresh]);

  return { data, loading, refreshing, error, refresh };
}
