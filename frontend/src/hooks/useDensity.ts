/**
 * UI.DEN — preferencia de densidad de UI persistida en localStorage.
 *
 * Dos modos:
 *   - `comfortable` (default) — prioriza legibilidad. Apto para PYMEs.
 *   - `compact`               — densifica spacing. Apto para gestorías
 *                                con muchos registros en pantalla.
 *
 * El provider en root layout aplica `data-density="..."` al <html> al
 * cargar, antes de hidratar React, para evitar flash visual.
 */
"use client";

import { useEffect, useState } from "react";

export type Density = "comfortable" | "compact";

const STORAGE_KEY = "ui_density_v1";
const DEFAULT_DENSITY: Density = "comfortable";

export function getStoredDensity(): Density {
    if (typeof window === "undefined") return DEFAULT_DENSITY;
    const v = window.localStorage.getItem(STORAGE_KEY);
    return v === "compact" ? "compact" : "comfortable";
}

export function applyDensity(density: Density): void {
    if (typeof document === "undefined") return;
    document.documentElement.setAttribute("data-density", density);
}

export function useDensity(): {
    density: Density;
    setDensity: (d: Density) => void;
} {
    const [density, setDensityState] = useState<Density>(DEFAULT_DENSITY);

    useEffect(() => {
        const stored = getStoredDensity();
        setDensityState(stored);
        applyDensity(stored);
    }, []);

    function setDensity(d: Density) {
        setDensityState(d);
        try {
            window.localStorage.setItem(STORAGE_KEY, d);
        } catch {
            // localStorage puede fallar en modo private; no es fatal.
        }
        applyDensity(d);
    }

    return { density, setDensity };
}
