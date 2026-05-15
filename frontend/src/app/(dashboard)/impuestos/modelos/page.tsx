/**
 * MOD.130/347/390/111/190 — preview visual de liquidaciones AEAT.
 *
 * Cada card renderiza el resultado de `build_modelo_*_data()` con un
 * layout específico por modelo (no JSON dump):
 *   - 130: hero con resultado a ingresar + grid (ingresos/gastos/beneficio)
 *   - 347: tabla de contrapartes declarables
 *   - 390: dos columnas devengado/deducible con tipos IVA
 *   - 111/190: lista de perceptores con base + retención
 */
"use client";

import { useState } from "react";
import {
    BookCheck,
    Building2,
    FileText,
    Loader2,
    RefreshCw,
    Users,
} from "lucide-react";
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
        descripcion: "Contrapartes con operaciones >3.005,06€/año.",
        periodicidad: "anual",
    },
    {
        key: "390",
        titulo: "Modelo 390",
        subtitulo: "Resumen anual IVA",
        descripcion: "Consolidación de los 4 modelos 303.",
        periodicidad: "anual",
    },
];

const CURRENT_YEAR = new Date().getFullYear();

function fmtEUR(n: number): string {
    return n.toLocaleString("es-ES", {
        style: "currency",
        currency: "EUR",
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    });
}

function fmtPct(n: number): string {
    return `${n}%`;
}

export default function ModelosAeatPage() {
    const toast = useToastStore();
    const [ejercicio, setEjercicio] = useState(CURRENT_YEAR);
    const [trimestre, setTrimestre] = useState(1);
    const [busy, setBusy] = useState<ModeloKey | null>(null);
    const [results, setResults] = useState<Partial<Record<ModeloKey, any>>>({});

    async function generate(modelo: ModeloKey) {
        setBusy(modelo);
        try {
            let data: unknown;
            switch (modelo) {
                case "130": data = await api.modelosAeat.m130(trimestre, ejercicio); break;
                case "111": data = await api.modelosAeat.m111(trimestre, ejercicio); break;
                case "190": data = await api.modelosAeat.m190(ejercicio); break;
                case "347": data = await api.modelosAeat.m347(ejercicio); break;
                case "390": data = await api.modelosAeat.m390(ejercicio); break;
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
                description="Liquidaciones calculadas con tus datos del periodo seleccionado. La presentación telemática real requiere alta como colaborador social en AEAT."
            />

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

            <div className="space-y-4">
                {MODELOS.map((m) => {
                    const isBusy = busy === m.key;
                    const data = results[m.key];
                    return (
                        <article
                            key={m.key}
                            className="rounded-lg border border-border bg-card p-5"
                        >
                            <header className="flex items-start justify-between gap-2 mb-4">
                                <div className="min-w-0">
                                    <h3 className="text-base font-semibold text-foreground">
                                        {m.titulo}
                                    </h3>
                                    <p className="text-xs text-muted-foreground">{m.subtitulo}</p>
                                    <p className="text-xs text-muted-foreground mt-1">{m.descripcion}</p>
                                </div>
                                <div className="flex items-center gap-2 flex-shrink-0">
                                    <span className="text-[10px] uppercase tracking-wider text-muted-foreground">
                                        {m.periodicidad}
                                    </span>
                                    <button
                                        type="button"
                                        onClick={() => generate(m.key)}
                                        disabled={isBusy}
                                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-primary text-foreground text-xs font-medium hover:bg-primary/90 disabled:opacity-50"
                                    >
                                        {isBusy ? (
                                            <Loader2 className="w-3 h-3 animate-spin" aria-hidden="true" />
                                        ) : data ? (
                                            <RefreshCw className="w-3 h-3" aria-hidden="true" />
                                        ) : null}
                                        {data ? "Recalcular" : "Calcular"}
                                    </button>
                                </div>
                            </header>

                            {data && m.key === "130" && <Modelo130View data={data} />}
                            {data && m.key === "111" && <Modelo111View data={data} />}
                            {data && m.key === "190" && <Modelo190View data={data} />}
                            {data && m.key === "347" && <Modelo347View data={data} />}
                            {data && m.key === "390" && <Modelo390View data={data} />}
                        </article>
                    );
                })}
            </div>

            <p className="text-xs text-muted-foreground italic">
                La presentación telemática real (PRES.303 / PRES.MOD1 / PRES.MOD2)
                requiere alta como colaborador social en AEAT y certificado de
                representación FNMT. Mientras tanto puedes presentar manualmente con
                estas cifras desde la Sede Electrónica.
            </p>
        </div>
    );
}

// ── Vistas por modelo ────────────────────────────────────────────────────

function TenantHeader({ tenant, periodo }: { tenant: any; periodo?: string }) {
    return (
        <div className="flex items-center gap-2 text-xs text-muted-foreground mb-3 pb-3 border-b border-border">
            <Building2 className="w-3.5 h-3.5" aria-hidden="true" />
            <span className="text-foreground font-medium">{tenant?.name ?? "—"}</span>
            <span>· NIF {tenant?.nif ?? "—"}</span>
            {periodo && <span className="ml-auto text-[10px] uppercase tracking-wider">{periodo}</span>}
        </div>
    );
}

function Stat({ label, value, accent }: { label: string; value: string; accent?: "primary" | "warning" | "success" }) {
    const color =
        accent === "primary" ? "text-primary"
            : accent === "warning" ? "text-amber-500"
                : accent === "success" ? "text-emerald-500"
                    : "text-foreground";
    return (
        <div className="rounded-md bg-background border border-border p-3">
            <p className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</p>
            <p className={`mt-1 text-lg font-semibold tabular-nums ${color}`}>{value}</p>
        </div>
    );
}

function Modelo130View({ data }: { data: any }) {
    const resultado = Number(data.resultado_a_ingresar ?? 0);
    return (
        <>
            <TenantHeader tenant={data.tenant} periodo={`${data.periodo} ${data.ejercicio}`} />
            <div className="rounded-lg bg-primary/5 border border-primary/30 p-4 text-center mb-3">
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground">
                    Resultado a ingresar
                </p>
                <p className={`mt-1 text-3xl font-bold tabular-nums ${resultado > 0 ? "text-amber-500" : resultado < 0 ? "text-emerald-500" : "text-foreground"}`}>
                    {fmtEUR(resultado)}
                </p>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                <Stat label="Ingresos acumulados" value={fmtEUR(data.ingresos_acumulados)} accent="success" />
                <Stat label="Gastos acumulados" value={fmtEUR(data.gastos_acumulados)} />
                <Stat label="Beneficio acumulado" value={fmtEUR(data.beneficio_acumulado)} accent="primary" />
                <Stat label="Pago fraccionado bruto (20%)" value={fmtEUR(data.pago_fraccionado_bruto)} />
                <Stat label="Retenciones soportadas" value={fmtEUR(data.retenciones_soportadas)} />
                <Stat label="Facturas (emit / recib)" value={`${data.num_facturas_emitidas} / ${data.num_facturas_recibidas}`} />
            </div>
        </>
    );
}

function Modelo111View({ data }: { data: any }) {
    const perceptores: Array<any> = data.perceptores_trabajo_personal ?? [];
    return (
        <>
            <TenantHeader tenant={data.tenant} periodo={`${data.periodo} ${data.ejercicio}`} />
            <div className="grid grid-cols-3 gap-2 mb-3">
                <Stat label="Perceptores" value={String(data.num_perceptores)} />
                <Stat label="Base retenciones" value={fmtEUR(data.total_base_retenciones)} />
                <Stat label="Retención total" value={fmtEUR(data.total_retencion_practicada)} accent="primary" />
            </div>
            {perceptores.length > 0 ? (
                <table className="w-full text-xs">
                    <thead>
                        <tr className="text-muted-foreground border-b border-border">
                            <th className="text-left font-medium pb-1.5">Perceptor</th>
                            <th className="text-right font-medium pb-1.5">Base</th>
                            <th className="text-right font-medium pb-1.5">Retención</th>
                        </tr>
                    </thead>
                    <tbody>
                        {perceptores.map((p: any, i: number) => (
                            <tr key={i} className="border-b border-border/40">
                                <td className="py-1.5 text-foreground">
                                    {p.name ?? p.nif ?? "—"}
                                    {p.nif && <span className="text-muted-foreground ml-1">({p.nif})</span>}
                                </td>
                                <td className="py-1.5 text-right text-foreground tabular-nums">{fmtEUR(p.base ?? 0)}</td>
                                <td className="py-1.5 text-right text-foreground tabular-nums">{fmtEUR(p.retencion ?? 0)}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            ) : (
                <p className="text-xs text-muted-foreground italic py-3 text-center">
                    Sin perceptores con retención en el periodo.
                </p>
            )}
        </>
    );
}

function Modelo190View({ data }: { data: any }) {
    const perceptores: Array<any> = data.perceptores ?? [];
    return (
        <>
            <TenantHeader tenant={data.tenant} periodo={`Anual ${data.ejercicio}`} />
            <div className="grid grid-cols-3 gap-2 mb-3">
                <Stat label="Perceptores" value={String(data.num_perceptores)} />
                <Stat label="Percepción íntegra" value={fmtEUR(data.total_percepcion_integra)} />
                <Stat label="Retención total" value={fmtEUR(data.total_retencion_practicada)} accent="primary" />
            </div>
            {perceptores.length > 0 ? (
                <table className="w-full text-xs">
                    <thead>
                        <tr className="text-muted-foreground border-b border-border">
                            <th className="text-left font-medium pb-1.5">Perceptor</th>
                            <th className="text-center font-medium pb-1.5">Clave</th>
                            <th className="text-right font-medium pb-1.5">Percepción</th>
                            <th className="text-right font-medium pb-1.5">Retención</th>
                        </tr>
                    </thead>
                    <tbody>
                        {perceptores.map((p: any, i: number) => (
                            <tr key={i} className="border-b border-border/40">
                                <td className="py-1.5 text-foreground">
                                    {p.name ?? p.nif ?? "—"}
                                    {p.nif && <span className="text-muted-foreground ml-1">({p.nif})</span>}
                                </td>
                                <td className="py-1.5 text-center text-muted-foreground">
                                    {p.clave ?? "A"}
                                </td>
                                <td className="py-1.5 text-right text-foreground tabular-nums">{fmtEUR(p.percepcion_integra ?? p.base ?? 0)}</td>
                                <td className="py-1.5 text-right text-foreground tabular-nums">{fmtEUR(p.retencion_practicada ?? p.retencion ?? 0)}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            ) : (
                <p className="text-xs text-muted-foreground italic py-3 text-center">
                    Sin perceptores anuales.
                </p>
            )}
            {data._pending_v1_1 && (
                <p className="mt-3 text-[10px] text-muted-foreground italic">
                    Pendiente v1.1: {data._pending_v1_1}
                </p>
            )}
        </>
    );
}

function Modelo347View({ data }: { data: any }) {
    const declarables: Array<any> = data.declarables ?? [];
    return (
        <>
            <TenantHeader tenant={data.tenant} periodo={`Anual ${data.ejercicio}`} />
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2 mb-3">
                <Stat label="Contrapartes analizadas" value={String(data.total_contrapartes_analizadas ?? 0)} />
                <Stat
                    label="Declarables (>= umbral)"
                    value={String(data.num_declarables ?? 0)}
                    accent={data.num_declarables > 0 ? "warning" : undefined}
                />
                <Stat label="Umbral legal" value={fmtEUR(data.umbral_legal ?? 3005.06)} />
            </div>
            {declarables.length > 0 ? (
                <table className="w-full text-xs">
                    <thead>
                        <tr className="text-muted-foreground border-b border-border">
                            <th className="text-left font-medium pb-1.5">NIF</th>
                            <th className="text-left font-medium pb-1.5">Nombre</th>
                            <th className="text-right font-medium pb-1.5">Emitidas</th>
                            <th className="text-right font-medium pb-1.5">Recibidas</th>
                        </tr>
                    </thead>
                    <tbody>
                        {declarables.map((d: any, i: number) => (
                            <tr key={i} className="border-b border-border/40">
                                <td className="py-1.5 text-foreground tabular-nums">{d.nif ?? "—"}</td>
                                <td className="py-1.5 text-foreground">{d.name ?? "—"}</td>
                                <td className="py-1.5 text-right text-foreground tabular-nums">{fmtEUR(d.emitidas ?? 0)}</td>
                                <td className="py-1.5 text-right text-foreground tabular-nums">{fmtEUR(d.recibidas ?? 0)}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            ) : (
                <p className="text-xs text-muted-foreground italic py-3 text-center">
                    Ningún cliente o proveedor ha superado el umbral de {fmtEUR(data.umbral_legal ?? 3005.06)} este ejercicio.
                </p>
            )}
        </>
    );
}

function Modelo390View({ data }: { data: any }) {
    const devengado: Array<any> = data.iva_devengado ?? [];
    const deducible: Array<any> = data.iva_deducible ?? [];
    const resultado = Number(data.resultado_anual ?? 0);

    return (
        <>
            <TenantHeader tenant={data.tenant} periodo={`Anual ${data.ejercicio}`} />
            <div className="rounded-lg bg-primary/5 border border-primary/30 p-4 text-center mb-3">
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground">
                    Resultado anual IVA
                </p>
                <p className={`mt-1 text-3xl font-bold tabular-nums ${resultado > 0 ? "text-amber-500" : resultado < 0 ? "text-emerald-500" : "text-foreground"}`}>
                    {fmtEUR(resultado)}
                </p>
                <p className="text-[10px] text-muted-foreground mt-1">
                    {resultado > 0 ? "A ingresar" : resultado < 0 ? "A devolver" : "A cero"}
                </p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                    <h4 className="text-xs font-semibold text-foreground mb-2">IVA devengado (ventas)</h4>
                    <IvaTable rows={devengado} totalQuota={data.total_devengado ?? 0} />
                </div>
                <div>
                    <h4 className="text-xs font-semibold text-foreground mb-2">IVA deducible (compras)</h4>
                    <IvaTable rows={deducible} totalQuota={data.total_deducible ?? 0} />
                </div>
            </div>
            <p className="mt-3 text-[10px] text-muted-foreground">
                Facturas emitidas: {data.num_facturas_emitidas} · recibidas: {data.num_facturas_recibidas}
            </p>
        </>
    );
}

function IvaTable({ rows, totalQuota }: { rows: any[]; totalQuota: number }) {
    if (!rows || rows.length === 0) {
        return <p className="text-xs text-muted-foreground italic py-3">Sin operaciones.</p>;
    }
    return (
        <table className="w-full text-xs">
            <thead>
                <tr className="text-muted-foreground border-b border-border">
                    <th className="text-left font-medium pb-1.5">Tipo</th>
                    <th className="text-right font-medium pb-1.5">Base</th>
                    <th className="text-right font-medium pb-1.5">Cuota</th>
                </tr>
            </thead>
            <tbody>
                {rows.map((r: any, i: number) => (
                    <tr key={i} className="border-b border-border/40">
                        <td className="py-1.5 text-foreground">{fmtPct(r.rate)}</td>
                        <td className="py-1.5 text-right text-foreground tabular-nums">{fmtEUR(r.base ?? 0)}</td>
                        <td className="py-1.5 text-right text-foreground tabular-nums">{fmtEUR(r.quota ?? 0)}</td>
                    </tr>
                ))}
                <tr>
                    <td className="pt-2 font-semibold text-foreground">Total cuota</td>
                    <td colSpan={2} className="pt-2 text-right font-semibold text-foreground tabular-nums">
                        {fmtEUR(totalQuota)}
                    </td>
                </tr>
            </tbody>
        </table>
    );
}
