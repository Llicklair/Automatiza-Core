"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api, type Task, type Approval, type Invoice, type GmailMessage, type DriveFile, type OutlookMessage, type OneDriveFile } from "@/lib/api";
import { useNotificationStore } from "@/stores/notifications";
import {
    CheckCircle2, AlertCircle, Clock, Zap, Wallet,
    TrendingUp, TrendingDown, ArrowRight, FileText, Activity,
    BrainCircuit, Sparkles, AlertTriangle, Lightbulb,
    SendHorizonal, Loader2, Bot, Mail, HardDrive, XCircle,
    FileSpreadsheet, FileImage, File as FileIcon, FolderOpen,
} from "lucide-react";
import { AreaChart, Area, XAxis, YAxis, Tooltip as RTooltip, ResponsiveContainer } from "recharts";
import Link from "next/link";

const SUGGESTIONS = [
    "¿Cuánto he facturado este mes?",
    "Genera las nóminas del mes",
    "¿Tengo facturas pendientes de cobro?",
    "Revisa mis obligaciones fiscales",
    "Crea una factura para cliente nuevo",
];

function AiChatBar() {
    const router = useRouter();
    const [input, setInput] = useState("");
    const [sending, setSending] = useState(false);
    const [lastResult, setLastResult] = useState<string | null>(null);
    const inputRef = useRef<HTMLInputElement>(null);

    async function send(text: string) {
        const msg = text.trim();
        if (!msg) return;
        setSending(true);
        setLastResult(null);
        setInput("");
        try {
            const task = await api.tasks.create("coordinator", msg);
            setLastResult(`Tarea enviada al agente. Puedes seguir el progreso en Tareas IA.`);
            // Poll breve para resultado rápido
            let attempts = 0;
            const poll = setInterval(async () => {
                attempts++;
                try {
                    const t = await api.tasks.get(task.id);
                    if (t.status === "done" && t.agent_results) {
                        const results = t.agent_results as any[];
                        const summary = results[results.length - 1]?.summary || results[results.length - 1]?.output_message;
                        if (summary) setLastResult(summary);
                        clearInterval(poll);
                    } else if (["failed", "cancelled"].includes(t.status)) {
                        setLastResult("El agente no pudo completar la tarea. Revisa Tareas IA.");
                        clearInterval(poll);
                    } else if (attempts >= 10) {
                        clearInterval(poll);
                    }
                } catch { clearInterval(poll); }
            }, 2000);
        } catch {
            setLastResult("Error al enviar la tarea. Inténtalo de nuevo.");
        } finally {
            setSending(false);
        }
    }

    return (
        <div className="relative z-10">
            {/* Input bar */}
            <div className="flex items-center gap-3 bg-[#111113] border border-indigo-500/30 rounded-2xl px-4 py-3 shadow-lg shadow-indigo-500/5 focus-within:border-indigo-500/60 transition-colors">
                <div className="w-7 h-7 rounded-lg bg-indigo-600 flex items-center justify-center flex-shrink-0">
                    <Bot className="w-3.5 h-3.5 text-white" />
                </div>
                <input
                    ref={inputRef}
                    type="text"
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    onKeyDown={e => e.key === "Enter" && !e.shiftKey && send(input)}
                    placeholder="Pregunta o pide algo a tu asistente IA..."
                    className="flex-1 bg-transparent text-white placeholder-zinc-500 text-sm focus:outline-none"
                    disabled={sending}
                />
                <button
                    onClick={() => send(input)}
                    disabled={sending || !input.trim()}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-xs font-medium transition flex-shrink-0"
                >
                    {sending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <SendHorizonal className="w-3.5 h-3.5" />}
                    {sending ? "Procesando…" : "Enviar"}
                </button>
            </div>

            {/* Sugerencias rápidas */}
            {!lastResult && (
                <div className="flex flex-wrap gap-2 mt-2.5">
                    {SUGGESTIONS.map(s => (
                        <button
                            key={s}
                            onClick={() => send(s)}
                            disabled={sending}
                            className="text-xs px-3 py-1.5 rounded-full bg-white/5 border border-white/10 text-zinc-400 hover:text-white hover:bg-white/10 hover:border-white/20 transition disabled:opacity-40"
                        >
                            {s}
                        </button>
                    ))}
                </div>
            )}

            {/* Resultado inline */}
            {lastResult && (
                <div className="mt-3 flex items-start gap-2.5 bg-indigo-500/5 border border-indigo-500/20 rounded-xl px-4 py-3">
                    <Sparkles className="w-4 h-4 text-indigo-400 flex-shrink-0 mt-0.5" />
                    <div className="flex-1 min-w-0">
                        <p className="text-sm text-zinc-200 leading-relaxed">{lastResult}</p>
                        <button
                            onClick={() => { setLastResult(null); inputRef.current?.focus(); }}
                            className="text-xs text-indigo-400 hover:text-indigo-300 mt-1.5 transition"
                        >
                            Nueva pregunta
                        </button>
                    </div>
                    <Link href="/tareas" className="text-xs text-zinc-500 hover:text-zinc-300 transition flex-shrink-0">
                        Ver tareas →
                    </Link>
                </div>
            )}
        </div>
    );
}

const STATUS_CONFIG: Record<string, { label: string; color: string; dot: string }> = {
    pending: { label: "Pendiente", color: "text-zinc-400", dot: "bg-zinc-500" },
    planning: { label: "Planificando", color: "text-blue-400", dot: "bg-blue-400" },
    executing: { label: "Ejecutando", color: "text-indigo-400", dot: "bg-indigo-400" },
    awaiting_approval: { label: "Aprobación", color: "text-amber-400", dot: "bg-amber-400" },
    done: { label: "Completada", color: "text-emerald-400", dot: "bg-emerald-400" },
    failed: { label: "Fallida", color: "text-red-400", dot: "bg-red-500" },
    cancelled: { label: "Cancelada", color: "text-zinc-500", dot: "bg-zinc-600" },
};

function StatusBadge({ status }: { status: string }) {
    const cfg = STATUS_CONFIG[status] ?? { label: status, color: "text-zinc-400", dot: "bg-zinc-500" };
    return (
        <span className={`inline-flex items-center gap-1.5 text-[11px] font-medium px-2.5 py-1 rounded-full bg-zinc-800 border border-white/5 ${cfg.color}`}>
            <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
            {cfg.label}
        </span>
    );
}

// Invoice status badge (reused logic from facturas/page)
function InvBadge({ status }: { status: string }) {
    switch (status) {
        case 'draft': return <span className="text-[10px] uppercase font-bold text-zinc-500">Borrador</span>;
        case 'pending': return <span className="text-[10px] uppercase font-bold text-amber-500">Pendiente</span>;
        case 'paid': return <span className="text-[10px] uppercase font-bold text-emerald-500">Cobrada</span>;
        case 'overdue': return <span className="text-[10px] uppercase font-bold text-red-500">Vencida</span>;
        default: return <span className="text-[10px] uppercase font-bold text-zinc-500">{status}</span>;
    }
}

function getGreeting(name: string) {
    const h = new Date().getHours();
    const saludo = h < 14 ? "Buenos días" : h < 21 ? "Buenas tardes" : "Buenas noches";
    return name ? `${saludo}, ${name}` : saludo;
}

function decodeJwtName(token: string): string {
    try {
        const payload = JSON.parse(atob(token.split(".")[1]));
        return payload.full_name || payload.name || payload.sub?.split("@")[0] || "";
    } catch { return ""; }
}

export default function DashboardPage() {
    const [tasks, setTasks] = useState<Task[]>([]);
    const [approvals, setApprovals] = useState<Approval[]>([]);
    const [invoices, setInvoices] = useState<Invoice[]>([]);
    const [summary, setSummary] = useState({ ingresos: 0, gastos: 0, neto: 0, margen: 0 });
    const [analytics, setAnalytics] = useState<{ cashflow: any[], insights: any[] }>({ cashflow: [], insights: [] });
    const [loading, setLoading] = useState(true);
    const [userName, setUserName] = useState("");
    const [gmailConnected, setGmailConnected] = useState(false);
    const [gdriveConnected, setGdriveConnected] = useState(false);
    const [outlookConnected, setOutlookConnected] = useState(false);
    const [onedriveConnected, setOnedriveConnected] = useState(false);
    const [gmailMessages, setGmailMessages] = useState<GmailMessage[]>([]);
    const [driveFiles, setDriveFiles] = useState<DriveFile[]>([]);
    const [outlookMessages, setOutlookMessages] = useState<OutlookMessage[]>([]);
    const [onedriveFiles, setOnedriveFiles] = useState<OneDriveFile[]>([]);
    const [activeTab, setActiveTab] = useState<"gmail" | "outlook" | "drive" | "onedrive">("gmail");
    const refreshKey = useNotificationStore((s) => s.refreshKey);

    useEffect(() => {
        const token = localStorage.getItem("access_token");
        if (token) setUserName(decodeJwtName(token));
    }, []);

    useEffect(() => {
        Promise.all([
            api.banking.summary().catch(() => ({ ingresos: 0, gastos: 0, neto: 0, margen: 0, is_demo: true })),
            api.erp.invoices.list({ limit: 5 }).catch(() => []),
            api.tasks.list({ limit: 6 }).catch(() => []),
            api.approvals.list().catch(() => []),
            api.banking.analytics().catch(() => ({ cashflow: [], insights: [] })),
            api.integrations.gmailStatus().catch(() => ({ connected: false })),
            api.integrations.gdriveStatus().catch(() => ({ connected: false })),
            api.integrations.outlookStatus().catch(() => ({ connected: false })),
            api.integrations.onedriveStatus().catch(() => ({ connected: false })),
        ])
            .then(([sum, inv, t, a, an, gs, ds, os, ods]) => {
                setSummary(sum);
                setInvoices(inv);
                setTasks(t);
                setApprovals(a);
                setAnalytics(an);
                setGmailConnected(gs.connected);
                setGdriveConnected(ds.connected);
                setOutlookConnected(os.connected);
                setOnedriveConnected(ods.connected);
                // Auto-select first connected tab
                if (gs.connected) setActiveTab("gmail");
                else if (os.connected) setActiveTab("outlook");
                else if (ds.connected) setActiveTab("drive");
                else if (ods.connected) setActiveTab("onedrive");
                // Load recent data only if connected
                if (gs.connected) api.integrations.gmailRecent().then(setGmailMessages).catch(() => {});
                if (ds.connected) api.integrations.gdriveRecent().then(setDriveFiles).catch(() => {});
                if (os.connected) api.integrations.outlookRecent().then(setOutlookMessages).catch(() => {});
                if (ods.connected) api.integrations.onedriveRecent().then(setOnedriveFiles).catch(() => {});
            })
            .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [refreshKey]);

    const netoIsPositive = summary.neto >= 0;

    return (
        <div className="p-8 max-w-[1400px] mx-auto space-y-8 relative z-0">
            {/* Ambient glow — subtle, only visible en dark backgrounds */}
            <div className="pointer-events-none fixed top-0 left-64 w-[600px] h-[400px] opacity-30" style={{ zIndex: -1 }}>
                <div className="absolute top-0 left-0 w-96 h-96 bg-indigo-600/15 rounded-full blur-3xl animate-pulse" />
                <div className="absolute top-16 left-48 w-64 h-64 bg-violet-600/10 rounded-full blur-3xl animate-pulse" style={{ animationDelay: "2s", animationDuration: "4s" }} />
            </div>

            {/* Header */}
            <div className="relative z-10">
                <h1 className="text-3xl font-bold text-white tracking-tight">{getGreeting(userName)}</h1>
                <p className="mt-1 text-sm text-zinc-400">
                    Aquí tienes el resumen financiero y operativo de tu negocio.
                </p>
            </div>

            {/* Chat IA */}
            <AiChatBar />

            {/* KPIs Financieros Principales */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Ingresos */}
                <div className="rounded-2xl border border-emerald-500/20 bg-gradient-to-br from-[#111113] to-emerald-950/20 p-6 relative overflow-hidden group">
                    <div className="absolute -right-4 -top-4 w-24 h-24 bg-emerald-500/10 rounded-full blur-2xl group-hover:bg-emerald-500/20 transition-all duration-500"></div>
                    <div className="flex items-center gap-3 mb-4 relative">
                        <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
                            <TrendingUp className="w-5 h-5 text-emerald-400" />
                        </div>
                        <h3 className="text-sm font-medium text-emerald-400/80">Ingresos (30d)</h3>
                    </div>
                    <div className="text-4xl font-bold text-white tracking-tight relative">
                        {loading ? "—" : `${summary.ingresos.toLocaleString('es-ES', { minimumFractionDigits: 2 })}€`}
                    </div>
                </div>

                {/* Gastos */}
                <div className="rounded-2xl border border-red-500/20 bg-gradient-to-br from-[#111113] to-red-950/20 p-6 relative overflow-hidden group">
                    <div className="absolute -right-4 -top-4 w-24 h-24 bg-red-500/10 rounded-full blur-2xl group-hover:bg-red-500/20 transition-all duration-500"></div>
                    <div className="flex items-center gap-3 mb-4 relative">
                        <div className="w-10 h-10 rounded-xl bg-red-500/10 border border-red-500/20 flex items-center justify-center">
                            <TrendingDown className="w-5 h-5 text-red-400" />
                        </div>
                        <h3 className="text-sm font-medium text-red-400/80">Gastos (30d)</h3>
                    </div>
                    <div className="text-4xl font-bold text-white tracking-tight relative">
                        {loading ? "—" : `${Math.abs(summary.gastos).toLocaleString('es-ES', { minimumFractionDigits: 2 })}€`}
                    </div>
                </div>

                {/* Beneficio */}
                <div className={`rounded-2xl border ${netoIsPositive ? 'border-indigo-500/30 bg-gradient-to-br from-[#111113] to-indigo-900/20' : 'border-amber-500/30 bg-gradient-to-br from-[#111113] to-amber-900/20'} p-6 relative overflow-hidden group shadow-lg shadow-black/50`}>
                    <div className={`absolute -right-4 -top-4 w-32 h-32 ${netoIsPositive ? 'bg-indigo-500/10' : 'bg-amber-500/10'} rounded-full blur-3xl group-hover:scale-110 transition-transform duration-700`}></div>
                    <div className="flex items-center justify-between mb-4 relative">
                        <div className="flex items-center gap-3">
                            <div className={`w-10 h-10 rounded-xl ${netoIsPositive ? 'bg-indigo-500/20 border-indigo-500/30' : 'bg-amber-500/20 border-amber-500/30'} border flex items-center justify-center`}>
                                <Wallet className={`w-5 h-5 ${netoIsPositive ? 'text-indigo-400' : 'text-amber-400'}`} />
                            </div>
                            <h3 className={`text-sm font-medium ${netoIsPositive ? 'text-indigo-300' : 'text-amber-300'}`}>Beneficio Neto</h3>
                        </div>
                        {!loading && (
                            <span className={`text-xs px-2.5 py-1 rounded-full font-bold border ${netoIsPositive ? 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20' : 'bg-amber-500/10 text-amber-400 border-amber-500/20'}`}>
                                {summary.margen > 0 ? '+' : ''}{summary.margen}% Margen
                            </span>
                        )}
                    </div>
                    <div className="text-4xl font-bold text-white tracking-tight relative">
                        {loading ? "—" : `${summary.neto.toLocaleString('es-ES', { minimumFractionDigits: 2 })}€`}
                    </div>
                </div>
            </div>

            {/* Layout Inferior: Cuadrícula principal */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">

                {/* Columna Izquierda Ancha: Facturas Recientes */}
                <div className="lg:col-span-2 space-y-6">

                    {/* Resumen e Insights IA */}
                    {!loading && analytics.insights?.length > 0 && (
                        <div className="bg-[#111113] border border-indigo-500/20 rounded-2xl overflow-hidden shadow-lg shadow-indigo-500/5 relative">
                            <div className="absolute top-0 right-0 p-4 opacity-10 blur-xl pointer-events-none">
                                <BrainCircuit className="w-48 h-48 text-indigo-500" />
                            </div>
                            <div className="px-6 py-5 border-b border-indigo-500/10 flex items-center justify-between relative z-10 bg-gradient-to-r from-indigo-500/10 to-transparent">
                                <h2 className="text-base font-semibold text-white flex items-center gap-2">
                                    <Sparkles className="w-5 h-5 text-indigo-400" /> Sugerencias Estratégicas IA
                                </h2>
                            </div>
                            <div className="p-6 relative z-10 grid grid-cols-1 md:grid-cols-3 gap-4">
                                {analytics.insights.map((insight: any) => {
                                    let icon = <Lightbulb className="w-4 h-4 text-indigo-400" />;
                                    let bg = "bg-indigo-500/5 border-indigo-500/10 hover:bg-indigo-500/10 hover:border-indigo-500/20";
                                    let titleC = "text-indigo-300";

                                    if (insight.type === 'warning') {
                                        icon = <AlertTriangle className="w-4 h-4 text-amber-400" />;
                                        bg = "bg-amber-500/5 border-amber-500/10 hover:bg-amber-500/10 hover:border-amber-500/20";
                                        titleC = "text-amber-300";
                                    } else if (insight.type === 'success') {
                                        icon = <TrendingUp className="w-4 h-4 text-emerald-400" />;
                                        bg = "bg-emerald-500/5 border-emerald-500/10 hover:bg-emerald-500/10 hover:border-emerald-500/20";
                                        titleC = "text-emerald-300";
                                    }

                                    return (
                                        <div key={insight.id} className={`rounded-xl border ${bg} p-5 flex flex-col justify-between transition-all duration-300 cursor-default group`}>
                                            <div>
                                                <div className="flex items-center gap-2 mb-3">
                                                    {icon}
                                                    <h4 className={`text-sm font-semibold ${titleC}`}>{insight.title}</h4>
                                                </div>
                                                <p className="text-xs text-zinc-400 leading-relaxed mb-4">{insight.message}</p>
                                            </div>
                                            <Link href={insight.action_url} className={`text-xs font-medium text-white opacity-60 group-hover:opacity-100 group-hover:underline transition-opacity flex items-center gap-1`}>
                                                {insight.action_text} <ArrowRight className="w-3 h-3" />
                                            </Link>
                                        </div>
                                    )
                                })}
                            </div>
                        </div>
                    )}

                    {/* Gráfico de Evolución Cashflow */}
                    {!loading && analytics.cashflow?.length > 0 && (
                        <div className="bg-[#111113] border border-[#27272a] rounded-2xl p-6 shadow-lg shadow-black/20">
                            <h2 className="text-sm font-semibold text-white mb-6 flex items-center gap-2">
                                <Activity className="w-4 h-4 text-zinc-400" /> Cashflow — Evolución semestral
                            </h2>
                            <div className="h-[250px] w-full">
                                <ResponsiveContainer width="100%" height="100%">
                                    <AreaChart data={analytics.cashflow} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                                        <defs>
                                            <linearGradient id="colorIn" x1="0" y1="0" x2="0" y2="1">
                                                <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                                                <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                                            </linearGradient>
                                            <linearGradient id="colorOut" x1="0" y1="0" x2="0" y2="1">
                                                <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                                                <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                                            </linearGradient>
                                        </defs>
                                        <XAxis dataKey="month" stroke="#52525b" fontSize={12} tickLine={false} axisLine={false} />
                                        <YAxis stroke="#52525b" fontSize={12} tickLine={false} axisLine={false} tickFormatter={(v) => `${(v / 1000).toFixed(1)}k`} />
                                        <RTooltip
                                            contentStyle={{ backgroundColor: '#18181b', borderColor: '#27272a', borderRadius: '8px', fontSize: '12px' }}
                                            itemStyle={{ color: '#e4e4e7' }}
                                            formatter={((value: unknown) => [`${Number(value)?.toLocaleString() ?? 0}€`]) as never}
                                        />
                                        <Area type="monotone" dataKey="ingresos" name="Ingresos" stroke="#10b981" strokeWidth={2} fillOpacity={1} fill="url(#colorIn)" />
                                        <Area type="monotone" dataKey="gastos" name="Gastos" stroke="#ef4444" strokeWidth={2} fillOpacity={1} fill="url(#colorOut)" />
                                    </AreaChart>
                                </ResponsiveContainer>
                            </div>
                        </div>
                    )}

                    {/* Facturas Recientes */}
                    <div className="bg-[#111113] border border-[#27272a] rounded-2xl overflow-hidden flex flex-col h-full">
                        <div className="px-6 py-5 border-b border-[#27272a] flex items-center justify-between bg-zinc-900/30">
                            <h2 className="text-base font-semibold text-white flex items-center gap-2">
                                <FileText className="w-4 h-4 text-zinc-400" /> Facturación Reciente
                            </h2>
                            <Link href="/ventas/facturas" className="text-xs font-medium text-indigo-400 hover:text-indigo-300 transition-colors flex items-center gap-1 bg-indigo-500/10 px-3 py-1.5 rounded-lg hover:bg-indigo-500/20">
                                Ver todas <ArrowRight className="w-3 h-3" />
                            </Link>
                        </div>

                        <div className="flex-1 p-0">
                            {loading ? (
                                <div className="p-12 text-center text-zinc-500 text-sm">Cargando facturas...</div>
                            ) : invoices.length === 0 ? (
                                <div className="p-16 text-center text-zinc-500 flex flex-col items-center">
                                    <FileText className="w-12 h-12 text-zinc-700 mb-3" />
                                    <p className="text-sm text-zinc-400">Aún no hay facturas emitidas</p>
                                    <Link href="/ventas/facturas/nueva" className="mt-4 text-xs bg-white/5 hover:bg-white/10 text-white px-4 py-2 rounded-lg transition-colors border border-white/10">
                                        Crear la primera
                                    </Link>
                                </div>
                            ) : (
                                <table className="w-full text-left border-collapse">
                                    <thead>
                                        <tr className="border-b border-white/5 text-xs text-zinc-500 font-medium uppercase tracking-wider bg-black/20">
                                            <th className="py-3 pl-6">Contacto</th>
                                            <th className="py-3 text-center">Estado</th>
                                            <th className="py-3 text-right">Fecha</th>
                                            <th className="py-3 text-right pr-6">Monto</th>
                                        </tr>
                                    </thead>
                                    <tbody className="text-sm divide-y divide-white/5">
                                        {invoices.map((inv) => (
                                            <tr key={inv.id} className="hover:bg-white/[0.02] transition-colors group">
                                                <td className="py-4 pl-6">
                                                    <div className="font-medium text-white">{inv.client?.name || 'Varios'}</div>
                                                    <div className="text-xs text-zinc-500">{inv.invoice_number || 'Borrador'}</div>
                                                </td>
                                                <td className="py-4 text-center">
                                                    <InvBadge status={inv.status} />
                                                </td>
                                                <td className="py-4 text-right text-zinc-400 text-xs">
                                                    {inv.date ? new Date(inv.date).toLocaleDateString('es-ES') : '-'}
                                                </td>
                                                <td className="py-4 pr-6 text-right font-semibold text-white">
                                                    {Number(inv.amount_total).toLocaleString('es-ES', { minimumFractionDigits: 2 })}€
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            )}
                        </div>
                    </div>
                </div>

                {/* Columna Derecha Estrecha: Panel Operativo de Automatización */}
                <div className="space-y-6">

                    {/* Actividad IA — primera porque es lo más importante */}
                    <div className="bg-[#111113] border border-indigo-500/30 rounded-2xl overflow-hidden shadow-lg shadow-indigo-500/10">
                        <div className="px-5 py-4 border-b border-indigo-500/15 bg-gradient-to-r from-indigo-500/15 to-transparent flex items-center justify-between">
                            <h2 className="text-sm font-semibold text-indigo-300 flex items-center gap-2">
                                <Sparkles className="w-4 h-4 text-indigo-400" /> Actividad IA
                            </h2>
                            <Link href="/tareas" className="text-[11px] text-indigo-400 hover:text-indigo-300 font-medium transition-colors flex items-center gap-1">
                                Ver todo <ArrowRight className="w-3 h-3" />
                            </Link>
                        </div>
                        <div className="divide-y divide-[#27272a] max-h-[280px] overflow-y-auto">
                            {loading ? (
                                <div className="p-6 text-center text-indigo-500/50 text-xs">Cargando actividad...</div>
                            ) : tasks.length === 0 ? (
                                <div className="p-8 text-center flex flex-col items-center gap-2">
                                    <BrainCircuit className="w-8 h-8 text-zinc-700" />
                                    <p className="text-xs text-zinc-500">Sin actividad reciente.<br />Usa el asistente para empezar.</p>
                                </div>
                            ) : (
                                tasks.map(task => (
                                    <div key={task.id} className="p-4 flex flex-col gap-2 hover:bg-indigo-500/5 transition-colors">
                                        <div className="flex items-start justify-between gap-3">
                                            <p className="text-xs text-zinc-200 line-clamp-2 leading-relaxed">
                                                {task.user_intent}
                                            </p>
                                            <StatusBadge status={task.status} />
                                        </div>
                                        <div className="flex items-center gap-2 text-[10px] text-zinc-600 font-mono">
                                            <Clock className="w-3 h-3" />
                                            {new Date(task.created_at).toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" })}
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>

                    {/* Aprobaciones Pendientes */}
                    <div className="bg-[#111113] border border-amber-500/20 rounded-2xl overflow-hidden shadow-lg shadow-amber-500/5">
                        <div className="px-5 py-4 border-b border-amber-500/10 bg-gradient-to-r from-amber-500/10 to-transparent flex items-center gap-2">
                            <Zap className="w-4 h-4 text-amber-500" />
                            <h2 className="text-sm font-semibold text-amber-500">Aprobaciones Requeridas</h2>
                            {approvals.length > 0 && (
                                <span className="ml-auto bg-amber-500 text-black text-[10px] font-bold px-2 py-0.5 rounded-full">
                                    {approvals.length}
                                </span>
                            )}
                        </div>
                        <div className="divide-y divide-[#27272a] max-h-[250px] overflow-y-auto">
                            {loading ? (
                                <div className="p-6 text-center text-zinc-500 text-xs text-amber-500/50">Buscando...</div>
                            ) : approvals.length === 0 ? (
                                <div className="p-8 text-center text-zinc-500 text-xs flex flex-col items-center gap-2">
                                    <CheckCircle2 className="w-8 h-8 text-zinc-700" />
                                    Todo al día. No hay cuellos de botella.
                                </div>
                            ) : (
                                approvals.map(a => (
                                    <div key={a.id} className="p-4 hover:bg-amber-500/5 transition-colors group cursor-default">
                                        <p className="text-sm text-zinc-200 line-clamp-2 leading-snug">{a.action_description}</p>
                                        <div className="flex items-center justify-between mt-3">
                                            <span className="text-[10px] uppercase font-bold text-amber-600 tracking-wider">
                                                Nivel: {a.risk_level}
                                            </span>
                                            <Link href="/aprobaciones" className="text-xs text-amber-500 hover:text-amber-400 font-medium opacity-0 group-hover:opacity-100 transition-opacity">
                                                Revisar &rarr;
                                            </Link>
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>

                    {/* Widget Correo + Almacenamiento */}
                    <div className="bg-[#111113] border border-[#27272a] rounded-2xl overflow-hidden">
                        {/* Header + Tabs */}
                        <div className="px-5 py-4 border-b border-[#27272a] bg-zinc-900/30">
                            <div className="flex items-center justify-between">
                                <h2 className="text-sm font-semibold text-white flex items-center gap-2">
                                    <Mail className="w-4 h-4 text-indigo-400" /> Correo y Archivos
                                </h2>
                                <div className="flex items-center gap-2">
                                    {gmailConnected && <span className="text-[10px] text-emerald-400 font-medium flex items-center gap-0.5"><CheckCircle2 className="w-2.5 h-2.5" />Gmail</span>}
                                    {outlookConnected && <span className="text-[10px] text-emerald-400 font-medium flex items-center gap-0.5"><CheckCircle2 className="w-2.5 h-2.5" />Outlook</span>}
                                    {gdriveConnected && <span className="text-[10px] text-emerald-400 font-medium flex items-center gap-0.5"><CheckCircle2 className="w-2.5 h-2.5" />Drive</span>}
                                    {onedriveConnected && <span className="text-[10px] text-emerald-400 font-medium flex items-center gap-0.5"><CheckCircle2 className="w-2.5 h-2.5" />OneDrive</span>}
                                </div>
                            </div>
                            {(gmailConnected || outlookConnected || gdriveConnected || onedriveConnected) && (
                                <div className="flex gap-1 mt-3">
                                    {gmailConnected && (
                                        <button onClick={() => setActiveTab("gmail")} className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${activeTab === "gmail" ? "bg-white/10 text-white" : "text-zinc-500 hover:text-zinc-300"}`}>
                                            <Mail className="w-3 h-3" /> Gmail
                                        </button>
                                    )}
                                    {outlookConnected && (
                                        <button onClick={() => setActiveTab("outlook")} className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${activeTab === "outlook" ? "bg-white/10 text-white" : "text-zinc-500 hover:text-zinc-300"}`}>
                                            <Mail className="w-3 h-3" /> Outlook
                                        </button>
                                    )}
                                    {gdriveConnected && (
                                        <button onClick={() => setActiveTab("drive")} className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${activeTab === "drive" ? "bg-white/10 text-white" : "text-zinc-500 hover:text-zinc-300"}`}>
                                            <HardDrive className="w-3 h-3" /> Drive
                                        </button>
                                    )}
                                    {onedriveConnected && (
                                        <button onClick={() => setActiveTab("onedrive")} className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${activeTab === "onedrive" ? "bg-white/10 text-white" : "text-zinc-500 hover:text-zinc-300"}`}>
                                            <HardDrive className="w-3 h-3" /> OneDrive
                                        </button>
                                    )}
                                </div>
                            )}
                        </div>

                        {/* Content */}
                        {!gmailConnected && !outlookConnected && !gdriveConnected && !onedriveConnected ? (
                            <div className="p-8 text-center flex flex-col items-center gap-2">
                                <XCircle className="w-8 h-8 text-zinc-700" />
                                <p className="text-xs text-zinc-500">No hay servicios conectados</p>
                                <Link href="/integraciones" className="mt-2 text-xs text-indigo-400 hover:text-indigo-300 transition-colors">
                                    Conectar en Integraciones &rarr;
                                </Link>
                            </div>
                        ) : (activeTab === "gmail" || activeTab === "outlook") ? (
                            <div className="divide-y divide-[#27272a] max-h-[300px] overflow-y-auto">
                                {(() => {
                                    const messages = activeTab === "gmail"
                                        ? gmailMessages.map(m => ({ id: m.id, from: m.from.replace(/<.*>/, "").trim(), subject: m.subject, snippet: m.snippet, date: m.date }))
                                        : outlookMessages.map(m => ({ id: m.id, from: m.from_name || m.from, subject: m.subject, snippet: m.snippet, date: m.date }));
                                    if (messages.length === 0) return <div className="p-6 text-center text-zinc-500 text-xs">Sin correos recientes</div>;
                                    return messages.map(msg => (
                                        <div key={msg.id} className="p-4 hover:bg-white/[0.02] transition-colors">
                                            <div className="flex items-start justify-between gap-2">
                                                <p className="text-xs font-medium text-zinc-200 truncate max-w-[180px]">{msg.from}</p>
                                                <span className="text-[10px] text-zinc-600 whitespace-nowrap">
                                                    {msg.date ? new Date(msg.date).toLocaleDateString("es-ES", { day: "2-digit", month: "short" }) : ""}
                                                </span>
                                            </div>
                                            <p className="text-xs text-zinc-400 font-medium mt-1 truncate">{msg.subject}</p>
                                            <p className="text-[11px] text-zinc-600 mt-0.5 line-clamp-1">{msg.snippet}</p>
                                        </div>
                                    ));
                                })()}
                            </div>
                        ) : (activeTab === "drive" || activeTab === "onedrive") ? (
                            <div className="divide-y divide-[#27272a] max-h-[300px] overflow-y-auto">
                                {(() => {
                                    const files = activeTab === "drive"
                                        ? driveFiles.map(f => ({ id: f.id, name: f.name, mime: f.mimeType || "", date: f.modifiedTime }))
                                        : onedriveFiles.map(f => ({ id: f.id, name: f.name, mime: f.mimeType || "", date: f.lastModifiedDateTime || "" }));
                                    if (files.length === 0) return <div className="p-6 text-center text-zinc-500 text-xs">Sin archivos recientes</div>;
                                    return files.map(file => {
                                        const icon = file.mime.includes("spreadsheet") ? <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-400" />
                                            : file.mime.includes("image") ? <FileImage className="w-3.5 h-3.5 text-purple-400" />
                                            : file.mime.includes("folder") ? <FolderOpen className="w-3.5 h-3.5 text-yellow-400" />
                                            : file.mime.includes("document") ? <FileText className="w-3.5 h-3.5 text-blue-400" />
                                            : file.mime.includes("pdf") ? <FileText className="w-3.5 h-3.5 text-red-400" />
                                            : <FileIcon className="w-3.5 h-3.5 text-zinc-400" />;
                                        return (
                                            <div key={file.id} className="p-4 hover:bg-white/[0.02] transition-colors flex items-center gap-3">
                                                {icon}
                                                <div className="flex-1 min-w-0">
                                                    <p className="text-xs text-zinc-200 truncate">{file.name}</p>
                                                    <p className="text-[10px] text-zinc-600 mt-0.5">
                                                        {file.date ? new Date(file.date).toLocaleDateString("es-ES", { day: "2-digit", month: "short", year: "numeric" }) : ""}
                                                    </p>
                                                </div>
                                            </div>
                                        );
                                    });
                                })()}
                            </div>
                        ) : null}

                        {/* Footer */}
                        {(gmailConnected || outlookConnected || gdriveConnected || onedriveConnected) && (
                            <div className="p-3 border-t border-[#27272a] bg-black/20 text-center">
                                <Link href="/integraciones" className="text-[11px] font-medium text-zinc-400 hover:text-white transition-colors">
                                    Gestionar integraciones
                                </Link>
                            </div>
                        )}
                    </div>

                </div>
            </div>
        </div>
    );
}
