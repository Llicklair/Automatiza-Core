"use client";

import { useEffect, useRef } from "react";
import { reportError } from "@/lib/error-reporter";
import { AI_DEGRADATION_MESSAGE, isConnectivityError } from "@/lib/api/errors";
import { useToastStore } from "@/stores/toast";

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
  // Throttle del toast de degradación: una sola alerta cada 30 s aunque lleguen
  // múltiples fallos de red en ráfaga (evita spam visual).
  const lastDegradationToastRef = useRef<number>(0);

  useEffect(() => {
    if (typeof window === "undefined") return;

    // Traduce un error de conectividad/IA en un aviso accionable para el usuario
    // (SCOPE.md §5.2). El resto de errores solo se reportan al backend.
    const surfaceDegradation = (err: unknown) => {
      if (!isConnectivityError(err)) return;
      const now = Date.now();
      if (now - lastDegradationToastRef.current < 30_000) return;
      lastDegradationToastRef.current = now;
      useToastStore.getState().show(AI_DEGRADATION_MESSAGE, "warning");
    };

    const onError = (event: ErrorEvent) => {
      const err =
        event.error instanceof Error
          ? event.error
          : new Error(event.message || "Unhandled error");
      surfaceDegradation(event.error);
      reportError(err, "window.error");
    };

    const onUnhandledRejection = (event: PromiseRejectionEvent) => {
      const reason = event.reason;
      surfaceDegradation(reason);
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
