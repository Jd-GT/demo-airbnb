"use client";

import { useEffect, useRef, useState } from "react";

type AsyncState<T> = {
  data: T | null;
  error: string | null;
  loading: boolean;
  reload: () => void;
};

export function useAsyncData<T>(
  loader: () => Promise<T>,
  deps: ReadonlyArray<unknown>,
): AsyncState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [reloadToken, setReloadToken] = useState(0);
  const loaderRef = useRef(loader);

  loaderRef.current = loader;

  useEffect(() => {
    let cancelled = false;

    const runLoader = async () => {
      setLoading(true);
      setError(null);

      try {
        const nextData = await loaderRef.current();
        if (!cancelled) {
          setData(nextData);
        }
      } catch (caughtError) {
        if (!cancelled) {
          const message =
            caughtError instanceof Error
              ? caughtError.message
              : "Ocurrio un error inesperado al consultar el backend.";
          setError(message);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void runLoader();

    return () => {
      cancelled = true;
    };
  }, [...deps, reloadToken]);

  return {
    data,
    error,
    loading,
    reload: () => setReloadToken((value) => value + 1),
  };
}
