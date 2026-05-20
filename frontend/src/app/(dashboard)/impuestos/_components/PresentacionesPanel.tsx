"use client";

import { useEffect, useState } from "react";
import {
    ShieldCheck, ShieldAlert, Send, Loader2, CheckCircle2, AlertCircle, Clock,
    Sparkles, Receipt,
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

const MODELS: ModelMeta[] = [
    { code: "303", nombre: "IVA trimestral",          periodicidad: "quarterly", descripcion: "Autoliquidación de IVA del trimestre." },
    { code: "130", nombre: "IRPF fraccionado",        periodicidad: "quarterly", descripcion: "Pago fraccionado IRPF estimación directa." },
    { code: "111", nombre: "Retenciones IRPF",        periodicidad: "quarterly", descripcion: "Retenciones a trabajadores y profesionales." },
    { code: "115", nombre: "Retenciones alquileres",  periodicidad: "quarterly", descripcion: "Retenciones 19% sobre arrendamientos de inmuebles urbanos." },
    { code: "349", nombre: "Intracomunitarias",       periodicidad: "quarterly", descripcion: "Operaciones con clientes/proveedores UE (NIF intracomunitario)." },
    { code: "390", nombre: "Resumen anual IVA",       periodicidad: "yearly",    descripcion: "Consolidación anual de los 4 trimestres del 303." },
    { code: "190", nombre: "Resumen anual retenciones", periodicidad: "yearly",  descripcion: "Resumen anual de retenciones IRPF (consolida 111)." },
    { code: "347", nombre: "Operaciones con terceros", periodicidad: "yearly",   descripcion: "Contrapartes con operaciones >3.005,06€ anuales." },
];

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

function currentDefaults(): { quarter: number; year: number } {
    const d = new Date();
    return { quarter: Math.floor(d.getMonth() / 3) + 1, year: d.getFullYear() };
}

export function PresentacionesPanel() {
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
        if (!cert) { toast.error("Sube primero el certificado AEAT"); return; }
        if (cert.is_expired) { toast.error("El certificado activo está caducado"); return; }
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
                toast.success(`Simulado OK. CSV: ${result.csv_justificante}`);
            } else {
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
        <div className="rounded-2xl border border-violet-500/20 bg-gradient-to-br from-violet-500/5 via-card to-card p-5 space-y-5">
            <div className="flex items-start gap-3 flex-wrap">
                <div className="flex-shrink-0 w-11 h-11 rounded-xl bg-violet-500/15 text-violet-400 flex items-center justify-center">
                    <Sparkles className="w-5 h-5" />
                </div>
                <div className="flex-1 min-w-[220px]">
                    <div className="flex items-center gap-2">
                        <h3 className="text-sm font-semibold text-foreground">Presentación electrónica AEAT</h3>
                        <span className="text-[10px] uppercase tracking-wider font-bold bg-amber-500/15 text-amber-500 border border-amber-500/30 px-1.5 py-0.5 rounded">BETA</span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-0.5">
                        Firma XAdES con tu certificado + envío a SEDE. Por defecto en modo <b>simulación (dry-run)</b>.
                    </p>
                </div>
                {cert && !cert.is_expired && (
                    <span className="inline-flex items-center gap-1.5 text-xs font-medium text-emerald-500 bg-emerald-500/10 border border-emerald-500/30 px-2 py-1 rounded">
                        <ShieldCheck className="w-3.5 h-3.5" />
                        Certificado OK
                    </span>
                )}
            </div>

            {/* Estado certificado o invitación a subirlo */}
            {loading ? (
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <Loader2 className="w-3.5 h-3.5 animate-spin" /> Cargando estado…
                </div>
            ) : !cert ? (
                <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs space-y-2">
                    <div className="flex items-start gap-2">
                        <ShieldAlert className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />
                        <p className="text-foreground">
                            <b>No hay certificado configurado.</b> Necesario para firmar las presentaciones.
                        </p>
                    </div>
                    <button
                        onClick={() => setUploadOpen(true)}
                        className="w-full h-9 rounded-md bg-amber-500/20 hover:bg-amber-500/30 text-amber-500 font-medium text-xs transition"
                    >
                        Subir certificado AEAT
                    </button>
                </div>
            ) : cert.is_expired ? (
                <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-xs space-y-2">
                    <div className="flex items-start gap-2">
                        <ShieldAlert className="w-4 h-4 text-rose-500 flex-shrink-0 mt-0.5" />
                        <p>El certificado <b>{cert.label}</b> está caducado.</p>
                    </div>
                    <button
                        onClick={() => setUploadOpen(true)}
                        className="w-full h-9 rounded-md bg-rose-500/20 hover:bg-rose-500/30 text-rose-500 font-medium text-xs transition"
                    >
                        Reemplazar certificado
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
                                    Válido hasta {new Date(cert.valid_until).toLocaleDateString("es-ES")}
                                </p>
                            )}
                        </div>
                        <button onClick={() => setUploadOpen(true)} className="text-muted-foreground hover:text-foreground underline">
                            Reemplazar
                        </button>
                    </div>
                </div>
            )}

            {/* Selector de modelo y periodo */}
            <div className="grid grid-cols-1 lg:grid-cols-[1fr_auto_auto_auto] gap-2 items-end">
                <div>
                    <label className="block text-[11px] uppercase tracking-wider text-muted-foreground mb-1">Modelo</label>
                    <select
                        value={modelCode}
                        onChange={(e) => setModelCode(e.target.value as ModelCode)}
                        className="w-full h-9 px-2 rounded-md border border-border bg-card text-sm"
                    >
                        {MODELS.map((m) => (
                            <option key={m.code} value={m.code}>
                                Modelo {m.code} · {m.nombre} ({m.periodicidad === "quarterly" ? "trim." : "anual"})
                            </option>
                        ))}
                    </select>
                </div>
                {meta.periodicidad === "quarterly" && (
                    <div>
                        <label className="block text-[11px] uppercase tracking-wider text-muted-foreground mb-1">Trim.</label>
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
                    <label className="block text-[11px] uppercase tracking-wider text-muted-foreground mb-1">Año</label>
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
                    Presentar (sim.)
                </button>
            </div>

            <p className="text-xs text-muted-foreground -mt-3">{meta.descripcion}</p>

            {/* Historial */}
            {history.length > 0 && (
                <div>
                    <h4 className="text-[11px] uppercase tracking-wider font-semibold text-muted-foreground mb-2">Últimas presentaciones</h4>
                    <div className="rounded-lg border border-border overflow-hidden">
                        <table className="w-full text-xs">
                            <thead className="bg-muted/30 text-muted-foreground">
                                <tr>
                                    <th className="text-left px-3 py-2 font-medium">Modelo</th>
                                    <th className="text-left px-3 py-2 font-medium">Periodo</th>
                                    <th className="text-left px-3 py-2 font-medium">Estado</th>
                                    <th className="text-left px-3 py-2 font-medium">CSV / Error</th>
                                    <th className="text-right px-3 py-2 font-medium">Fecha</th>
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
                                                {STATUS_LABEL[p.status] ?? p.status}
                                            </span>
                                        </td>
                                        <td className="px-3 py-2 text-muted-foreground font-mono text-[10px] max-w-[180px] truncate" title={p.csv_justificante ?? p.error_message ?? ""}>
                                            {p.csv_justificante ?? p.error_message ?? "—"}
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
                Aviso: en modo simulación el XML se firma localmente (stub si no hay xmlsec) y NO se envía a la SEDE. Para producción real: instalar signxml + libxmlsec1, validar contra el XSD oficial AEAT del año fiscal, y desactivar el flag dry_run.
            </p>

            <CertificateUploadModal
                open={uploadOpen}
                onClose={() => setUploadOpen(false)}
                onUploaded={loadAll}
            />
        </div>
    );
}
