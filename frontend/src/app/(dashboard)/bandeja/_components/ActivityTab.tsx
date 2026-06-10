"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { api } from "@/lib/api";
import type { AIEmployee, ActivityEntry } from "@/lib/api/ai_employees";
import { RefreshCw, ChevronDown, Bot } from "lucide-react";
import { InboxMessage, CATEGORY_CONFIG } from "./InboxMessage";
import { useNotificationSocket } from "@/lib/hooks/useNotificationSocket";
import { usePolling } from "@/lib/hooks/usePolling";

interface ActivityTabProps {
    isActive?: boolean;
}

export function ActivityTab({ isActive = true }: ActivityTabProps) {
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
    }, [fetchEntries]);

    // Respaldo del socket `activity_new` (cubre eventos perdidos por desconexión).
    usePolling(() => { void fetchEntries(true); }, 60_000, { enabled: isActive });

    useNotificationSocket({
        activity_new: (msg) => {
            const entry = msg.entry as ActivityEntry | undefined;
            if (!entry) return;
            // Only prepend if it matches current filters
            if (filterEmp && entry.employee_id !== filterEmp) return;
            if (filterCat && entry.category !== filterCat) return;
            setEntries(prev => [entry, ...prev]);
            offsetRef.current += 1;
        },
    });

    const empMap = Object.fromEntries(employees.map(e => [e.id, e]));

    return (
        <div className="space-y-4">
            {/* Filters + refresh */}
            <div className="flex items-center gap-2 flex-wrap">
                <select value={filterEmp} onChange={e => setFilterEmp(e.target.value)}
                    className="bg-card border border-border rounded-lg px-3 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-violet-500/50">
                    <option value="">Todos los agentes</option>
                    {employees.map(e => <option key={e.id} value={e.id}>{e.name}</option>)}
                </select>
                <select value={filterCat} onChange={e => setFilterCat(e.target.value)}
                    className="bg-card border border-border rounded-lg px-3 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-violet-500/50">
                    <option value="">Todas las categorías</option>
                    {Object.entries(CATEGORY_CONFIG).map(([v, c]) => (
                        <option key={v} value={v}>{c.icon} {c.label}</option>
                    ))}
                </select>
                {(filterEmp || filterCat) && (
                    <button onClick={() => { setFilterEmp(""); setFilterCat(""); }}
                        className="text-xs text-muted-foreground hover:text-foreground px-3 py-1.5 border border-border rounded-lg hover:bg-muted">
                        Limpiar
                    </button>
                )}
                <div className="flex-1" />
                <button onClick={() => { setRefreshing(true); fetchEntries(true).finally(() => setRefreshing(false)); }}
                    className="p-2 rounded-lg border border-border hover:bg-muted text-muted-foreground transition-colors">
                    <RefreshCw className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`} />
                </button>
            </div>

            {/* Messages */}
            {loading ? (
                <div className="flex justify-center py-16">
                    <div className="w-7 h-7 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" />
                </div>
            ) : entries.length === 0 ? (
                <div className="text-center py-20 border-2 border-dashed border-border rounded-xl">
                    <Bot className="w-10 h-10 text-muted-foreground/60 mx-auto mb-3" />
                    <p className="text-muted-foreground font-medium text-sm">Bandeja vacía</p>
                    <p className="text-xs text-muted-foreground/60 mt-1">
                        Cuando tus agentes completen tareas o necesiten tu atención, aparecerán aquí
                    </p>
                </div>
            ) : (
                <div className="bg-card border border-border rounded-xl px-4">
                    {entries.map(entry => (
                        <InboxMessage key={entry.id} entry={entry} employee={empMap[entry.employee_id ?? ""]} />
                    ))}
                    {hasMore && (
                        <div className="py-4 flex justify-center">
                            <button onClick={async () => { setLoadingMore(true); await fetchEntries(false); setLoadingMore(false); }}
                                disabled={loadingMore}
                                className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground transition-colors">
                                {loadingMore
                                    ? <div className="w-4 h-4 border-2 border-border border-t-transparent rounded-full animate-spin" />
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
