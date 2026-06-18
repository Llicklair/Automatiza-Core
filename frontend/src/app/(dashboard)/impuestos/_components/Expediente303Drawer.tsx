"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import {
    X, Loader2, Download, FileText, CheckCircle2, Copy,
    AlertTriangle, ExternalLink, Sparkles, Circle,
} from "lucide-react";
import { api } from "@/lib/api";
import type { Modelo303Expediente } from "@/lib/api/reports";
import { useToastStore } from "@/stores/toast";
import { PresentacionElectronicaPanel } from "./PresentacionElectronicaPanel";

interface Props {
    quarter: number;
    year: number;
    open: boolean;
    onClose: () => void;
}

const fmt = (n: number) =>
    new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" }).format(n);

export function Expediente303Drawer({ quarter, year, open, onClose }: Props) {
    const t = useTranslations("impuestos");
    const [data, setData] = useState<Modelo303Expediente | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [pdfLoading, setPdfLoading] = useState(false);
    const toast = useToastStore();

    useEffect(() => {
        if (!open) return;
        setLoading(true);
        setError(null);
        api.reports.modelo303Expediente(quarter, year)
            .then(setData)
            .catch((e: Error) => setError(e.message || t("expediente303.generError")))
            .finally(() => setLoading(false));
    }, [open, quarter, year]);

    if (!open) return null;

    const handleDownloadXml = () => {
        if (!data) return;
        const blob = new Blob([data.xml], { type: "application/xml" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = data.xml_filename;
        a.click();
        URL.revokeObjectURL(url);
    };

    const handleDownloadPdf = async () => {
        setPdfLoading(true);
        try {
            await api.reports.modelo303Pdf(quarter, year);
        } catch {
            toast.error(t("expediente303.pdfError"));
        } finally {
            setPdfLoading(false);
        }
    };

    const handleCopyCasilla = (codigo: string, valor: number) => {
        navigator.clipboard.writeText(valor.toFixed(2));
        toast.success(t("expediente303.casillaCopiada", { codigo, valor: valor.toFixed(2) }));
    };

    const signoTone = data?.resumen.signo === "ingresar"
        ? "bg-rose-500/10 text-rose-500 border-rose-500/30"
        : data?.resumen.signo === "compensar"
            ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/30"
            : "bg-muted text-muted-foreground border-border";

    return (
        <div
            className="fixed inset-0 z-50 bg-black/50 flex items-stretch justify-end"
            onClick={onClose}
        >
            <div
                className="bg-background border-l border-border w-full max-w-3xl h-full overflow-hidden flex flex-col"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header */}
                <div className="flex items-start justify-between gap-4 p-5 border-b border-border">
                    <div>
                        <div className="flex items-center gap-2 text-xs text-muted-foreground uppercase tracking-wider font-semibold">
                            <Sparkles className="w-3.5 h-3.5 text-primary" />
                            {t("expediente303.badge")}
                        </div>
                        <h2 className="text-lg font-semibold text-foreground mt-1">
                            {t("expediente303.heading", { periodo: data?.periodo || `${quarter}T ${year}` })}
                        </h2>
                        {data?.tenant && (
                            <p className="text-xs text-muted-foreground mt-0.5">
                                {t("expediente303.tenantNif", { name: data.tenant.name, nif: data.tenant.nif })}
                            </p>
                        )}
                    </div>
                    <button onClick={onClose} className="text-muted-foreground hover:text-foreground" aria-label={t("expediente303.closeAria")}>
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-auto p-5 space-y-5">
                    {loading && (
                        <div className="flex items-center justify-center py-20 text-muted-foreground gap-3">
                            <Loader2 className="w-5 h-5 animate-spin" />
                            {t("expediente303.calculando")}
                        </div>
                    )}

                    {error && (
                        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-400 flex items-start gap-2">
                            <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                            {error}
                        </div>
                    )}

                    {data && (
                        <>
                            {/* Resumen */}
                            <div className={`rounded-2xl border p-5 ${signoTone}`}>
                                <div className="text-xs uppercase tracking-wider font-semibold opacity-80">
                                    {t("expediente303.resultadoTrimestre")}
                                </div>
                                <div className="text-3xl font-bold mt-1 tabular-nums">
                                    {fmt(Math.abs(data.resumen.resultado))}
                                    <span className="ml-2 text-sm font-medium align-middle">
                                        {data.resumen.signo === "ingresar" && t("expediente303.aIngresar")}
                                        {data.resumen.signo === "compensar" && t("expediente303.aCompensar")}
                                        {data.resumen.signo === "cero" && t("expediente303.sinActividad")}
                                    </span>
                                </div>
                                <div className="grid grid-cols-2 gap-3 mt-4 text-sm">
                                    <div>
                                        <p className="opacity-70 text-xs">{t("expediente303.ivaDevengado")}</p>
                                        <p className="font-semibold tabular-nums">{fmt(data.resumen.total_devengado)}</p>
                                    </div>
                                    <div>
                                        <p className="opacity-70 text-xs">{t("expediente303.ivaDeducible")}</p>
                                        <p className="font-semibold tabular-nums">{fmt(data.resumen.total_deducible)}</p>
                                    </div>
                                </div>
                            </div>

                            {/* Descargas */}
                            <div className="grid grid-cols-2 gap-3">
                                <button
                                    onClick={handleDownloadPdf}
                                    disabled={pdfLoading}
                                    className="flex items-center justify-center gap-2 h-10 rounded-lg border border-border bg-card hover:bg-muted/50 transition text-sm font-medium disabled:opacity-50"
                                >
                                    {pdfLoading
                                        ? <><Loader2 className="w-4 h-4 animate-spin" /> {t("expediente303.descargando")}</>
                                        : <><FileText className="w-4 h-4" /> {t("expediente303.descargarPdf")}</>}
                                </button>
                                <button
                                    onClick={handleDownloadXml}
                                    className="flex items-center justify-center gap-2 h-10 rounded-lg border border-border bg-card hover:bg-muted/50 transition text-sm font-medium"
                                >
                                    <Download className="w-4 h-4" /> {t("expediente303.descargarXml")}
                                </button>
                            </div>

                            {/* Casillas */}
                            <div>
                                <h3 className="text-sm font-semibold text-foreground mb-2">{t("expediente303.casillasTitle")}</h3>
                                <p className="text-xs text-muted-foreground mb-3">
                                    {t.rich("expediente303.casillasNota", {
                                        editable: (chunks) => <span className="text-amber-500">{chunks}</span>,
                                    })}
                                </p>
                                <div className="rounded-lg border border-border overflow-hidden">
                                    <table className="w-full text-sm">
                                        <thead className="bg-muted/30 text-xs uppercase tracking-wider text-muted-foreground">
                                            <tr>
                                                <th className="text-left px-3 py-2 w-16">{t("expediente303.thCod")}</th>
                                                <th className="text-left px-3 py-2">{t("expediente303.thDescripcion")}</th>
                                                <th className="text-right px-3 py-2">{t("expediente303.thValor")}</th>
                                                <th className="w-10"></th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-border">
                                            {data.casillas.map((c) => (
                                                <tr key={c.codigo} className={c.editable ? "bg-amber-500/5" : ""}>
                                                    <td className="px-3 py-2 font-mono text-xs text-muted-foreground">{c.codigo}</td>
                                                    <td className="px-3 py-2 text-foreground">
                                                        <div>{c.descripcion}</div>
                                                        {c.nota && (
                                                            <div className="text-[11px] text-amber-500/80 mt-0.5">{c.nota}</div>
                                                        )}
                                                    </td>
                                                    <td className="px-3 py-2 text-right tabular-nums font-medium text-foreground">
                                                        {c.valor.toFixed(2)}
                                                    </td>
                                                    <td className="px-2 py-2">
                                                        <button
                                                            onClick={() => handleCopyCasilla(c.codigo, c.valor)}
                                                            title={t("expediente303.copiarValor")}
                                                            className="text-muted-foreground hover:text-primary p-1"
                                                        >
                                                            <Copy className="w-3.5 h-3.5" />
                                                        </button>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>

                            {/* Checklist */}
                            <div>
                                <h3 className="text-sm font-semibold text-foreground mb-3">{t("expediente303.pasosTitle")}</h3>
                                <ol className="space-y-2">
                                    {data.checklist.map((step) => (
                                        <li key={step.n} className="flex items-start gap-3 rounded-lg border border-border bg-card p-3">
                                            {step.completado
                                                ? <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0 mt-0.5" />
                                                : <Circle className="w-4 h-4 text-muted-foreground flex-shrink-0 mt-0.5" />}
                                            <div className="flex-1 min-w-0">
                                                <p className="text-sm font-medium text-foreground">
                                                    <span className="text-muted-foreground mr-1">{step.n}.</span>
                                                    {step.titulo}
                                                </p>
                                                <p className="text-xs text-muted-foreground mt-0.5">{step.detalle}</p>
                                            </div>
                                        </li>
                                    ))}
                                </ol>
                                <a
                                    href="https://sede.agenciatributaria.gob.es/Sede/iva/modelo-303.html"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="mt-3 inline-flex items-center gap-1.5 text-xs text-primary hover:underline"
                                >
                                    {t("expediente303.abrirSede")}
                                    <ExternalLink className="w-3 h-3" />
                                </a>
                            </div>

                            <PresentacionElectronicaPanel quarter={quarter} year={year} />

                            <div className="text-[11px] text-muted-foreground border-t border-border pt-3">
                                {t("expediente303.footnote")}
                            </div>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}
