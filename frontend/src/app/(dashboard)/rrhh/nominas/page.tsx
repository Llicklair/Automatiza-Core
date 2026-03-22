"use client";

import { useEffect, useState } from "react";
import { api, Payroll } from "@/lib/api";
import {
    WalletCards, Search, CheckCircle2, Clock,
    Send, Download, Bot, Loader2, Sparkles,
    AlertCircle, X
} from "lucide-react";
import { format } from "date-fns";
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
                <div className="flex gap-3">
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
                                    <p className="text-zinc-500 text-xs mt-2">Haz clic en &quot;Generar con IA&quot; para calcular las pre-nóminas del mes.</p>
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
