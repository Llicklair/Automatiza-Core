"use client";

import { useState } from "react";
import { KeyRound, ExternalLink } from "lucide-react";
import { licenseApi } from "@/lib/api/license";
import { useLicenseStore } from "@/stores/license";

export default function LicenseModal() {
    const { open, hide } = useLicenseStore();
    const [key, setKey] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [success, setSuccess] = useState(false);

    if (!open) return null;

    async function handleActivate() {
        const trimmed = key.trim();
        if (!trimmed) return;
        setLoading(true);
        setError("");
        try {
            const res = await licenseApi.activate(trimmed);
            if (res.ok) {
                setSuccess(true);
                setTimeout(() => window.location.reload(), 1500);
            } else {
                setError(res.reason ?? "Clave no válida.");
            }
        } catch {
            setError("No se pudo conectar con el servidor de licencias.");
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/70 backdrop-blur-sm">
            <div
                role="dialog"
                aria-modal="true"
                aria-labelledby="license-modal-title"
                className="w-full max-w-md rounded-2xl border border-border bg-card shadow-2xl overflow-hidden"
            >
                {/* Header */}
                <div className="flex items-center px-5 py-4 border-b border-border gap-2">
                    <KeyRound className="w-5 h-5 text-indigo-400" />
                    <span id="license-modal-title" className="font-semibold text-foreground text-sm">
                        Activar licencia
                    </span>
                </div>

                {/* Body */}
                <div className="px-5 py-5 flex flex-col gap-4">
                    {success ? (
                        <p className="text-sm text-emerald-400 text-center py-4">
                            ✓ Licencia activada correctamente. Recargando…
                        </p>
                    ) : (
                        <>
                            <p className="text-sm text-muted-foreground leading-relaxed">
                                Introduce la clave de licencia que recibiste por email tras tu compra.
                                Tiene el formato <span className="font-mono text-foreground">AP-P-XXXX-XXXX-XX</span>.
                            </p>

                            <input
                                type="text"
                                value={key}
                                onChange={(e) => setKey(e.target.value.toUpperCase())}
                                onKeyDown={(e) => e.key === "Enter" && handleActivate()}
                                placeholder="AP-P-XXXX-XXXX-XX"
                                className="w-full rounded-xl border border-border bg-background px-4 py-2.5 font-mono text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-indigo-500"
                                autoFocus
                            />

                            {error && (
                                <p className="text-xs text-red-400">{error}</p>
                            )}

                            <a
                                href="https://llicklair.github.io/Automatiza-core_landing/#precios"
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
                            >
                                ¿No tienes licencia? Ver planes
                                <ExternalLink className="w-3 h-3" />
                            </a>
                        </>
                    )}
                </div>

                {/* Footer */}
                {!success && (
                    <div className="px-5 pb-5">
                        <button
                            onClick={handleActivate}
                            disabled={loading || !key.trim()}
                            className="w-full py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-medium transition-colors"
                        >
                            {loading ? "Activando…" : "Activar"}
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}
