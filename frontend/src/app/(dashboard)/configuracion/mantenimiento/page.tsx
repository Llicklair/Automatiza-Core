/**
 * Mantenimiento — herramientas de admin para operaciones puntuales:
 *
 *   - CONT.LOG: descargar bundle de diagnóstico ZIP (logs scrubbed + info)
 *   - MIG.6:    disparar manualmente el backfill Verifactu del tenant
 *
 * Pensado para soporte L1/L2 — el cliente cliquea el botón y nos envía
 * el ZIP sin compartir credenciales ni acceso remoto.
 */
"use client";

import { useState } from "react";
import {
    AlertCircle,
    CheckCircle2,
    Download,
    Loader2,
    Wrench,
} from "lucide-react";
import { system } from "@/lib/api/system";
import { useToastStore } from "@/stores/toast";
import { PageHeader } from "@/components/shared/PageHeader";
import { PageContainer } from "@/components/shared/PageContainer";

export default function MantenimientoPage() {
    const toast = useToastStore();
    const [bundleBusy, setBundleBusy] = useState(false);
    const [backfillBusy, setBackfillBusy] = useState(false);
    const [backfillNif, setBackfillNif] = useState("");
    const [backfillResult, setBackfillResult] = useState<unknown>(null);

    async function downloadBundle() {
        setBundleBusy(true);
        try {
            await system.downloadDiagnosticBundle();
            toast.show("Bundle descargado. Envíalo al soporte.", "success");
        } catch (e: any) {
            toast.show(`Error: ${e.message}`, "error");
        } finally {
            setBundleBusy(false);
        }
    }

    async function runBackfill() {
        if (!backfillNif.trim()) {
            toast.show("Indica el NIF emisor antes de iniciar.", "warning");
            return;
        }
        setBackfillBusy(true);
        try {
            const data = await system.runVerifactuBackfill(backfillNif);
            setBackfillResult(data);
            toast.show("Backfill ejecutado.", "success");
        } catch (e: any) {
            toast.show(`Error: ${e.message}`, "error");
        } finally {
            setBackfillBusy(false);
        }
    }

    return (
        <PageContainer width="3xl">
            <PageHeader
                title="Mantenimiento"
                description="Herramientas de operación puntual. Solo admin. Pensadas para diagnosticar problemas o repoblar datos tras una migración."
            />

            {/* Bundle de diagnóstico */}
            <section
                aria-labelledby="bundle-heading"
                className="rounded-lg border border-border bg-card p-5 space-y-3"
            >
                <header className="flex items-center gap-2">
                    <Download className="w-4 h-4 text-primary" aria-hidden="true" />
                    <h2 id="bundle-heading" className="text-sm font-semibold text-foreground">
                        Bundle de diagnóstico
                    </h2>
                </header>
                <p className="text-xs text-muted-foreground leading-relaxed">
                    Empaqueta un ZIP con los logs locales (PII redactada), versión, hash de schema y
                    precondiciones. Útil cuando soporte te pida información para investigar un fallo —
                    no incluye credenciales ni datos de clientes.
                </p>
                <button
                    type="button"
                    onClick={downloadBundle}
                    disabled={bundleBusy}
                    className="inline-flex items-center gap-1.5 px-4 py-2 rounded-md bg-primary text-foreground text-sm font-medium hover:bg-primary/90 disabled:opacity-50"
                >
                    {bundleBusy ? (
                        <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
                    ) : (
                        <Download className="w-4 h-4" aria-hidden="true" />
                    )}
                    Descargar bundle (.zip)
                </button>
            </section>

            {/* Backfill Verifactu */}
            <section
                aria-labelledby="backfill-heading"
                className="rounded-lg border border-border bg-card p-5 space-y-3"
            >
                <header className="flex items-center gap-2">
                    <Wrench className="w-4 h-4 text-primary" aria-hidden="true" />
                    <h2 id="backfill-heading" className="text-sm font-semibold text-foreground">
                        Backfill Verifactu
                    </h2>
                </header>
                <p className="text-xs text-muted-foreground leading-relaxed">
                    Reconstruye la cadena hash Verifactu de las facturas históricas (migradas desde
                    Holded/A3/CSV antes de la activación). Cada factura recibe su huella en orden
                    cronológico, marcada con
                    <code className="mx-1 px-1 py-0.5 bg-background border border-border rounded">
                        is_backfilled=true
                    </code>
                    para distinguirla del firmado en tiempo real (auditable ante AEAT).
                </p>
                <div className="flex items-start gap-2 px-3 py-2 rounded bg-amber-500/5 border border-amber-500/30">
                    <AlertCircle
                        className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5"
                        aria-hidden="true"
                    />
                    <p className="text-xs text-muted-foreground leading-relaxed">
                        Un NIF emisor incorrecto invalida toda la cadena. Verifica el NIF de tu empresa
                        antes de ejecutar. La operación es idempotente — si ya hay facturas con cadena,
                        las salta.
                    </p>
                </div>
                <div className="flex items-end gap-2">
                    <label className="flex-1">
                        <span className="text-xs text-muted-foreground">NIF emisor</span>
                        <input
                            type="text"
                            value={backfillNif}
                            onChange={(e) => setBackfillNif(e.target.value)}
                            placeholder="B12345678"
                            className="mt-1 w-full px-3 py-2 rounded-md bg-background border border-border text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                        />
                    </label>
                    <button
                        type="button"
                        onClick={runBackfill}
                        disabled={backfillBusy || !backfillNif.trim()}
                        className="px-4 py-2 rounded-md bg-primary text-foreground text-sm font-medium hover:bg-primary/90 disabled:opacity-50 flex items-center gap-1.5"
                    >
                        {backfillBusy ? (
                            <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
                        ) : (
                            <Wrench className="w-4 h-4" aria-hidden="true" />
                        )}
                        Ejecutar backfill
                    </button>
                </div>
                {backfillResult ? (
                    <div className="rounded-md bg-green-500/5 border border-green-500/30 p-3 flex items-start gap-2">
                        <CheckCircle2
                            className="w-4 h-4 text-green-500 flex-shrink-0 mt-0.5"
                            aria-hidden="true"
                        />
                        <pre className="text-[10px] tabular-nums text-foreground overflow-x-auto">
                            {JSON.stringify(backfillResult, null, 2)}
                        </pre>
                    </div>
                ) : null}
            </section>
        </PageContainer>
    );
}
