"use client";

import { useEffect } from "react";
import { reportError } from "@/lib/error-reporter";

/**
 * Captura errores que se escapan a los error boundaries de Next:
 *  - `window.onerror`           → excepciones síncronas no manejadas
 *  - `window.onunhandledrejection` → promises rechazadas sin .catch
 *
 * Los errores de React (renders, effects) ya van por los error.tsx
 * route-level, así que aquí solo cubrimos los huecos: useMutation
 * sin onError, fetch sin try/catch, librerías de terceros, scripts
 * inline, timers, polyfills, etc.
 *
 * Reusa el `reportError` existente, que tiene debounce por mensaje +
 * componente, así que reportes duplicados (e.g. React rethrowea como
 * window.error) no spamean al backend.
 */
export function GlobalErrorListener() {
  useEffect(() => {
    if (typeof window === "undefined") return;

    const onError = (event: ErrorEvent) => {
      const err =
        event.error instanceof Error
          ? event.error
          : new Error(event.message || "Unhandled error");
      reportError(err, "window.error");
    };

    const onUnhandledRejection = (event: PromiseRejectionEvent) => {
      const reason = event.reason;
      const err =
        reason instanceof Error
          ? reason
          : new Error(
              typeof reason === "string" ? reason : "Unhandled promise rejection",
            );
      reportError(err, "unhandledrejection");
    };

    window.addEventListener("error", onError);
    window.addEventListener("unhandledrejection", onUnhandledRejection);

    return () => {
      window.removeEventListener("error", onError);
      window.removeEventListener("unhandledrejection", onUnhandledRejection);
    };
  }, []);

  return null;
}
