"use client";

import { useEffect, useRef } from "react";

interface UsePollingOptions {
    /** Si es false, no se programa ningún intervalo. Default: true. */
    enabled?: boolean;
    /**
     * Pausa el polling cuando la pestaña está oculta y, al volver a ser
     * visible, dispara `fn()` inmediatamente (catch-up) antes de reanudar
     * el intervalo. Default: true.
     *
     * NO usar para polls que esperan a que el usuario complete algo en
     * otra pestaña (p. ej. redirecciones OAuth): se pausarían justo
     * cuando deben seguir comprobando.
     */
    pauseWhenHidden?: boolean;
}

/**
 * Polling compartido (auditoría UIX #10). Sustituye a los `setInterval`
 * ad-hoc de los hooks de página.
 *
 * - `fn` vive en un ref: puede ser una closure nueva en cada render sin
 *   reiniciar el intervalo.
 * - No hace carga inicial — los callsites ya la hacen en su propio efecto.
 */
export function usePolling(
    fn: () => void,
    intervalMs: number,
    { enabled = true, pauseWhenHidden = true }: UsePollingOptions = {},
): void {
    const fnRef = useRef(fn);
    useEffect(() => {
        fnRef.current = fn;
    });

    useEffect(() => {
        if (!enabled) return;

        let id: ReturnType<typeof setInterval> | null = null;

        const start = () => {
            if (id === null) id = setInterval(() => fnRef.current(), intervalMs);
        };
        const stop = () => {
            if (id !== null) {
                clearInterval(id);
                id = null;
            }
        };

        const onVisibility = () => {
            if (document.visibilityState === "hidden") {
                stop();
            } else {
                fnRef.current(); // catch-up al volver a la pestaña
                start();
            }
        };

        if (pauseWhenHidden) {
            document.addEventListener("visibilitychange", onVisibility);
            if (document.visibilityState !== "hidden") start();
        } else {
            start();
        }

        return () => {
            if (pauseWhenHidden) {
                document.removeEventListener("visibilitychange", onVisibility);
            }
            stop();
        };
    }, [intervalMs, enabled, pauseWhenHidden]);
}
