"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import {
    ShieldCheck, ShieldAlert, Send, Loader2, CheckCircle2, AlertCircle,
    Clock, Sparkles, ExternalLink,
} from "lucide-react";
import { api } from "@/lib/api";
import type { AeatCertificate, AeatPresentation } from "@/lib/api/aeat";
import { useToastStore } from "@/stores/toast";
import { CertificateUploadModal } from "./CertificateUploadModal";

interface Props {
    quarter: number;
    year: number;
}

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

export function PresentacionElectronicaPanel({ quarter, year }: Props) {
    const t = useTranslations("impuestos");
    const toast = useToastStore();
    const [cert, setCert] = useState<AeatCertificate | null>(null);
    const [history, setHistory] = useState<AeatPresentation[]>([]);
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const [uploadOpen, setUploadOpen] = useState(false);

    const loadAll = async () => {
        setLoading(true);
        try {
            const [certRes, listRes] = await Promise.all([
                api.aeat.certificate.get(),
                api.aeat.presentations.list(10),
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
            const created = await api.aeat.presentations.create303FromQuarter(quarter, year, "preproduccion");
            // Acto seguido: submit dry-run
            const result = await api.aeat.presentations.submit(created.id, true);
            if (result.status === "accepted") {
                toast.success(t("presentacion.simuladoOk", { csv: result.csv_justificante ?? "—" }));
            } else if (result.status === "error" || result.status === "rejected") {
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
        <div className="rounded-xl border border-violet-500/20 bg-violet-500/5 p-4 space-y-4">
            <div className="flex items-start gap-3">
                <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-violet-500/15 text-violet-400 flex items-center justify-center">
                    <Sparkles className="w-5 h-5" />
                </div>
                <div className="flex-1">
                    <div className="flex items-center gap-2">
                        <h4 className="text-sm font-semibold text-foreground">{t("presentacion.title")}</h4>
                        <span className="text-[10px] uppercase tracking-wider font-bold bg-amber-500/15 text-amber-500 border border-amber-500/30 px-1.5 py-0.5 rounded">{t("presentacion.beta")}</span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-0.5">
                        {t("presentacion.descDrawer")}
                    </p>
                </div>
            </div>

            {/* Estado del certificado */}
            {loading ? (
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <Loader2 className="w-3.5 h-3.5 animate-spin" /> {t("presentacion.cargandoEstado")}
                </div>
            ) : cert ? (
                <div className="rounded-lg border border-border bg-card p-3 text-xs">
                    <div className="flex items-center justify-between gap-3 flex-wrap">
                        <div className="flex items-center gap-2">
                            {cert.is_expired
                                ? <ShieldAlert className="w-4 h-4 text-rose-500" />
                                : <ShieldCheck className="w-4 h-4 text-emerald-500" />}
                            <span className="font-medium text-foreground">{cert.label}</span>
                            {cert.is_expired && (
                                <span className="text-[10px] uppercase font-bold text-rose-500 bg-rose-500/10 border border-rose-500/30 px-1.5 py-0.5 rounded">
                                    {t("presentacion.caducado")}
                                </span>
                            )}
                        </div>
                        <button
                            onClick={() => setUploadOpen(true)}
                            className="text-muted-foreground hover:text-foreground underline"
                        >
                            {t("presentacion.reemplazar")}
                        </button>
                    </div>
                    {cert.subject_cn && (
                        <p className="text-muted-foreground mt-1.5 truncate" title={cert.subject_cn}>
                            <span className="text-foreground/70">{t("presentacion.sujeto")}</span> {cert.subject_cn}
                        </p>
                    )}
                    {cert.valid_until && (
                        <p className="text-muted-foreground mt-0.5">
                            <span className="text-foreground/70">{t("presentacion.validoHasta")}</span> {new Date(cert.valid_until).toLocaleDateString("es-ES")}
                        </p>
                    )}
                </div>
            ) : (
                <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-foreground space-y-2">
                    <div className="flex items-start gap-2">
                        <ShieldAlert className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />
                        <div>
                            <p className="font-medium">{t("presentacion.sinCertTitle")}</p>
                            <p className="text-muted-foreground mt-0.5">
                                {t("presentacion.sinCertDesc")}
                            </p>
                        </div>
                    </div>
                    <button
                        onClick={() => setUploadOpen(true)}
                        className="w-full h-9 rounded-md bg-amber-500/20 hover:bg-amber-500/30 text-amber-500 font-medium text-xs transition"
                    >
                        {t("presentacion.subirCert")}
                    </button>
                </div>
            )}

            {/* Botón de presentar */}
            <button
                onClick={handlePresent}
                disabled={submitting || loading || !cert || cert.is_expired}
                className="w-full h-10 rounded-lg bg-violet-500 hover:brightness-110 text-white font-medium text-sm flex items-center justify-center gap-2 transition disabled:opacity-50"
            >
                {submitting
                    ? <><Loader2 className="w-4 h-4 animate-spin" /> {t("presentacion.firmandoEnviando")}</>
                    : <><Send className="w-4 h-4" /> {t("presentacion.presentar303", { quarter, year })}</>}
            </button>

            {/* Historial reciente */}
            {history.length > 0 && (
                <div>
                    <h5 className="text-xs uppercase tracking-wider font-semibold text-muted-foreground mb-2">{t("presentacion.ultimasPresentaciones")}</h5>
                    <ul className="space-y-1.5">
                        {history.slice(0, 5).map((p) => (
                            <li key={p.id} className="flex items-center gap-2 text-xs">
                                <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded border ${STATUS_TONE[p.status] ?? "bg-muted text-muted-foreground border-border"}`}>
                                    {p.status === "accepted" && <CheckCircle2 className="w-3 h-3" />}
                                    {(p.status === "rejected" || p.status === "error") && <AlertCircle className="w-3 h-3" />}
                                    {(p.status === "pending" || p.status === "signed") && <Clock className="w-3 h-3" />}
                                    {STATUS_LABEL_KEY[p.status] ? t(STATUS_LABEL_KEY[p.status]) : p.status}
                                </span>
                                <span className="text-foreground">{t("presentacion.modBadge", { modelo: p.model_code, periodo: p.period, year: p.year })}</span>
                                {p.csv_justificante && (
                                    <span className="text-muted-foreground font-mono ml-auto" title={t("presentacion.csvJustificante")}>
                                        {p.csv_justificante}
                                    </span>
                                )}
                            </li>
                        ))}
                    </ul>
                </div>
            )}

            <p className="text-[10px] text-muted-foreground">
                <ExternalLink className="w-2.5 h-2.5 inline mr-0.5" />
                {t("presentacion.footnoteDrawer")}
            </p>

            <CertificateUploadModal
                open={uploadOpen}
                onClose={() => setUploadOpen(false)}
                onUploaded={loadAll}
            />
        </div>
    );
}
