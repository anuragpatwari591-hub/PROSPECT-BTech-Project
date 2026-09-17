import { useCallback, useEffect, useState } from "react";
import { ApiError } from "./api";

export interface AsyncState<T> { data: T | null; error: ApiError | null; loading: boolean; reload: () => void }

/** Runs an async loader whenever `key` changes; ignores responses from outdated requests. */
export function useAsync<T>(loader: () => Promise<T>, key: unknown[]): AsyncState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);
  const reload = useCallback(() => setTick((t) => t + 1), []);

  useEffect(() => {
    let current = true;
    setLoading(true);
    loader()
      .then((result) => { if (current) { setData(result); setError(null); } })
      .catch((err) => {
        if (current) {
          setData(null);
          setError(err instanceof ApiError ? err : new ApiError(0, "UNKNOWN", String(err)));
        }
      })
      .finally(() => { if (current) setLoading(false); });
    return () => { current = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...key, tick]);

  return { data, error, loading, reload };
}
