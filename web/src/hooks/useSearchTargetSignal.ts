import { useEffect, useState } from 'react';

/** Event fired by the navbar when a search hit points at the page already open. */
export const SEARCH_TARGET_EVENT = 'df5:search-target';

/**
 * Re-runs a page's "focus the search result" effect when the navbar re-emits a
 * hit for the page we are already on. Navigating to an identical URL is a no-op,
 * so the `?item=` / `?quest=` effect would otherwise never fire again.
 *
 * Returns a counter to put in that effect's dependency list.
 */
export function useSearchTargetSignal() {
  const [signal, setSignal] = useState(0);

  useEffect(() => {
    const handler = () => setSignal((value) => value + 1);
    window.addEventListener(SEARCH_TARGET_EVENT, handler);
    return () => window.removeEventListener(SEARCH_TARGET_EVENT, handler);
  }, []);

  return signal;
}
