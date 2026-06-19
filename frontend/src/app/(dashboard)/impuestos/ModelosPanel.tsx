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
import { useTranslations } from "next-intl";
import {
    BookCheck,
    Building2,
    Download,
    FileText,
    Loader2,
    RefreshCw,
    Users,
} from "lucide-react";
import { api } from "@/lib/api";
import { PageHeader } from "@/components/shared/PageHeader";
import { useToastStore } from "@/stores/toast";

type ModeloKey = "130" | "111" | "190" | "347" | "390";

interface ModeloMeta {
    key: ModeloKey;
    titulo: string;
    subtitulo: string;
    descripcion: string;
    periodicidad: "trimestral" | "anual";
}

const buildModelos = (t: ReturnType<typeof useTranslations>): ModeloMeta[] => [
    {
        key: "130",
        titulo: t("modelos.modelo130Titulo"),
        subtitulo: t("modelos.modelo130Subtitulo"),
        descripcion: t("modelos.modelo130Descripcion"),
        periodicidad: "trimestral",
    },
    {
        key: "111",
        titulo: t("modelos.modelo111Titulo"),
        subtitulo: t("modelos.modelo111Subtitulo"),
        descripcion: t("modelos.modelo111Descripcion"),
        periodicidad: "trimestral",
    },
    {
        key: "190",
        titulo: t("modelos.modelo190Titulo"),
        subtitulo: t("modelos.modelo190Subtitulo"),
        descripcion: t("modelos.modelo190Descripcion"),
        periodicidad: "anual",
    },
    {
        key: "347",
        titulo: t("modelos.modelo347Titulo"),
        subtitulo: t("modelos.modelo347Subtitulo"),
        descripcion: t("modelos.modelo347Descripcion"),
        periodicidad: "anual",
    },
    {
        key: "390",
        titulo: t("modelos.modelo390Titulo"),
        subtitulo: t("modelos.modelo390Subtitulo"),
        descripcion: t("modelos.modelo390Descripcion"),
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

export function ModelosPanel() {
    const t = useTranslations("impuestos");
    const MODELOS = buildModelos(t);
    const toast = useToastStore();
    const [ejercicio, setEjercicio] = useState(CURRENT_YEAR);
    const [trimestre, setTrimestre] = useState(1);
    const [busy, setBusy] = useState<ModeloKey | null>(null);
    const [results, setResults] = useState<Partial<Record<ModeloKey, any>>>({});
    type DownloadKey = ModeloKey | "303" | "115" | "349";
    const [downloading, setDownloading] = useState<DownloadKey | null>(null);

    async function downloadPdf(modelo: DownloadKey) {
        setDownloading(modelo);
        try {
            switch (modelo) {
                case "303": await api.modelosAeat.pdf.m303(trimestre, ejercicio); break;
                case "130": await api.modelosAeat.pdf.m130(trimestre, ejercicio); break;
                case "111": await api.modelosAeat.pdf.m111(trimestre, ejercicio); break;
                case "115": await api.modelosAeat.pdf.m115(trimestre, ejercicio); break;
                case "349": await api.modelosAeat.pdf.m349(trimestre, ejercicio); break;
                case "190": await api.modelosAeat.pdf.m190(ejercicio); break;
                case "347": await api.modelosAeat.pdf.m347(ejercicio); break;
                case "390": await api.modelosAeat.pdf.m390(ejercicio); break;
            }
            toast.show(t("modelos.pdfDownloaded", { modelo }), "success");
        } catch (e: any) {
            toast.show(t("modelos.pdfDownloadError", { message: e.message }), "error");
        } finally {
            setDownloading(null);
        }
    }

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
            toast.show(t("modelos.modeloCalculated", { modelo }), "success");
        } catch (e: any) {
            toast.show(t("modelos.calcError", { message: e.message }), "error");
        } finally {
            setBusy(null);
        }
    }

    return (
        <div className="space-y-6">
            <PageHeader
                title={t("modelos.title")}
                description={t("modelos.description")}
            />

            <section className="rounded-lg border border-border bg-card p-4 space-y-3">
                <h2 className="text-sm font-medium text-foreground">{t("modelos.periodoFiscal")}</h2>
                <div className="flex flex-wrap items-center gap-3">
                    <label className="text-xs text-muted-foreground flex items-center gap-2">
                        {t("modelos.ejercicio")}
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
                        {t("modelos.trimestre")}
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
                    <div className="ml-auto flex flex-wrap items-center gap-2">
                        <span className="text-[10px] uppercase tracking-wider text-muted-foreground">
                            {t("modelos.descargarTrimestral")}
                        </span>
                        {(["303", "115", "349"] as const).map((mk) => (
                            <button
                                key={mk}
                                type="button"
                                onClick={() => downloadPdf(mk)}
                                disabled={downloading === mk}
                                title={t("modelos.pdfTitle", { modelo: mk })}
                                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-primary text-foreground text-xs font-medium hover:bg-primary/90 disabled:opacity-50"
                            >
                                {downloading === mk ? (
                                    <Loader2 className="w-3 h-3 animate-spin" aria-hidden="true" />
                                ) : (
                                    <Download className="w-3 h-3" aria-hidden="true" />
                                )}
                                {t("modelos.pdfButton", { modelo: mk })}
                            </button>
                        ))}
                    </div>
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
                                        {m.periodicidad === "trimestral" ? t("modelos.periodicidadTrimestral") : t("modelos.periodicidadAnual")}
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
                                        {data ? t("modelos.recalcular") : t("modelos.calcular")}
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => downloadPdf(m.key)}
                                        disabled={downloading === m.key}
                                        title={t("modelos.pdfBorradorTitle")}
                                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-border text-foreground text-xs font-medium hover:bg-muted disabled:opacity-50"
                                    >
                                        {downloading === m.key ? (
                                            <Loader2 className="w-3 h-3 animate-spin" aria-hidden="true" />
                                        ) : (
                                            <Download className="w-3 h-3" aria-hidden="true" />
                                        )}
                                        {t("modelos.pdf")}
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
                {t("modelos.footnote")}
            </p>
        </div>
    );
}

// ── Vistas por modelo ────────────────────────────────────────────────────

function TenantHeader({ tenant, periodo }: { tenant: any; periodo?: string }) {
    const t = useTranslations("impuestos");
    return (
        <div className="flex items-center gap-2 text-xs text-muted-foreground mb-3 pb-3 border-b border-border">
            <Building2 className="w-3.5 h-3.5" aria-hidden="true" />
            <span className="text-foreground font-medium">{tenant?.name ?? "—"}</span>
            <span>· {t("modelos.nif", { nif: tenant?.nif ?? "—" })}</span>
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
    const t = useTranslations("impuestos");
    const resultado = Number(data.resultado_a_ingresar ?? 0);
    return (
        <>
            <TenantHeader tenant={data.tenant} periodo={`${data.periodo} ${data.ejercicio}`} />
            <div className="rounded-lg bg-primary/5 border border-primary/30 p-4 text-center mb-3">
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground">
                    {t("modelos.resultadoAIngresar")}
                </p>
                <p className={`mt-1 text-3xl font-bold tabular-nums ${resultado > 0 ? "text-amber-500" : resultado < 0 ? "text-emerald-500" : "text-foreground"}`}>
                    {fmtEUR(resultado)}
                </p>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                <Stat label={t("modelos.stat130Ingresos")} value={fmtEUR(data.ingresos_acumulados)} accent="success" />
                <Stat label={t("modelos.stat130Gastos")} value={fmtEUR(data.gastos_acumulados)} />
                <Stat label={t("modelos.stat130Beneficio")} value={fmtEUR(data.beneficio_acumulado)} accent="primary" />
                <Stat label={t("modelos.stat130PagoFraccionado")} value={fmtEUR(data.pago_fraccionado_bruto)} />
                <Stat label={t("modelos.stat130Retenciones")} value={fmtEUR(data.retenciones_soportadas)} />
                <Stat label={t("modelos.stat130Facturas")} value={`${data.num_facturas_emitidas} / ${data.num_facturas_recibidas}`} />
            </div>
        </>
    );
}

function Modelo111View({ data }: { data: any }) {
    const t = useTranslations("impuestos");
    const perceptores: Array<any> = data.perceptores_trabajo_personal ?? [];
    return (
        <>
            <TenantHeader tenant={data.tenant} periodo={`${data.periodo} ${data.ejercicio}`} />
            <div className="grid grid-cols-3 gap-2 mb-3">
                <Stat label={t("modelos.perceptores")} value={String(data.num_perceptores)} />
                <Stat label={t("modelos.baseRetenciones")} value={fmtEUR(data.total_base_retenciones)} />
                <Stat label={t("modelos.retencionTotal")} value={fmtEUR(data.total_retencion_practicada)} accent="primary" />
            </div>
            {perceptores.length > 0 ? (
                <table className="w-full text-xs">
                    <thead>
                        <tr className="text-muted-foreground border-b border-border">
                            <th className="text-left font-medium pb-1.5">{t("modelos.thPerceptor")}</th>
                            <th className="text-right font-medium pb-1.5">{t("modelos.thBase")}</th>
                            <th className="text-right font-medium pb-1.5">{t("modelos.thRetencion")}</th>
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
                    {t("modelos.sinPerceptoresRetencion")}
                </p>
            )}
        </>
    );
}

function Modelo190View({ data }: { data: any }) {
    const t = useTranslations("impuestos");
    const perceptores: Array<any> = data.perceptores ?? [];
    return (
        <>
            <TenantHeader tenant={data.tenant} periodo={`${t("modelos.periodicidadAnual")} ${data.ejercicio}`} />
            <div className="grid grid-cols-3 gap-2 mb-3">
                <Stat label={t("modelos.perceptores")} value={String(data.num_perceptores)} />
                <Stat label={t("modelos.percepcionIntegra")} value={fmtEUR(data.total_percepcion_integra)} />
                <Stat label={t("modelos.retencionTotal")} value={fmtEUR(data.total_retencion_practicada)} accent="primary" />
            </div>
            {perceptores.length > 0 ? (
                <table className="w-full text-xs">
                    <thead>
                        <tr className="text-muted-foreground border-b border-border">
                            <th className="text-left font-medium pb-1.5">{t("modelos.thPerceptor")}</th>
                            <th className="text-center font-medium pb-1.5">{t("modelos.thClave")}</th>
                            <th className="text-right font-medium pb-1.5">{t("modelos.thPercepcion")}</th>
                            <th className="text-right font-medium pb-1.5">{t("modelos.thRetencion")}</th>
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
                    {t("modelos.sinPerceptoresAnuales")}
                </p>
            )}
            {data._pending_v1_1 && (
                <p className="mt-3 text-[10px] text-muted-foreground italic">
                    {t("modelos.pendienteV11", { detail: data._pending_v1_1 })}
                </p>
            )}
        </>
    );
}

function Modelo347View({ data }: { data: any }) {
    const t = useTranslations("impuestos");
    const declarables: Array<any> = data.declarables ?? [];
    return (
        <>
            <TenantHeader tenant={data.tenant} periodo={`${t("modelos.periodicidadAnual")} ${data.ejercicio}`} />
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2 mb-3">
                <Stat label={t("modelos.contrapartesAnalizadas")} value={String(data.total_contrapartes_analizadas ?? 0)} />
                <Stat
                    label={t("modelos.declarables")}
                    value={String(data.num_declarables ?? 0)}
                    accent={data.num_declarables > 0 ? "warning" : undefined}
                />
                <Stat label={t("modelos.umbralLegal")} value={fmtEUR(data.umbral_legal ?? 3005.06)} />
            </div>
            {declarables.length > 0 ? (
                <table className="w-full text-xs">
                    <thead>
                        <tr className="text-muted-foreground border-b border-border">
                            <th className="text-left font-medium pb-1.5">{t("modelos.thNif")}</th>
                            <th className="text-left font-medium pb-1.5">{t("modelos.thNombre")}</th>
                            <th className="text-right font-medium pb-1.5">{t("modelos.thEmitidas")}</th>
                            <th className="text-right font-medium pb-1.5">{t("modelos.thRecibidas")}</th>
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
                    {t("modelos.ningunUmbral", { umbral: fmtEUR(data.umbral_legal ?? 3005.06) })}
                </p>
            )}
        </>
    );
}

function Modelo390View({ data }: { data: any }) {
    const t = useTranslations("impuestos");
    const devengado: Array<any> = data.iva_devengado ?? [];
    const deducible: Array<any> = data.iva_deducible ?? [];
    const resultado = Number(data.resultado_anual ?? 0);

    return (
        <>
            <TenantHeader tenant={data.tenant} periodo={`${t("modelos.periodicidadAnual")} ${data.ejercicio}`} />
            <div className="rounded-lg bg-primary/5 border border-primary/30 p-4 text-center mb-3">
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground">
                    {t("modelos.resultadoAnualIva")}
                </p>
                <p className={`mt-1 text-3xl font-bold tabular-nums ${resultado > 0 ? "text-amber-500" : resultado < 0 ? "text-emerald-500" : "text-foreground"}`}>
                    {fmtEUR(resultado)}
                </p>
                <p className="text-[10px] text-muted-foreground mt-1">
                    {resultado > 0 ? t("modelos.aIngresar") : resultado < 0 ? t("modelos.aDevolver") : t("modelos.aCero")}
                </p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                    <h4 className="text-xs font-semibold text-foreground mb-2">{t("modelos.ivaDevengado")}</h4>
                    <IvaTable rows={devengado} totalQuota={data.total_devengado ?? 0} />
                </div>
                <div>
                    <h4 className="text-xs font-semibold text-foreground mb-2">{t("modelos.ivaDeducible")}</h4>
                    <IvaTable rows={deducible} totalQuota={data.total_deducible ?? 0} />
                </div>
            </div>
            <p className="mt-3 text-[10px] text-muted-foreground">
                {t("modelos.facturasEmitidasRecibidas", { emitidas: data.num_facturas_emitidas, recibidas: data.num_facturas_recibidas })}
            </p>
        </>
    );
}

function IvaTable({ rows, totalQuota }: { rows: any[]; totalQuota: number }) {
    const t = useTranslations("impuestos");
    if (!rows || rows.length === 0) {
        return <p className="text-xs text-muted-foreground italic py-3">{t("modelos.sinOperaciones")}</p>;
    }
    return (
        <table className="w-full text-xs">
            <thead>
                <tr className="text-muted-foreground border-b border-border">
                    <th className="text-left font-medium pb-1.5">{t("modelos.thTipo")}</th>
                    <th className="text-right font-medium pb-1.5">{t("modelos.thBase")}</th>
                    <th className="text-right font-medium pb-1.5">{t("modelos.thCuota")}</th>
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
                    <td className="pt-2 font-semibold text-foreground">{t("modelos.totalCuota")}</td>
                    <td colSpan={2} className="pt-2 text-right font-semibold text-foreground tabular-nums">
                        {fmtEUR(totalQuota)}
                    </td>
                </tr>
            </tbody>
        </table>
    );
}
