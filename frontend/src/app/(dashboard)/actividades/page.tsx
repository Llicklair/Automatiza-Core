"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { api } from "@/lib/api";
import type { AIEmployee, ActivityEntry } from "@/lib/api/ai_employees";
import { Inbox, RefreshCw, ChevronDown, CheckCheck, Bot } from "lucide-react";

const CATEGORY_CONFIG: Record<string, { icon: string; color: string; label: string }> = {
    billing:    { icon: "💰", color: "bg-amber-500/10 border-amber-500/20 text-amber-400",   label: "Facturación" },
    hr:         { icon: "👥", color: "bg-blue-500/10 border-blue-500/20 text-blue-400",       label: "RRHH" },
    crm:        { icon: "🤝", color: "bg-violet-500/10 border-violet-500/20 text-violet-400", label: "CRM" },
    email:      { icon: "📧", color: "bg-sky-500/10 border-sky-500/20 text-sky-400",          label: "Email" },
    banking:    { icon: "🏦", color: "bg-emerald-500/10 border-emerald-500/20 text-emerald-400", label: "Banca" },
    compliance: { icon: "⚖️", color: "bg-orange-500/10 border-orange-500/20 text-orange-400", label: "Compliance" },
    documents:  { icon: "📄", color: "bg-zinc-500/10 border-zinc-500/20 text-zinc-400",       label: "Documentos" },
    system:     { icon: "⚙️", color: "bg-zinc-500/10 border-zinc-500/20 text-zinc-500",       label: "Sistema" },
};

function timeAgo(dateStr: string): string {
    const diff = Date.now() - new Date(dateStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return "ahora";
    if (mins < 60) return `hace ${mins}m`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `hace ${hrs}h`;
    return new Date(dateStr).toLocaleDateString("es-ES", { day: "numeric", month: "short" });
}

function InboxMessage({ entry, employee }: { entry: ActivityEntry; employee?: AIEmployee }) {
    const cat = CATEGORY_CONFIG[entry.category] ?? CATEGORY_CONFIG.system;

    return (
        <div className="flex gap-3 py-4 px-1 border-b border-[#27272a] last:border-0 hover:bg-zinc-900/50 rounded-lg transition-colors -mx-1 px-2">
            {/* Avatar agente */}
            <div className="w-9 h-9 rounded-full bg-violet-500/10 border border-violet-500/20 flex items-center justify-center text-base shrink-0 mt-0.5">
                {entry.icon || cat.icon}
            </div>

            <div className="flex-1 min-w-0 space-y-1">
                {/* Cabecera */}
                <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 min-w-0">
                        <span className="text-sm font-medium text-white truncate">
                            {employee?.name ?? "Agente IA"}
                        </span>
                        <span className={`shrink-0 text-[10px] px-1.5 py-0.5 rounded border font-medium ${cat.color}`}>
                            {cat.label}
                        </span>
                    </div>
                    <span className="text-[10px] text-zinc-600 shrink-0">{timeAgo(entry.created_at)}</span>
                </div>

                {/* Mensaje */}
                <p className="text-sm text-zinc-300 leading-relaxed">{entry.message}</p>

                {/* Metadata si existe */}
                {entry.metadata && Object.keys(entry.metadata).length > 0 && (
                    <div className="flex flex-wrap gap-2 pt-1">
                        {Object.entries(entry.metadata).slice(0, 4).map(([k, v]) => (
                            <span key={k} className="text-[10px] text-zinc-600">
                                <span className="text-zinc-500">{k.replace(/_/g, " ")}:</span>{" "}
                                <span className="text-zinc-400">{String(v).slice(0, 50)}</span>
                            </span>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}

export default function BandejaAgentesPage() {
    const [entries, setEntries]           = useState<ActivityEntry[]>([]);
    const [employees, setEmployees]       = useState<AIEmployee[]>([]);
    const [loading, setLoading]           = useState(true);
    const [loadingMore, setLoadingMore]   = useState(false);
    const [refreshing, setRefreshing]     = useState(false);
    const [hasMore, setHasMore]           = useState(true);
    const [filterEmp, setFilterEmp]       = useState("");
    const [filterCat, setFilterCat]       = useState("");
    const offsetRef = useRef(0);
    const LIMIT = 50;

    const fetchEntries = useCallback(async (reset = false) => {
        const offset = reset ? 0 : offsetRef.current;
        const data = await api.aiEmployees.activityFeed({
            employee_id: filterEmp || undefined,
            category: filterCat || undefined,
            limit: LIMIT, offset,
        });
        if (reset) { setEntries(data); offsetRef.current = data.length; }
        else { setEntries(prev => [...prev, ...data]); offsetRef.current += data.length; }
        setHasMore(data.length === LIMIT);
    }, [filterEmp, filterCat]);

    useEffect(() => {
        setLoading(true);
        Promise.all([
            fetchEntries(true),
            api.aiEmployees.list().then(setEmployees).catch(() => {}),
        ]).finally(() => setLoading(false));
        const interval = setInterval(() => fetchEntries(true), 15_000);
        return () => clearInterval(interval);
    }, [fetchEntries]);

    const empMap = Object.fromEntries(employees.map(e => [e.id, e]));
    const unread = entries.length;

    return (
        <div className="max-w-3xl mx-auto px-4 py-8 space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-xl font-semibold text-white flex items-center gap-2">
                        <Inbox className="w-6 h-6 text-violet-400" />
                        Bandeja de Agentes
                        {unread > 0 && (
                            <span className="text-xs font-medium bg-violet-600 text-white px-2 py-0.5 rounded-full">{unread}</span>
                        )}
                    </h1>
                    <p className="text-xs text-zinc-500 mt-1">Mensajes e informes de tus agentes IA</p>
                </div>
                <button onClick={() => { setRefreshing(true); fetchEntries(true).finally(() => setRefreshing(false)); }}
                    className="p-2 rounded-lg border border-[#27272a] hover:bg-zinc-800 text-zinc-500 transition-colors">
                    <RefreshCw className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`} />
                </button>
            </div>

            {/* Filtros */}
            <div className="flex gap-2 flex-wrap">
                <select value={filterEmp} onChange={e => setFilterEmp(e.target.value)}
                    className="bg-[#18181b] border border-[#27272a] rounded-lg px-3 py-1.5 text-xs text-zinc-300 focus:outline-none focus:ring-1 focus:ring-violet-500/50">
                    <option value="">Todos los agentes</option>
                    {employees.map(e => <option key={e.id} value={e.id}>{e.name}</option>)}
                </select>
                <select value={filterCat} onChange={e => setFilterCat(e.target.value)}
                    className="bg-[#18181b] border border-[#27272a] rounded-lg px-3 py-1.5 text-xs text-zinc-300 focus:outline-none focus:ring-1 focus:ring-violet-500/50">
                    <option value="">Todas las categorías</option>
                    {Object.entries(CATEGORY_CONFIG).map(([v, c]) => (
                        <option key={v} value={v}>{c.icon} {c.label}</option>
                    ))}
                </select>
                {(filterEmp || filterCat) && (
                    <button onClick={() => { setFilterEmp(""); setFilterCat(""); }}
                        className="text-xs text-zinc-500 hover:text-zinc-300 px-3 py-1.5 border border-[#27272a] rounded-lg hover:bg-zinc-800">
                        Limpiar
                    </button>
                )}
            </div>

            {/* Mensajes */}
            {loading ? (
                <div className="flex justify-center py-16">
                    <div className="w-7 h-7 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" />
                </div>
            ) : entries.length === 0 ? (
                <div className="text-center py-20 border-2 border-dashed border-[#27272a] rounded-xl">
                    <Bot className="w-10 h-10 text-zinc-700 mx-auto mb-3" />
                    <p className="text-zinc-500 font-medium text-sm">Bandeja vacía</p>
                    <p className="text-xs text-zinc-600 mt-1">
                        Cuando tus agentes completen tareas o necesiten tu atención, aparecerán aquí
                    </p>
                </div>
            ) : (
                <div className="bg-[#18181b] border border-[#27272a] rounded-xl px-4">
                    {entries.map(entry => (
                        <InboxMessage key={entry.id} entry={entry} employee={empMap[entry.employee_id ?? ""]} />
                    ))}
                    {hasMore && (
                        <div className="py-4 flex justify-center">
                            <button onClick={async () => { setLoadingMore(true); await fetchEntries(false); setLoadingMore(false); }}
                                disabled={loadingMore}
                                className="flex items-center gap-2 text-xs text-zinc-500 hover:text-zinc-300 transition-colors">
                                {loadingMore
                                    ? <div className="w-4 h-4 border-2 border-zinc-600 border-t-transparent rounded-full animate-spin" />
                                    : <ChevronDown className="w-4 h-4" />}
                                Cargar más
                            </button>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
