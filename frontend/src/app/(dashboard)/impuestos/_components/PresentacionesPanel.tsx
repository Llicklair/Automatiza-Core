"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import {
    ShieldCheck, ShieldAlert, Send, Loader2, CheckCircle2, AlertCircle, Clock,
    Sparkles, Receipt, Download,
} from "lucide-react";
import { api } from "@/lib/api";
import type { AeatCertificate, AeatPresentation } from "@/lib/api/aeat";
import { useToastStore } from "@/stores/toast";
import { CertificateUploadModal } from "./CertificateUploadModal";

type ModelCode = "303" | "130" | "111" | "115" | "349" | "190" | "347" | "390";
type Periodicity = "quarterly" | "yearly";

interface ModelMeta {
    code: ModelCode;
    nombre: string;
    periodicidad: Periodicity;
    descripcion: string;
}

const buildModels = (t: ReturnType<typeof useTranslations>): ModelMeta[] => [
    { code: "303", nombre: t("presentacion.modelo303Nombre"), periodicidad: "quarterly", descripcion: t("presentacion.modelo303Desc") },
    { code: "130", nombre: t("presentacion.modelo130Nombre"), periodicidad: "quarterly", descripcion: t("presentacion.modelo130Desc") },
    { code: "111", nombre: t("presentacion.modelo111Nombre"), periodicidad: "quarterly", descripcion: t("presentacion.modelo111Desc") },
    { code: "115", nombre: t("presentacion.modelo115Nombre"), periodicidad: "quarterly", descripcion: t("presentacion.modelo115Desc") },
    { code: "349", nombre: t("presentacion.modelo349Nombre"), periodicidad: "quarterly", descripcion: t("presentacion.modelo349Desc") },
    { code: "390", nombre: t("presentacion.modelo390Nombre"), periodicidad: "yearly", descripcion: t("presentacion.modelo390Desc") },
    { code: "190", nombre: t("presentacion.modelo190Nombre"), periodicidad: "yearly", descripcion: t("presentacion.modelo190Desc") },
    { code: "347", nombre: t("presentacion.modelo347Nombre"), periodicidad: "yearly", descripcion: t("presentacion.modelo347Desc") },
];

const STATUS_TONE: Record<string, string> = {
    pending: "bg-muted text-muted-foreground border-border",
    signed: "bg-primary/15 text-primary border-primary/30",
    submitted: "bg-primary/15 text-primary border-primary/30",
    accepted: "bg-emerald-500/15 text-emerald-500 border-emerald-500/30",
    rejected: "bg-rose-500/15 text-rose-500 border-rose-500/30",
    error: "bg-rose-500/15 text-rose-500 border-rose-500/30",
};

const STATUS_LABEL_KEY: Record<string, string> = {
    pending: "presentacion.statusPending", signed: "presentacion.statusSigned", submitted: "presentacion.statusSubmitted",
    accepted: "presentacion.statusAccepted", rejected: "presentacion.statusRejected", error: "presentacion.statusError",
};

function currentDefaults(): { quarter: number; year: number } {
    const d = new Date();
    return { quarter: Math.floor(d.getMonth() / 3) + 1, year: d.getFullYear() };
}

export function PresentacionesPanel() {
    const t = useTranslations("impuestos");
    const MODELS = buildModels(t);
    const toast = useToastStore();
    const init = currentDefaults();
    const [cert, setCert] = useState<AeatCertificate | null>(null);
    const [history, setHistory] = useState<AeatPresentation[]>([]);
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const [uploadOpen, setUploadOpen] = useState(false);

    const [modelCode, setModelCode] = useState<ModelCode>("303");
    const [quarter, setQuarter] = useState(init.quarter);
    const [year, setYear] = useState(init.year);

    const meta = MODELS.find((m) => m.code === modelCode)!;

    const loadAll = async () => {
        setLoading(true);
        try {
            const [certRes, listRes] = await Promise.all([
                api.aeat.certificate.get(),
                api.aeat.presentations.list(20),
            ]);
            setCert(certRes.active);
            setHistory(listRes.items);
        } catch {
            // silent
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { loadAll(); }, []);

    const handlePresent = async () => {
        if (!cert) { toast.error(t("presentacion.uploadCertFirst")); return; }
        if (cert.is_expired) { toast.error(t("presentacion.certExpired")); return; }
        setSubmitting(true);
        try {
            let created: AeatPresentation;
            if (modelCode === "303") {
                created = await api.aeat.presentations.create303FromQuarter(quarter, year, "preproduccion");
            } else if (meta.periodicidad === "quarterly") {
                created = await api.aeat.presentations.createQuarterly(
                    modelCode as "111" | "130" | "115" | "349", quarter, year, "preproduccion",
                );
            } else {
                created = await api.aeat.presentations.createYearly(
                    modelCode as "190" | "347" | "390", year, "preproduccion",
                );
            }
            const result = await api.aeat.presentations.submit(created.id, true);
            if (result.status === "accepted") {
                toast.success(t("presentacion.simuladoOk", { csv: result.csv_justificante ?? "—" }));
            } else {
                toast.error(t("presentacion.errorWithCode", { code: result.error_code ?? t("presentacion.statusError"), message: result.error_message ?? "—" }));
            }
            loadAll();
        } catch (e) {
            toast.error(e instanceof Error ? e.message : t("presentacion.presentError"));
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="rounded-2xl border border-violet-500/20 bg-gradient-to-br from-violet-500/5 via-card to-card p-5 space-y-5">
            <div className="flex items-start gap-3 flex-wrap">
                <div className="flex-shrink-0 w-11 h-11 rounded-xl bg-violet-500/15 text-violet-400 flex items-center justify-center">
                    <Sparkles className="w-5 h-5" />
                </div>
                <div className="flex-1 min-w-[220px]">
                    <div className="flex items-center gap-2">
                        <h3 className="text-sm font-semibold text-foreground">{t("presentacion.titlePanel")}</h3>
                        <span className="text-[10px] uppercase tracking-wider font-bold bg-amber-500/15 text-amber-500 border border-amber-500/30 px-1.5 py-0.5 rounded">{t("presentacion.beta")}</span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-0.5">
                        {t("presentacion.descPanel")}
                    </p>
                </div>
                {cert && !cert.is_expired && (
                    <span className="inline-flex items-center gap-1.5 text-xs font-medium text-emerald-500 bg-emerald-500/10 border border-emerald-500/30 px-2 py-1 rounded">
                        <ShieldCheck className="w-3.5 h-3.5" />
                        {t("presentacion.certOk")}
                    </span>
                )}
            </div>

            {/* Estado certificado o invitación a subirlo */}
            {loading ? (
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <Loader2 className="w-3.5 h-3.5 animate-spin" /> {t("presentacion.cargandoEstado")}
                </div>
            ) : !cert ? (
                <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs space-y-2">
                    <div className="flex items-start gap-2">
                        <ShieldAlert className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />
                        <p className="text-foreground">
                            {t("presentacion.sinCertPanel")}
                        </p>
                    </div>
                    <button
                        onClick={() => setUploadOpen(true)}
                        className="w-full h-9 rounded-md bg-amber-500/20 hover:bg-amber-500/30 text-amber-500 font-medium text-xs transition"
                    >
                        {t("presentacion.subirCert")}
                    </button>
                </div>
            ) : cert.is_expired ? (
                <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-xs space-y-2">
                    <div className="flex items-start gap-2">
                        <ShieldAlert className="w-4 h-4 text-rose-500 flex-shrink-0 mt-0.5" />
                        <p>{t("presentacion.certCaducadoMsg", { label: cert.label })}</p>
                    </div>
                    <button
                        onClick={() => setUploadOpen(true)}
                        className="w-full h-9 rounded-md bg-rose-500/20 hover:bg-rose-500/30 text-rose-500 font-medium text-xs transition"
                    >
                        {t("presentacion.reemplazarCert")}
                    </button>
                </div>
            ) : (
                <div className="rounded-lg border border-border bg-card p-3 text-xs">
                    <div className="flex items-center justify-between gap-3">
                        <div className="min-w-0">
                            <p className="font-medium text-foreground truncate">{cert.label}</p>
                            {cert.subject_cn && (
                                <p className="text-muted-foreground truncate" title={cert.subject_cn}>{cert.subject_cn}</p>
                            )}
                            {cert.valid_until && (
                                <p className="text-muted-foreground">
                                    {t("presentacion.validoHastaInline", { fecha: new Date(cert.valid_until).toLocaleDateString("es-ES") })}
                                </p>
                            )}
                        </div>
                        <button onClick={() => setUploadOpen(true)} className="text-muted-foreground hover:text-foreground underline">
                            {t("presentacion.reemplazar")}
                        </button>
                    </div>
                </div>
            )}

            {/* Selector de modelo y periodo */}
            <div className="grid grid-cols-1 lg:grid-cols-[1fr_auto_auto_auto] gap-2 items-end">
                <div>
                    <label className="block text-[11px] uppercase tracking-wider text-muted-foreground mb-1">{t("presentacion.modelo")}</label>
                    <select
                        value={modelCode}
                        onChange={(e) => setModelCode(e.target.value as ModelCode)}
                        className="w-full h-9 px-2 rounded-md border border-border bg-card text-sm"
                    >
                        {MODELS.map((m) => (
                            <option key={m.code} value={m.code}>
                                {t("presentacion.modeloOption", { code: m.code, nombre: m.nombre, periodicidad: m.periodicidad === "quarterly" ? t("presentacion.periodicidadTrim") : t("presentacion.periodicidadAnual") })}
                            </option>
                        ))}
                    </select>
                </div>
                {meta.periodicidad === "quarterly" && (
                    <div>
                        <label className="block text-[11px] uppercase tracking-wider text-muted-foreground mb-1">{t("presentacion.trim")}</label>
                        <select
                            value={quarter}
                            onChange={(e) => setQuarter(Number(e.target.value))}
                            className="h-9 px-2 rounded-md border border-border bg-card text-sm"
                        >
                            {[1, 2, 3, 4].map((q) => <option key={q} value={q}>{q}T</option>)}
                        </select>
                    </div>
                )}
                <div>
                    <label className="block text-[11px] uppercase tracking-wider text-muted-foreground mb-1">{t("presentacion.year")}</label>
                    <select
                        value={year}
                        onChange={(e) => setYear(Number(e.target.value))}
                        className="h-9 px-2 rounded-md border border-border bg-card text-sm"
                    >
                        {[year - 1, year, year + 1].map((y) => <option key={y} value={y}>{y}</option>)}
                    </select>
                </div>
                <button
                    onClick={handlePresent}
                    disabled={submitting || loading || !cert || cert.is_expired}
                    className="h-9 px-4 rounded-md bg-violet-500 hover:brightness-110 text-white font-medium text-sm flex items-center gap-2 transition disabled:opacity-50"
                >
                    {submitting
                        ? <Loader2 className="w-4 h-4 animate-spin" />
                        : <Send className="w-4 h-4" />}
                    {t("presentacion.presentarSim")}
                </button>
            </div>

            <p className="text-xs text-muted-foreground -mt-3">{meta.descripcion}</p>

            {/* Historial */}
            {history.length > 0 && (
                <div>
                    <h4 className="text-[11px] uppercase tracking-wider font-semibold text-muted-foreground mb-2">{t("presentacion.ultimasPresentaciones")}</h4>
                    <div className="rounded-lg border border-border overflow-hidden">
                        <table className="w-full text-xs">
                            <thead className="bg-muted/30 text-muted-foreground">
                                <tr>
                                    <th className="text-left px-3 py-2 font-medium">{t("presentacion.thModelo")}</th>
                                    <th className="text-left px-3 py-2 font-medium">{t("presentacion.thPeriodo")}</th>
                                    <th className="text-left px-3 py-2 font-medium">{t("presentacion.thEstado")}</th>
                                    <th className="text-left px-3 py-2 font-medium">{t("presentacion.thCsvError")}</th>
                                    <th className="text-right px-3 py-2 font-medium">{t("presentacion.thFecha")}</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-border">
                                {history.slice(0, 10).map((p) => (
                                    <tr key={p.id} className="bg-card">
                                        <td className="px-3 py-2 font-medium text-foreground">
                                            <Receipt className="w-3 h-3 inline mr-1 text-muted-foreground" />
                                            {p.model_code}
                                        </td>
                                        <td className="px-3 py-2 text-muted-foreground">{p.period} {p.year}</td>
                                        <td className="px-3 py-2">
                                            <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded border ${STATUS_TONE[p.status] ?? "bg-muted text-muted-foreground border-border"}`}>
                                                {p.status === "accepted" && <CheckCircle2 className="w-3 h-3" />}
                                                {(p.status === "rejected" || p.status === "error") && <AlertCircle className="w-3 h-3" />}
                                                {(p.status === "pending" || p.status === "signed") && <Clock className="w-3 h-3" />}
                                                {STATUS_LABEL_KEY[p.status] ? t(STATUS_LABEL_KEY[p.status]) : p.status}
                                            </span>
                                        </td>
                                        <td className="px-3 py-2 text-muted-foreground font-mono text-[10px] max-w-[180px]" title={p.csv_justificante ?? p.error_message ?? ""}>
                                            <span className="inline-flex items-center gap-1.5 max-w-full">
                                                <span className="truncate">{p.csv_justificante ?? p.error_message ?? "—"}</span>
                                                {p.csv_justificante && (
                                                    <button
                                                        type="button"
                                                        className="shrink-0 text-muted-foreground hover:text-foreground transition-colors"
                                                        title={t("presentacion.descargarAcuse")}
                                                        onClick={() => void api.aeat.presentations.downloadAcuse(p)}
                                                    >
                                                        <Download className="w-3 h-3" />
                                                    </button>
                                                )}
                                            </span>
                                        </td>
                                        <td className="px-3 py-2 text-right text-muted-foreground">
                                            {p.created_at ? new Date(p.created_at).toLocaleDateString("es-ES") : "—"}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            <p className="text-[10px] text-muted-foreground">
                {t("presentacion.footnotePanel")}
            </p>

            <CertificateUploadModal
                open={uploadOpen}
                onClose={() => setUploadOpen(false)}
                onUploaded={loadAll}
            />
        </div>
    );
}
