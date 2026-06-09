/**
 * AI.BAN — Banner de transparencia Art. 50 Reglamento UE 2024/1689 (AI Act).
 *
 * Aparece la primera vez que el usuario interactúa con un agente LLM y
 * permanece dismissible (recordado en localStorage). Su objetivo es cumplir
 * la obligación de informar al usuario final de que está interactuando con
 * un sistema de IA.
 *
 * Texto canónico revisado por abogado SaaS (decisión humana 6).
 */
"use client";

import { Info, X } from "lucide-react";
import { useEffect, useState } from "react";

const STORAGE_KEY = "ai_disclosure_seen_v1";

interface Props {
    /** Si se proporciona, el banner se localiza por dominio (recordatorio por sección). */
    domain?: string;
    /** Texto extra opcional (ej.: nombre del agente). */
    extraNote?: string;
}

export function AIDisclosureBanner({ domain, extraNote }: Props) {
    const [visible, setVisible] = useState(false);

    useEffect(() => {
        if (typeof window === "undefined") return;
        const key = domain ? `${STORAGE_KEY}_${domain}` : STORAGE_KEY;
        const seen = window.localStorage.getItem(key);
        if (!seen) setVisible(true);
    }, [domain]);

    if (!visible) return null;

    const dismiss = () => {
        if (typeof window === "undefined") return;
        const key = domain ? `${STORAGE_KEY}_${domain}` : STORAGE_KEY;
        window.localStorage.setItem(key, "1");
        setVisible(false);
    };

    return (
        <div
            role="status"
            aria-live="polite"
            className="flex items-start gap-3 rounded-lg border border-primary/30 bg-primary/5 px-4 py-3 text-sm"
        >
            <Info className="mt-0.5 h-4 w-4 flex-shrink-0 text-primary" />
            <div className="flex-1">
                <p className="font-medium text-foreground">
                    Estás interactuando con un sistema de inteligencia artificial.
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                    Las respuestas se generan automáticamente y pueden contener errores.
                    Revisa la información antes de tomar decisiones, especialmente fiscales o
                    laborales. AutomatizaCore cumple el Reglamento UE 2024/1689 (AI Act).
                    {extraNote && <span className="ml-1">{extraNote}</span>}
                </p>
            </div>
            <button
                type="button"
                onClick={dismiss}
                aria-label="Cerrar aviso"
                className="rounded p-1 text-muted-foreground hover:bg-primary/10 hover:text-foreground transition"
            >
                <X className="h-4 w-4" />
            </button>
        </div>
    );
}
