/**
 * SEC.AUT — Settings de autonomía por dominio.
 *
 * El admin elige cómo actúan los agentes en cada dominio:
 *   AUTO    — sin confirmación
 *   CONFIRM — prepara y espera clic humano
 *   MANUAL  — solo sugiere
 *
 * Defaults consensuados (banking_write=MANUAL, accounting=CONFIRM, etc.)
 * se muestran con badge "Default" mientras no se haya editado.
 */
"use client";

import { useEffect, useState } from "react";
import { Loader2, RotateCcw, ShieldAlert } from "lucide-react";
import { api } from "@/lib/api";
import type { AutonomyMode, PolicyList } from "@/lib/api/autonomy";
import { useToastStore } from "@/stores/toast";

const DOMAIN_LABELS: Record<string, { name: string; hint: string }> = {
    banking_read: { name: "Banca · lectura", hint: "Consulta de saldos y movimientos." },
    banking_write: { name: "Banca · escritura", hint: "Transferencias y emisión de pagos." },
    accounting: { name: "Contabilidad", hint: "Asientos, conciliación, cierre." },
    billing: { name: "Facturación", hint: "Emisión de facturas y presupuestos." },
    crm: { name: "CRM", hint: "Clientes, oportunidades, actividades." },
    hr: { name: "RRHH", hint: "Empleados, nóminas, ausencias." },
    documents: { name: "Documentos", hint: "Indexación y consulta de docs." },
    email: { name: "Email", hint: "Lectura y envío de correos." },
    marketing: { name: "Marketing", hint: "Campañas y mensajes. En beta." },
    recruitment: { name: "Selección", hint: "Procesos de contratación. En beta." },
    rag: { name: "RAG / Conocimiento", hint: "Búsqueda semántica interna." },
    validators: { name: "Validadores", hint: "Pre-checks antes de ejecutar acciones." },
    uploads: { name: "Subidas", hint: "Ingesta de ficheros del usuario." },
};

const MODE_DESCRIPTIONS: Record<AutonomyMode, string> = {
    AUTO: "El agente actúa sin pedir confirmación.",
    CONFIRM: "El agente prepara la acción y espera tu clic.",
    MANUAL: "El agente solo sugiere; tú ejecutas a mano.",
};

const MODE_COLORS: Record<AutonomyMode, string> = {
    AUTO: "border-green-500/30 bg-green-500/5 text-green-500",
    CONFIRM: "border-amber-500/30 bg-amber-500/5 text-amber-500",
    MANUAL: "border-red-500/30 bg-red-500/5 text-red-500",
};

export default function AutonomyPage() {
    const [data, setData] = useState<PolicyList | null>(null);
    const [loading, setLoading] = useState(true);
    const [busy, setBusy] = useState<string | null>(null);
    const toast = useToastStore();

    async function load() {
        setLoading(true);
        try {
            const res = await api.autonomy.list();
            setData(res);
        } catch (e: any) {
            toast.show(`Error: ${e.message}`, "error");
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        load();
    }, []);

    async function changeMode(domain: string, mode: AutonomyMode) {
        setBusy(domain);
        try {
            await api.autonomy.set(domain, mode);
            await load();
        } catch (e: any) {
            toast.show(`Error: ${e.message}`, "error");
        } finally {
            setBusy(null);
        }
    }

    async function resetDomain(domain: string) {
        setBusy(domain);
        try {
            await api.autonomy.reset(domain);
            await load();
        } catch (e: any) {
            toast.show(`Error: ${e.message}`, "error");
        } finally {
            setBusy(null);
        }
    }

    if (loading || !data) {
        return (
            <div className="p-8 flex items-center gap-3 text-muted-foreground">
                <Loader2 className="w-4 h-4 animate-spin" /> Cargando política de autonomía…
            </div>
        );
    }

    return (
        <div className="p-6 max-w-4xl space-y-6">
            <header>
                <h1 className="text-2xl font-semibold text-foreground tracking-tight">
                    Autonomía de los agentes
                </h1>
                <p className="mt-1 text-sm text-muted-foreground">
                    Decide cuánto puede hacer cada agente sin tu confirmación. Los defaults son
                    conservadores: banca‑escritura requiere ejecución manual, contabilidad y
                    marketing piden confirmación humana.
                </p>
            </header>

            <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-4 flex items-start gap-3">
                <ShieldAlert className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" aria-hidden="true" />
                <p className="text-xs text-muted-foreground leading-relaxed">
                    Cambiar a <strong>AUTO</strong> en dominios sensibles (banca‑escritura, contabilidad)
                    delega ejecución total al agente. Solo recomendado si tienes auditoría y backups verificados.
                </p>
            </div>

            <ul className="space-y-2">
                {data.known_domains.map((domain) => {
                    const entry = data.policies[domain];
                    const meta = DOMAIN_LABELS[domain] ?? { name: domain, hint: "" };
                    const isBusy = busy === domain;
                    return (
                        <li
                            key={domain}
                            className="rounded-lg border border-border bg-card p-4 flex flex-col md:flex-row md:items-center gap-3"
                        >
                            <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2">
                                    <h2 className="text-sm font-medium text-foreground">{meta.name}</h2>
                                    {entry.is_default && (
                                        <span className="text-[10px] uppercase tracking-wider text-muted-foreground border border-border rounded px-1.5 py-0.5">
                                            default
                                        </span>
                                    )}
                                </div>
                                {meta.hint && (
                                    <p className="mt-0.5 text-xs text-muted-foreground">{meta.hint}</p>
                                )}
                                <p className="mt-1 text-xs text-muted-foreground italic">
                                    {MODE_DESCRIPTIONS[entry.mode]}
                                </p>
                            </div>

                            <div className="flex items-center gap-1.5" role="group" aria-label={`Modo de autonomía para ${meta.name}`}>
                                {(["AUTO", "CONFIRM", "MANUAL"] as AutonomyMode[]).map((mode) => {
                                    const active = entry.mode === mode;
                                    return (
                                        <button
                                            key={mode}
                                            type="button"
                                            onClick={() => changeMode(domain, mode)}
                                            disabled={isBusy || active}
                                            aria-pressed={active}
                                            className={`px-2.5 py-1 rounded-md border text-xs font-medium transition-colors disabled:cursor-default ${active
                                                ? MODE_COLORS[mode]
                                                : "border-border text-muted-foreground hover:text-foreground hover:border-primary"
                                                }`}
                                        >
                                            {mode}
                                        </button>
                                    );
                                })}
                                {!entry.is_default && (
                                    <button
                                        type="button"
                                        onClick={() => resetDomain(domain)}
                                        disabled={isBusy}
                                        aria-label={`Resetear ${meta.name} al valor por defecto`}
                                        className="ml-1 p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-background"
                                    >
                                        <RotateCcw className="w-3.5 h-3.5" />
                                    </button>
                                )}
                                {isBusy && <Loader2 className="w-3.5 h-3.5 animate-spin text-muted-foreground" aria-hidden="true" />}
                            </div>
                        </li>
                    );
                })}
            </ul>
        </div>
    );
}
