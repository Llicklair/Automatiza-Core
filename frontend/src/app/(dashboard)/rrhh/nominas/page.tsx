"use client";

import { useCallback, useEffect, useState } from "react";
import { api, Payroll, Employee, PayrollCalculation } from "@/lib/api";
import {
    WalletCards, Search, CheckCircle2, Clock,
    Send, Download, Bot, Loader2, Sparkles,
    AlertCircle, X, Calculator,
} from "lucide-react";
import { format, startOfMonth, endOfMonth } from "date-fns";
import { es } from "date-fns/locale";
import { logError } from "@/lib/logger";
import { useNotificationStore } from "@/stores/notifications";

export default function PayrollsPage() {
    const [payrolls, setPayrolls] = useState<Payroll[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [generatingPayrolls, setGeneratingPayrolls] = useState(false);
    const [approvingId, setApprovingId] = useState<string | null>(null);
    const [downloadingId, setDownloadingId] = useState<string | null>(null);
    const [toast, setToast] = useState<{ msg: string; type: "ok" | "err" } | null>(null);
    const [search, setSearch] = useState("");
    const [autoOpen, setAutoOpen] = useState(false);
    const [autoEmployees, setAutoEmployees] = useState<Employee[]>([]);
    const [autoEmpLoading, setAutoEmpLoading] = useState(false);
    const [autoEmpId, setAutoEmpId] = useState<string>("");
    const [autoPreview, setAutoPreview] = useState<PayrollCalculation | null>(null);
    const [autoPreviewLoading, setAutoPreviewLoading] = useState(false);
    const [autoSubmitting, setAutoSubmitting] = useState(false);
    const refreshKey = useNotificationStore((s) => s.refreshKey);

    // eslint-disable-next-line react-hooks/exhaustive-deps
    useEffect(() => { loadData(); }, [refreshKey]);

    const loadData = async () => {
        setIsLoading(true);
        try {
            setPayrolls(await api.hr.payrolls.list());
        } catch (e) { logError("rrhh/nominas/page", e); }
        finally { setIsLoading(false); }
    };

    const showToast = (msg: string, type: "ok" | "err") => {
        setToast({ msg, type });
        setTimeout(() => setToast(null), 5000);
    };

    const openAutoModal = () => {
        setAutoOpen(true);
        setAutoPreview(null);
        setAutoEmpId("");
    };

    const loadAutoEmployees = useCallback(async () => {
        setAutoEmpLoading(true);
        try {
            const list = await api.hr.employees.list();
            const active = list.filter((e) => e.status === "active");
            const useList = active.length > 0 ? active : list;
            setAutoEmployees(useList);
            const first = useList[0];
            setAutoEmpId(first?.id ?? "");
        } catch (e) {
            logError("rrhh/nominas/auto-employees", e);
            showToast("No se pudieron cargar empleados.", "err");
        } finally {
            setAutoEmpLoading(false);
        }
    }, []);

    useEffect(() => {
        if (!autoOpen) return;
        void loadAutoEmployees();
    }, [autoOpen, loadAutoEmployees]);

    // eslint-disable-next-line react-hooks/exhaustive-deps
    useEffect(() => {
        if (!autoOpen || !autoEmpId) {
            setAutoPreview(null);
            return;
        }
        let cancelled = false;
        setAutoPreviewLoading(true);
        setAutoPreview(null);
        api.hr.payrolls
            .preview(autoEmpId)
            .then((p) => {
                if (!cancelled) setAutoPreview(p);
            })
            .catch((e: unknown) => {
                if (!cancelled) {
                    logError("rrhh/nominas/preview", e);
                    const msg = e instanceof Error ? e.message : "Preview no disponible";
                    showToast(msg, "err");
                }
            })
            .finally(() => {
                if (!cancelled) setAutoPreviewLoading(false);
            });
        return () => {
            cancelled = true;
        };
    }, [autoOpen, autoEmpId]);

    const handleAutoCreate = async () => {
        if (!autoEmpId) return;
        const now = new Date();
        const periodStart = format(startOfMonth(now), "yyyy-MM-dd");
        const periodEnd = format(endOfMonth(now), "yyyy-MM-dd");
        const issueDate = format(now, "yyyy-MM-dd");
        setAutoSubmitting(true);
        try {
            await api.hr.payrolls.generateAuto({
                employee_id: autoEmpId,
                period_start: periodStart,
                period_end: periodEnd,
                issue_date: issueDate,
                status: "draft",
            });
            showToast("Nómina en borrador creada con cálculo determinista.", "ok");
            setAutoOpen(false);
            await loadData();
        } catch (e: unknown) {
            const msg = e instanceof Error ? e.message : "No se pudo crear la nómina";
            showToast(msg, "err");
        } finally {
            setAutoSubmitting(false);
        }
    };

    const handleGeneratePayrolls = async () => {
        setGeneratingPayrolls(true);
        const now = new Date();
        const monthName = now.toLocaleString("es-ES", { month: "long" });
        const year = now.getFullYear();
        try {
            await api.tasks.create(
                "hr",
                `Genera todas las nóminas del mes de ${monthName} de ${year} para todos los empleados activos del tenant. Créalas en estado DRAFT para revisión humana.`
            );
            showToast(`Agente RRHH lanzado. Generando nóminas de ${monthName} ${year}...`, "ok");
            setTimeout(() => loadData(), 6000);
        } catch (e: any) {
            showToast("Error: " + (e.message || "No se pudo lanzar el agente RRHH"), "err");
        } finally {
            setGeneratingPayrolls(false);
        }
    };

    const handleApprove = async (payroll: Payroll) => {
        setApprovingId(payroll.id);
        try {
            const updated = await api.hr.payrolls.approve(payroll.id);
            setPayrolls(prev => prev.map(p => p.id === updated.id ? updated : p));
            showToast(`Nómina de ${payroll.employee?.name} aprobada. PDF generado en Documentos > Nóminas.`, "ok");
        } catch (e: any) {
            showToast("Error al aprobar: " + e.message, "err");
        } finally {
            setApprovingId(null);
        }
    };

    const handleDownloadPdf = async (payroll: Payroll) => {
        setDownloadingId(payroll.id);
        try {
            const empName = payroll.employee?.name?.replace(/\s+/g, "_") ?? "empleado";
            const period = payroll.period_start
                ? format(new Date(payroll.period_start), "yyyy-MM")
                : "periodo";
            const filename = `Nomina_${empName}_${period}.pdf`;
            await api.hr.payrolls.downloadPdf(payroll.id, filename);
        } catch (e: any) {
            showToast("Error descargando PDF: " + e.message, "err");
        } finally {
            setDownloadingId(null);
        }
    };

    const getStatusBadge = (status: string) => {
        switch (status) {
            case "draft": return <span className="flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-500 border border-amber-500/20"><Clock className="w-3 h-3" /> Borrador</span>;
            case "sent": return <span className="flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20"><Send className="w-3 h-3" /> Emitida</span>;
            case "paid": return <span className="flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"><CheckCircle2 className="w-3 h-3" /> Pagada</span>;
            default: return <span className="text-xs text-zinc-500 capitalize">{status}</span>;
        }
    };

    const fmt = (v: number) => new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" }).format(v);

    const filtered = payrolls.filter(p =>
        (p.employee?.name ?? "").toLowerCase().includes(search.toLowerCase())
    );

    const drafts = payrolls.filter(p => p.status === "draft").length;

    return (
        <div className="min-h-screen bg-[#09090b] text-white p-8">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-8">
                <div>
                    <h1 className="text-3xl font-light text-white flex items-center gap-3">
                        <div className="p-2 bg-emerald-500/10 rounded-xl">
                            <WalletCards className="w-8 h-8 text-emerald-400" />
                        </div>
                        Emisión de Nóminas
                    </h1>
                    <div className="flex items-center gap-2 mt-2 ml-14">
                        <p className="text-zinc-400 text-sm">Revisa, aprueba y descarga las pre-nóminas generadas por la IA.</p>
                        <span className="flex items-center gap-1 px-2 py-0.5 bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 rounded-full text-xs font-medium">
                            <Bot className="w-3 h-3" /> IA-First
                        </span>
                    </div>
                </div>
                <div className="flex flex-wrap gap-3">
                    <button
                        type="button"
                        onClick={openAutoModal}
                        className="flex items-center gap-2 bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-white px-5 py-2.5 rounded-full font-medium transition-colors"
                    >
                        <Calculator className="w-4 h-4 text-emerald-400" />
                        Calcular automática
                    </button>
                    <button
                        onClick={handleGeneratePayrolls}
                        disabled={generatingPayrolls}
                        className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-60 text-white shadow-lg shadow-indigo-500/20 px-5 py-2.5 rounded-full font-medium transition-colors"
                    >
                        {generatingPayrolls ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                        {generatingPayrolls ? "Generando..." : "Generar con IA"}
                    </button>
                    {drafts > 0 && (
                        <button
                            onClick={async () => {
                                const draftPayrolls = payrolls.filter(p => p.status === "draft");
                                for (const p of draftPayrolls) await handleApprove(p);
                            }}
                            className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-500/20 px-5 py-2.5 rounded-full font-medium transition-colors"
                        >
                            <CheckCircle2 className="w-4 h-4" />
                            Aprobar todos ({drafts})
                        </button>
                    )}
                </div>
            </div>

            {/* Tabla */}
            <div className="bg-[#111113] border border-zinc-800 rounded-2xl shadow-2xl flex flex-col overflow-hidden">
                <div className="p-4 border-b border-zinc-800 flex justify-between items-center bg-[#161618]">
                    <div className="relative">
                        <Search className="w-4 h-4 text-zinc-500 absolute left-3 top-1/2 -translate-y-1/2" />
                        <input
                            type="text"
                            placeholder="Buscar empleado..."
                            value={search}
                            onChange={e => setSearch(e.target.value)}
                            className="bg-[#09090b] border border-zinc-800 text-sm text-white rounded-lg pl-10 pr-4 py-2 focus:outline-none focus:border-emerald-500 transition-colors w-64"
                        />
                    </div>
                    <div className="flex items-center gap-2 text-sm text-zinc-400 bg-[#09090b] px-3 py-1.5 rounded-lg border border-zinc-800">
                        <span className={`w-2 h-2 rounded-full ${drafts > 0 ? "bg-amber-500 animate-pulse" : "bg-zinc-600"}`} />
                        Borradores: {drafts}
                    </div>
                </div>

                <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm whitespace-nowrap min-w-[900px]">
                        <thead className="bg-[#161618]/50 text-zinc-400 border-b border-zinc-800">
                            <tr>
                                <th className="px-6 py-4 font-medium">Empleado</th>
                                <th className="px-6 py-4 font-medium">Período</th>
                                <th className="px-6 py-4 font-medium text-right">Bruto</th>
                                <th className="px-6 py-4 font-medium text-right">Deducciones</th>
                                <th className="px-6 py-4 font-medium text-right border-l border-zinc-800">Neto</th>
                                <th className="px-6 py-4 font-medium text-center">Estado</th>
                                <th className="px-6 py-4 font-medium text-right">Acciones</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-zinc-800/50">
                            {isLoading ? (
                                <tr><td colSpan={7} className="px-6 py-12 text-center">
                                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-emerald-500 mx-auto" />
                                </td></tr>
                            ) : filtered.length === 0 ? (
                                <tr><td colSpan={7} className="px-6 py-16 text-center">
                                    <WalletCards className="w-10 h-10 text-zinc-600 mx-auto mb-3" />
                                    <p className="text-zinc-400 font-medium">No hay nóminas aún</p>
                                    <p className="text-zinc-500 text-xs mt-2">
                                        Usa &quot;Calcular automática&quot; (preview + reglas fijas) o &quot;Generar con IA&quot; para el agente RRHH.
                                    </p>
                                </td></tr>
                            ) : filtered.map((payroll) => (
                                <tr key={payroll.id} className="hover:bg-emerald-500/[0.02] transition-colors group">
                                    <td className="px-6 py-4">
                                        <div className="font-medium text-white">{payroll.employee?.name ?? "—"}</div>
                                        <div className="text-[10px] font-mono text-zinc-500 uppercase">PAY-{payroll.id.slice(0, 8)}</div>
                                    </td>
                                    <td className="px-6 py-4 text-zinc-300">
                                        <span className="bg-zinc-800/50 text-xs px-2 py-1 rounded">
                                            {format(new Date(payroll.period_start), "d MMM", { locale: es })} – {format(new Date(payroll.period_end), "d MMM yyyy", { locale: es })}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 text-right text-zinc-400">{fmt(payroll.base_salary)}</td>
                                    <td className="px-6 py-4 text-right text-red-400/80 text-xs">−{fmt(payroll.deductions)}</td>
                                    <td className="px-6 py-4 text-right font-semibold text-emerald-400 border-l border-zinc-800 bg-[#161618]/20 text-base">{fmt(payroll.net_salary)}</td>
                                    <td className="px-6 py-4"><div className="flex justify-center">{getStatusBadge(payroll.status)}</div></td>
                                    <td className="px-6 py-4 text-right">
                                        <div className="flex items-center justify-end gap-1.5">
                                            {/* Descargar PDF */}
                                            <button
                                                onClick={() => handleDownloadPdf(payroll)}
                                                disabled={downloadingId === payroll.id}
                                                className="p-1.5 text-zinc-400 hover:text-indigo-400 bg-zinc-800/50 hover:bg-indigo-500/10 rounded-lg transition-colors disabled:opacity-50"
                                                title="Descargar PDF"
                                            >
                                                {downloadingId === payroll.id
                                                    ? <Loader2 className="w-4 h-4 animate-spin" />
                                                    : <Download className="w-4 h-4" />}
                                            </button>
                                            {/* Aprobar */}
                                            {payroll.status === "draft" && (
                                                <button
                                                    onClick={() => handleApprove(payroll)}
                                                    disabled={approvingId === payroll.id}
                                                    className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-emerald-400 hover:text-emerald-300 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/20 rounded-lg transition-colors disabled:opacity-50"
                                                    title="Aprobar y emitir"
                                                >
                                                    {approvingId === payroll.id
                                                        ? <Loader2 className="w-3 h-3 animate-spin" />
                                                        : <CheckCircle2 className="w-3 h-3" />}
                                                    Aprobar
                                                </button>
                                            )}
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Modal: cálculo automático + preview */}
            {autoOpen && (
                <div
                    className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
                    role="dialog"
                    aria-modal="true"
                    aria-labelledby="auto-payroll-title"
                    onClick={(e) => e.target === e.currentTarget && !autoSubmitting && setAutoOpen(false)}
                >
                    <div className="w-full max-w-lg rounded-2xl border border-zinc-800 bg-[#111113] shadow-2xl overflow-hidden">
                        <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-800">
                            <h2 id="auto-payroll-title" className="text-lg font-medium text-white flex items-center gap-2">
                                <Calculator className="w-5 h-5 text-emerald-400" />
                                Nómina automática (mes actual)
                            </h2>
                            <button
                                type="button"
                                disabled={autoSubmitting}
                                onClick={() => setAutoOpen(false)}
                                className="p-2 rounded-lg text-zinc-400 hover:bg-zinc-800 disabled:opacity-50"
                                aria-label="Cerrar"
                            >
                                <X className="w-4 h-4" />
                            </button>
                        </div>
                        <div className="p-5 space-y-4 max-h-[70vh] overflow-y-auto">
                            {autoEmpLoading ? (
                                <div className="flex justify-center py-8">
                                    <Loader2 className="w-8 h-8 animate-spin text-emerald-500" />
                                </div>
                            ) : autoEmployees.length === 0 ? (
                                <p className="text-sm text-zinc-400 text-center py-4">No hay empleados. Crea uno en RRHH primero.</p>
                            ) : (
                                <>
                                    <label className="block text-xs text-zinc-500 uppercase tracking-wide">Empleado</label>
                                    <select
                                        value={autoEmpId}
                                        onChange={(e) => setAutoEmpId(e.target.value)}
                                        className="w-full bg-[#09090b] border border-zinc-800 rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:border-emerald-500"
                                    >
                                        {autoEmployees.map((e) => (
                                            <option key={e.id} value={e.id}>
                                                {e.name}
                                                {e.base_salary != null ? ` — ${fmt(e.base_salary)}/mes` : " — sin salario base"}
                                            </option>
                                        ))}
                                    </select>
                                    <p className="text-xs text-zinc-500">
                                        Período:{" "}
                                        <span className="text-zinc-300">
                                            {format(startOfMonth(new Date()), "d MMM", { locale: es })} –{" "}
                                            {format(endOfMonth(new Date()), "d MMM yyyy", { locale: es })}
                                        </span>
                                    </p>
                                    <div className="rounded-xl border border-zinc-800 bg-[#09090b] p-4">
                                        <p className="text-xs font-medium text-zinc-400 mb-3">Previsualización del cálculo</p>
                                        {autoPreviewLoading ? (
                                            <div className="flex justify-center py-6">
                                                <Loader2 className="w-6 h-6 animate-spin text-emerald-500" />
                                            </div>
                                        ) : autoPreview ? (
                                            <dl className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-sm">
                                                <dt className="text-zinc-500">Bruto</dt>
                                                <dd className="text-right text-zinc-200">{fmt(autoPreview.base_salary)}</dd>
                                                <dt className="text-zinc-600 text-[11px] col-span-2 pt-1 border-t border-zinc-800/80">
                                                    Cotizaciones SS (empleado, régimen general)
                                                </dt>
                                                <dt className="text-zinc-500 pl-2 text-xs">Contingencias comunes</dt>
                                                <dd className="text-right text-red-400/80 text-xs">−{fmt(autoPreview.ss_contingencias_comunes)}</dd>
                                                <dt className="text-zinc-500 pl-2 text-xs">Desempleo</dt>
                                                <dd className="text-right text-red-400/80 text-xs">−{fmt(autoPreview.ss_desempleo)}</dd>
                                                <dt className="text-zinc-500 pl-2 text-xs">Formación profesional</dt>
                                                <dd className="text-right text-red-400/80 text-xs">−{fmt(autoPreview.ss_formacion_profesional)}</dd>
                                                <dt className="text-zinc-500 pl-2 text-xs">MEI</dt>
                                                <dd className="text-right text-red-400/80 text-xs">−{fmt(autoPreview.ss_mei)}</dd>
                                                <dt className="text-zinc-500">SS total</dt>
                                                <dd className="text-right text-red-400/90">−{fmt(autoPreview.total_ss)}</dd>
                                                <dt className="text-zinc-500">IRPF ({autoPreview.irpf_rate_applied}%)</dt>
                                                <dd className="text-right text-red-400/90">−{fmt(autoPreview.irpf)}</dd>
                                                <dt className="text-zinc-500">Deducciones totales</dt>
                                                <dd className="text-right text-zinc-400">−{fmt(autoPreview.deductions)}</dd>
                                                <dt className="text-zinc-500 font-medium pt-1 border-t border-zinc-800/80">Neto estimado</dt>
                                                <dd className="text-right font-semibold text-emerald-400 pt-1 border-t border-zinc-800/80">{fmt(autoPreview.net_salary)}</dd>
                                            </dl>
                                        ) : (
                                            <p className="text-xs text-zinc-500 py-2">Selecciona un empleado con salario base.</p>
                                        )}
                                    </div>
                                </>
                            )}
                        </div>
                        <div className="flex justify-end gap-2 px-5 py-4 border-t border-zinc-800 bg-[#0c0c0e]">
                            <button
                                type="button"
                                disabled={autoSubmitting}
                                onClick={() => setAutoOpen(false)}
                                className="px-4 py-2 text-sm rounded-lg text-zinc-400 hover:bg-zinc-800 disabled:opacity-50"
                            >
                                Cancelar
                            </button>
                            <button
                                type="button"
                                disabled={
                                    autoSubmitting ||
                                    !autoEmpId ||
                                    autoPreviewLoading ||
                                    !autoPreview ||
                                    autoEmployees.length === 0
                                }
                                onClick={() => void handleAutoCreate()}
                                className="flex items-center gap-2 px-4 py-2 text-sm rounded-lg font-medium bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white"
                            >
                                {autoSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
                                Crear borrador
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Toast */}
            {toast && (
                <div className={`fixed bottom-6 right-6 z-50 flex items-center gap-3 px-5 py-3 rounded-2xl shadow-2xl text-sm font-medium max-w-sm ${toast.type === "ok"
                    ? "bg-emerald-500/10 border border-emerald-500/20 text-emerald-400"
                    : "bg-red-500/10 border border-red-500/20 text-red-400"
                    }`}>
                    {toast.type === "ok" ? <CheckCircle2 className="w-5 h-5 flex-shrink-0" /> : <AlertCircle className="w-5 h-5 flex-shrink-0" />}
                    <span className="flex-1">{toast.msg}</span>
                    <button onClick={() => setToast(null)} className="opacity-60 hover:opacity-100"><X className="w-4 h-4" /></button>
                </div>
            )}
        </div>
    );
}
