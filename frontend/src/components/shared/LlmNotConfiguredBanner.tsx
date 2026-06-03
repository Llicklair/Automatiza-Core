"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Sparkles, AlertTriangle } from "lucide-react";
import { api } from "@/lib/api";

/**
 * Aviso cuando el tenant no tiene ninguna clave de IA configurada.
 *
 * Modelo BYOK (cada cuenta trae su propia API key): sin clave, los agentes no
 * funcionan. Este banner lo hace visible y enlaza a Configuración → Claves API,
 * en vez de dejar que el usuario choque con un error críptico al usar la IA.
 *
 * Se muestra en las superficies principales de IA (dashboard, mi-equipo). Si la
 * llamada falla, no molesta (no se muestra).
 */
export function LlmNotConfiguredBanner() {
    const [show, setShow] = useState(false);

    useEffect(() => {
        api.tenant
            .getLlmConfig()
            .then(cfg => {
                const hasKey = Object.values(cfg.providers || {}).some(p => p.has_key);
                setShow(!hasKey);
            })
            .catch(() => {});
    }, []);

    if (!show) return null;

    return (
        <div className="flex items-center gap-3 rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm">
            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
            <span className="flex-1 text-foreground">
                La IA aún no está configurada. Añade tu clave de API para que tus agentes
                puedan trabajar.
            </span>
            <Link
                href="/configuracion/api-keys"
                className="shrink-0 inline-flex items-center gap-1.5 rounded-lg bg-amber-500/20 px-3 py-1.5 font-medium text-amber-300 hover:bg-amber-500/30 transition-colors">
                <Sparkles className="w-4 h-4" /> Configurar IA
            </Link>
        </div>
    );
}
