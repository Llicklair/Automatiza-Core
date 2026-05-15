/**
 * MOD.130/347/390/111/190 — preview de liquidaciones AEAT calculadas.
 *
 * Cada card invoca el endpoint que ejecuta `build_modelo_*_data()` con los
 * datos del tenant y muestra el JSON resultado en formato legible. Los
 * modelos están **calculados** pero NO presentados — la presentación real
 * va por PRES.303 / PRES.MOD1 / PRES.MOD2 cuando DEC.14 (alta colaborador
 * social) esté completo.
 */
"use client";

import { useState } from "react";
import { ChevronDown, Loader2, RefreshCw } from "lucide-react";
import { api } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { useToastStore } from "@/stores/toast";

type ModeloKey = "130" | "111" | "190" | "347" | "390";

interface ModeloMeta {
    key: ModeloKey;
    titulo: string;
    subtitulo: string;
    descripcion: string;
    periodicidad: "trimestral" | "anual";
}

const MODELOS: ModeloMeta[] = [
    {
        key: "130",
        titulo: "Modelo 130",
        subtitulo: "IRPF · Estimación directa",
        descripcion: "Pago fraccionado trimestral. 20% del beneficio acumulado.",
        periodicidad: "trimestral",
    },
    {
        key: "111",
        titulo: "Modelo 111",
        subtitulo: "Retenciones trabajadores",
        descripcion: "Retenciones IRPF de empleados, trimestral.",
        periodicidad: "trimestral",
    },
    {
        key: "190",
        titulo: "Modelo 190",
        subtitulo: "Resumen anual retenciones",
        descripcion: "Consolidación de 12 meses de nóminas (4×111).",
        periodicidad: "anual",
    },
    {
        key: "347",
        titulo: "Modelo 347",
        subtitulo: "Operaciones con terceros",
        descripcion: "Declaración informativa de contrapartes >3.005,06€/año.",
        periodicidad: "anual",
    },
    {
        key: "390",
        titulo: "Modelo 390",
        subtitulo: "Resumen anual IVA",
        descripcion: "Consolidación de los 4 modelos 303 del ejercicio.",
        periodicidad: "anual",
    },
];

const CURRENT_YEAR = new Date().getFullYear();

export default function ModelosAeatPage() {
    const toast = useToastStore();
    const [ejercicio, setEjercicio] = useState(CURRENT_YEAR);
    const [trimestre, setTrimestre] = useState(1);
    const [busy, setBusy] = useState<ModeloKey | null>(null);
    const [results, setResults] = useState<Record<ModeloKey, unknown>>({} as any);

    async function generate(modelo: ModeloKey) {
        setBusy(modelo);
        try {
            let data: unknown;
            switch (modelo) {
                case "130":
                    data = await api.modelosAeat.m130(trimestre, ejercicio);
                    break;
                case "111":
                    data = await api.modelosAeat.m111(trimestre, ejercicio);
                    break;
                case "190":
                    data = await api.modelosAeat.m190(ejercicio);
                    break;
                case "347":
                    data = await api.modelosAeat.m347(ejercicio);
                    break;
                case "390":
                    data = await api.modelosAeat.m390(ejercicio);
                    break;
            }
            setResults((r) => ({ ...r, [modelo]: data }));
            toast.show(`Modelo ${modelo} calculado.`, "success");
        } catch (e: any) {
            toast.show(`Error: ${e.message}`, "error");
        } finally {
            setBusy(null);
        }
    }

    return (
        <div className="p-6 max-w-5xl space-y-6">
            <PageHeader
                title="Modelos AEAT — preview"
                description="Liquidaciones calculadas con tus datos del periodo seleccionado. La presentación telemática real (PRES.303 / PRES.MOD1 / PRES.MOD2) requiere alta como colaborador social en AEAT."
            />

            {/* Periodo */}
            <section className="rounded-lg border border-border bg-card p-4 space-y-3">
                <h2 className="text-sm font-medium text-foreground">Periodo fiscal</h2>
                <div className="flex flex-wrap items-center gap-3">
                    <label className="text-xs text-muted-foreground flex items-center gap-2">
                        Ejercicio
                        <input
                            type="number"
                            min={2020}
                            max={2099}
                            value={ejercicio}
                            onChange={(e) => setEjercicio(Number(e.target.value))}
                            className="w-24 px-2 py-1 rounded-md bg-background border border-border text-foreground text-sm"
                        />
                    </label>
                    <label className="text-xs text-muted-foreground flex items-center gap-2">
                        Trimestre (130, 111)
                        <select
                            value={trimestre}
                            onChange={(e) => setTrimestre(Number(e.target.value))}
                            className="px-2 py-1 rounded-md bg-background border border-border text-foreground text-sm"
                        >
                            <option value={1}>1T</option>
                            <option value={2}>2T</option>
                            <option value={3}>3T</option>
                            <option value={4}>4T</option>
                        </select>
                    </label>
                </div>
            </section>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {MODELOS.map((m) => {
                    const isBusy = busy === m.key;
                    const result = results[m.key];
                    return (
                        <article
                            key={m.key}
                            className="rounded-lg border border-border bg-card p-5"
                        >
                            <header className="flex items-start justify-between gap-2 mb-2">
                                <div className="min-w-0">
                                    <h3 className="text-base font-semibold text-foreground">
                                        {m.titulo}
                                    </h3>
                                    <p className="text-xs text-muted-foreground">{m.subtitulo}</p>
                                </div>
                                <span className="text-[10px] uppercase tracking-wider text-muted-foreground flex-shrink-0">
                                    {m.periodicidad}
                                </span>
                            </header>
                            <p className="text-xs text-muted-foreground leading-relaxed mb-3">
                                {m.descripcion}
                            </p>
                            <button
                                type="button"
                                onClick={() => generate(m.key)}
                                disabled={isBusy}
                                className="w-full inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-md bg-primary text-foreground text-sm font-medium hover:bg-primary/90 disabled:opacity-50"
                            >
                                {isBusy ? (
                                    <Loader2 className="w-3.5 h-3.5 animate-spin" aria-hidden="true" />
                                ) : result ? (
                                    <RefreshCw className="w-3.5 h-3.5" aria-hidden="true" />
                                ) : null}
                                {result ? "Recalcular" : "Calcular liquidación"}
                            </button>

                            {result !== undefined && (
                                <details className="mt-3" open>
                                    <summary className="text-xs font-medium text-muted-foreground cursor-pointer flex items-center gap-1">
                                        <ChevronDown className="w-3 h-3" aria-hidden="true" />
                                        Resultado JSON
                                    </summary>
                                    <pre className="mt-2 text-[10px] bg-background border border-border rounded p-2 overflow-x-auto max-h-64 text-foreground tabular-nums">
                                        {JSON.stringify(result, null, 2)}
                                    </pre>
                                </details>
                            )}
                        </article>
                    );
                })}
            </div>

            <p className="text-xs text-muted-foreground">
                Para presentar telemáticamente cualquiera de estos modelos, AutomatizaPyme
                necesita estar dada de alta como colaborador social en AEAT y disponer del
                certificado de representación FNMT. Mientras tanto, puedes usar el preview
                para revisar las cifras antes de presentar por tu cuenta en Sede.
            </p>
        </div>
    );
}
