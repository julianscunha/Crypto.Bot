import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Polls `fetcher` every `intervalMs` and exposes the latest data,
 * loading state, and any error. Keeps the previous successful data
 * visible while a refresh is in-flight or fails, so the UI doesn't
 * flash empty on a transient network hiccup.
 */
export function usePolling(fetcher, intervalMs = 3000) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const refresh = useCallback(async () => {
    try {
      const result = await fetcherRef.current();
      setData(result);
      setError(null);
    } catch (err) {
      setError(err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    let timeoutId;

    async function tick() {
      if (cancelled) return;
      await refresh();
      if (cancelled) return;
      timeoutId = setTimeout(tick, intervalMs);
    }

    tick();

    return () => {
      cancelled = true;
      clearTimeout(timeoutId);
    };
  }, [refresh, intervalMs]);

  return { data, error, isLoading, refresh };
}
