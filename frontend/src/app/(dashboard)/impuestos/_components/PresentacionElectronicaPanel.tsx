"use client";

import { useEffect, useState } from "react";
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

const STATUS_LABEL: Record<string, string> = {
    pending: "Pendiente", signed: "Firmado", submitted: "Enviado",
    accepted: "Aceptado", rejected: "Rechazado", error: "Error",
};

export function PresentacionElectronicaPanel({ quarter, year }: Props) {
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
        if (!cert) { toast.error("Sube primero el certificado AEAT"); return; }
        if (cert.is_expired) { toast.error("El certificado activo está caducado"); return; }
        setSubmitting(true);
        try {
            const created = await api.aeat.presentations.create303FromQuarter(quarter, year, "preproduccion");
            // Acto seguido: submit dry-run
            const result = await api.aeat.presentations.submit(created.id, true);
            if (result.status === "accepted") {
                toast.success(`Simulado OK. CSV: ${result.csv_justificante}`);
            } else if (result.status === "error" || result.status === "rejected") {
                toast.error(`${result.error_code ?? "Error"}: ${result.error_message ?? "—"}`);
            }
            loadAll();
        } catch (e) {
            toast.error(e instanceof Error ? e.message : "Error en la presentación");
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
                        <h4 className="text-sm font-semibold text-foreground">Presentación electrónica</h4>
                        <span className="text-[10px] uppercase tracking-wider font-bold bg-amber-500/15 text-amber-500 border border-amber-500/30 px-1.5 py-0.5 rounded">BETA</span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-0.5">
                        Firma XAdES con tu certificado + envío a SEDE AEAT. Por defecto se ejecuta en modo <b>simulación (dry-run)</b> hasta que valides el flujo completo.
                    </p>
                </div>
            </div>

            {/* Estado del certificado */}
            {loading ? (
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <Loader2 className="w-3.5 h-3.5 animate-spin" /> Cargando estado…
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
                                    Caducado
                                </span>
                            )}
                        </div>
                        <button
                            onClick={() => setUploadOpen(true)}
                            className="text-muted-foreground hover:text-foreground underline"
                        >
                            Reemplazar
                        </button>
                    </div>
                    {cert.subject_cn && (
                        <p className="text-muted-foreground mt-1.5 truncate" title={cert.subject_cn}>
                            <span className="text-foreground/70">Sujeto:</span> {cert.subject_cn}
                        </p>
                    )}
                    {cert.valid_until && (
                        <p className="text-muted-foreground mt-0.5">
                            <span className="text-foreground/70">Válido hasta:</span> {new Date(cert.valid_until).toLocaleDateString("es-ES")}
                        </p>
                    )}
                </div>
            ) : (
                <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-foreground space-y-2">
                    <div className="flex items-start gap-2">
                        <ShieldAlert className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />
                        <div>
                            <p className="font-medium">No hay certificado configurado</p>
                            <p className="text-muted-foreground mt-0.5">
                                Necesitas subir un certificado .pfx/.p12 del representante para firmar las presentaciones.
                            </p>
                        </div>
                    </div>
                    <button
                        onClick={() => setUploadOpen(true)}
                        className="w-full h-9 rounded-md bg-amber-500/20 hover:bg-amber-500/30 text-amber-500 font-medium text-xs transition"
                    >
                        Subir certificado AEAT
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
                    ? <><Loader2 className="w-4 h-4 animate-spin" /> Firmando y enviando (simulación)…</>
                    : <><Send className="w-4 h-4" /> Presentar 303 — {quarter}T {year} (simulación)</>}
            </button>

            {/* Historial reciente */}
            {history.length > 0 && (
                <div>
                    <h5 className="text-xs uppercase tracking-wider font-semibold text-muted-foreground mb-2">Últimas presentaciones</h5>
                    <ul className="space-y-1.5">
                        {history.slice(0, 5).map((p) => (
                            <li key={p.id} className="flex items-center gap-2 text-xs">
                                <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded border ${STATUS_TONE[p.status] ?? "bg-muted text-muted-foreground border-border"}`}>
                                    {p.status === "accepted" && <CheckCircle2 className="w-3 h-3" />}
                                    {(p.status === "rejected" || p.status === "error") && <AlertCircle className="w-3 h-3" />}
                                    {(p.status === "pending" || p.status === "signed") && <Clock className="w-3 h-3" />}
                                    {STATUS_LABEL[p.status] ?? p.status}
                                </span>
                                <span className="text-foreground">Mod. {p.model_code} · {p.period} {p.year}</span>
                                {p.csv_justificante && (
                                    <span className="text-muted-foreground font-mono ml-auto" title="CSV justificante">
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
                En modo simulación el XML se firma localmente (o con stub si no hay xmlsec) y NO se envía a la SEDE. Activar producción requiere validar el flujo y desactivar el flag <code>dry_run</code>.
            </p>

            <CertificateUploadModal
                open={uploadOpen}
                onClose={() => setUploadOpen(false)}
                onUploaded={loadAll}
            />
        </div>
    );
}
