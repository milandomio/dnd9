import { createContext, useContext } from "react";

/**
 * SSR data context.
 *
 * During server-side rendering (SSG build), this context is pre-populated
 * with route-specific data so components render with content.
 *
 * During client-side hydration, window.__SSR_DATA__ is read instead.
 * After hydration, components fall back to their own useEffect + fetch.
 */
const SSRDataContext = createContext<Record<string, any> | null>(null);

export function useSSRData<T>(key: string): T | null {
  const ctx = useContext(SSRDataContext);
  if (ctx) return (ctx[key] as T) ?? null;

  // Client hydration path: data was injected by SSG script into HTML
  if (typeof window !== "undefined") {
    const w = window as any;
    if (w.__SSR_DATA__ && w.__SSR_DATA__[key]) return w.__SSR_DATA__[key] as T;
  }

  return null;
}

export default SSRDataContext;
