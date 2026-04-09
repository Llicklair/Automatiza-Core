/**
 * Frontend error reporter — sends errors to the backend for centralized logging.
 * Uses direct fetch (not the API client) to avoid circular dependencies.
 */

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ??
  (typeof window !== "undefined"
    ? `${window.location.protocol}//${window.location.hostname}:8080`
    : "http://127.0.0.1:8080");

const ENDPOINT = `${API_BASE}/api/v1/system/frontend-errors`;

/** Debounce: avoid flooding the backend with duplicate errors */
const _reported = new Set<string>();
const MAX_REPORTED = 50;

export function reportError(
  error: Error & { digest?: string },
  component?: string,
): void {
  if (typeof window === "undefined") return;

  const key = `${component}:${error.message}`;
  if (_reported.has(key)) return;
  if (_reported.size >= MAX_REPORTED) return;
  _reported.add(key);

  const payload = {
    message: error.message || "Unknown error",
    stack: error.stack?.slice(0, 5000) ?? null,
    url: window.location.href,
    component: component ?? null,
    digest: error.digest ?? null,
    timestamp: new Date().toISOString(),
  };

  // Fire-and-forget — never let reporting break the app
  try {
    fetch(ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }).catch(() => {
      /* silently ignore reporting failures */
    });
  } catch {
    /* silently ignore */
  }
}
