/**
 * DIS.UPD — selector de canal de actualización (stable / beta).
 *
 * Usa el bridge IPC expuesto por `desktop/preload.js`:
 *   - `window.electronAPI.getUpdateChannel()`
 *   - `window.electronAPI.setUpdateChannel(channel)`
 *
 * Si la app corre fuera de Electron (browser dev), se oculta — la
 * elección de canal solo aplica al binario empaquetado.
 */
"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, GitBranch, Loader2 } from "lucide-react";
import { useToastStore } from "@/stores/toast";

type Channel = "stable" | "beta";

function _api() {
    if (typeof window === "undefined") return null;
    return window.electronAPI ?? null;
}

export function UpdateChannelSelector() {
    const toast = useToastStore();
    const [channel, setChannel] = useState<Channel | null>(null);
    const [busy, setBusy] = useState(false);

    useEffect(() => {
        const api = _api();
        if (!api?.getUpdateChannel) return;
        api.getUpdateChannel().then(setChannel).catch(() => setChannel("stable"));
    }, []);

    if (typeof window !== "undefined" && !_api()?.getUpdateChannel) {
        // Modo browser dev: no aplicable.
        return null;
    }

    if (channel === null) {
        return (
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <Loader2 className="w-3 h-3 animate-spin" aria-hidden="true" />
                Cargando canal de actualización…
            </div>
        );
    }

    async function choose(next: Channel) {
        if (next === channel) return;
        setBusy(true);
        try {
            const res = await _api()?.setUpdateChannel?.(next);
            if (res?.ok) {
                setChannel(res.channel);
                toast.show(
                    next === "beta"
                        ? "Canal beta activado — recibirás pre-releases."
                        : "Canal estable activado.",
                    "success",
                );
            }
        } catch (e: any) {
            toast.show(`Error: ${e.message}`, "error");
        } finally {
            setBusy(false);
        }
    }

    const options: { value: Channel; title: string; description: string }[] = [
        {
            value: "stable",
            title: "Estable",
            description: "Releases finales. Recomendado para uso diario.",
        },
        {
            value: "beta",
            title: "Beta",
            description: "Pre-releases. Acceso temprano a features con más riesgo.",
        },
    ];

    return (
        <section aria-labelledby="update-channel-heading" className="space-y-3">
            <div className="flex items-center gap-2">
                <GitBranch className="w-4 h-4 text-primary" aria-hidden="true" />
                <h3 id="update-channel-heading" className="text-sm font-medium text-foreground">
                    Canal de actualización
                </h3>
            </div>
            <div role="radiogroup" aria-labelledby="update-channel-heading" className="space-y-2">
                {options.map((opt) => {
                    const active = channel === opt.value;
                    return (
                        <button
                            key={opt.value}
                            type="button"
                            role="radio"
                            aria-checked={active}
                            onClick={() => choose(opt.value)}
                            disabled={busy || active}
                            className={`w-full text-left p-3 rounded-lg border transition-colors ${active
                                ? "border-primary bg-primary/5 ring-1 ring-primary/30"
                                : "border-border bg-card hover:border-primary/50"
                                }`}
                        >
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm font-semibold text-foreground">{opt.title}</p>
                                    <p className="text-xs text-muted-foreground mt-0.5">{opt.description}</p>
                                </div>
                                {active && (
                                    <CheckCircle2 className="w-4 h-4 text-primary" aria-label="Activo" />
                                )}
                            </div>
                        </button>
                    );
                })}
            </div>
        </section>
    );
}
