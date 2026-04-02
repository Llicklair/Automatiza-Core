"use client";

import { useEffect, useState, useCallback } from "react";
import { api, AIEmployee, ActivityEntry } from "@/lib/api";
import { Bot, Zap, Moon, AlertCircle, RefreshCw, Plus, Users2 } from "lucide-react";

const STATUS_CONFIG = {
    idle:    { label: "Disponible",  color: "bg-emerald-100 text-emerald-700", dot: "bg-emerald-400" },
    working: { label: "Trabajando",  color: "bg-blue-100 text-blue-700",       dot: "bg-blue-400 animate-pulse" },
    paused:  { label: "Pausado",     color: "bg-gray-100 text-gray-500",        dot: "bg-gray-400" },
    blocked: { label: "Requiere firma", color: "bg-amber-100 text-amber-700",   dot: "bg-amber-400 animate-pulse" },
} as const;

const DOMAIN_ICON: Record<string, string> = {
    billing:    "💰",
    hr:         "👥",
    email:      "📧",
    crm:        "🤝",
    banking:    "🏦",
    compliance: "⚖️",
    excel:      "📊",
    documents:  "📄",
};

function EmployeeCard({
    employee,
    onToggle,
}: {
    employee: AIEmployee;
    onToggle: (id: string, current: AIEmployee["status"]) => void;
}) {
    const s = STATUS_CONFIG[employee.status] ?? STATUS_CONFIG.idle;
    const icon = DOMAIN_ICON[employee.domain] ?? "🤖";

    return (
        <div className="bg-white rounded-xl border border-gray-200 p-5 flex flex-col gap-4 shadow-sm hover:shadow-md transition-shadow">
            <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                    <div className="w-11 h-11 rounded-full bg-indigo-50 flex items-center justify-center text-xl">
                        {icon}
                    </div>
                    <div>
                        <p className="font-semibold text-gray-900 text-sm">{employee.name}</p>
                        <p className="text-xs text-gray-500">{employee.role}</p>
                    </div>
                </div>
                <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${s.color}`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${s.dot}`} />
                    {s.label}
                </span>
            </div>

            <div className="flex items-center justify-between pt-1 border-t border-gray-100">
                <span className="text-xs text-gray-400 capitalize">{employee.domain}</span>
                {!employee.is_builtin ? null : (
                    <span className="text-xs text-indigo-500 font-medium">Built-in</span>
                )}
                <button
                    onClick={() => onToggle(employee.id, employee.status)}
                    className={`text-xs px-2.5 py-1 rounded-lg border transition-colors ${
                        employee.status === "paused"
                            ? "border-emerald-300 text-emerald-600 hover:bg-emerald-50"
                            : "border-gray-200 text-gray-500 hover:bg-gray-50"
                    }`}
                >
                    {employee.status === "paused" ? "Activar" : "Pausar"}
                </button>
            </div>
        </div>
    );
}

function ActivityFeedItem({ entry }: { entry: ActivityEntry }) {
    const date = new Date(entry.created_at);
    const time = date.toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" });
    const day  = date.toLocaleDateString("es-ES", { day: "numeric", month: "short" });

    return (
        <div className="flex gap-3 py-3 border-b border-gray-100 last:border-0">
            <span className="text-xl mt-0.5 shrink-0">{entry.icon}</span>
            <div className="flex-1 min-w-0">
                <p className="text-sm text-gray-800 leading-snug">{entry.message}</p>
                <p className="text-xs text-gray-400 mt-1">{day} · {time}</p>
            </div>
        </div>
    );
}

export default function MiEquipoPage() {
    const [employees, setEmployees]   = useState<AIEmployee[]>([]);
    const [feed, setFeed]             = useState<ActivityEntry[]>([]);
    const [loading, setLoading]       = useState(true);
    const [seeding, setSeeding]       = useState(false);
    const [error, setError]           = useState<string | null>(null);
    const [refreshing, setRefreshing] = useState(false);

    const loadData = useCallback(async () => {
        try {
            const [emps, entries] = await Promise.all([
                api.aiEmployees.list(),
                api.aiEmployees.activityFeed({ limit: 30 }),
            ]);
            setEmployees(emps);
            setFeed(entries);
            setError(null);
        } catch (e: any) {
            setError(e?.message ?? "Error cargando datos");
        }
    }, []);

    useEffect(() => {
        setLoading(true);
        loadData().finally(() => setLoading(false));

        // Refresco automático cada 15s para estados en tiempo real
        const interval = setInterval(loadData, 15_000);
        return () => clearInterval(interval);
    }, [loadData]);

    const handleSeed = async () => {
        setSeeding(true);
        try {
            await api.aiEmployees.seed();
            await loadData();
        } finally {
            setSeeding(false);
        }
    };

    const handleToggle = async (id: string, current: AIEmployee["status"]) => {
        const next = current === "paused" ? "idle" : "paused";
        setEmployees(prev => prev.map(e => e.id === id ? { ...e, status: next } : e));
        try {
            await api.aiEmployees.updateStatus(id, next);
        } catch {
            // Revert on error
            setEmployees(prev => prev.map(e => e.id === id ? { ...e, status: current } : e));
        }
    };

    const handleRefresh = async () => {
        setRefreshing(true);
        await loadData();
        setRefreshing(false);
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
            </div>
        );
    }

    return (
        <div className="max-w-6xl mx-auto px-4 py-8 space-y-8">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                        <Bot className="w-7 h-7 text-indigo-500" />
                        Mi Equipo IA
                    </h1>
                    <p className="text-sm text-gray-500 mt-1">
                        Empleados virtuales que trabajan en segundo plano para ti
                    </p>
                </div>
                <div className="flex gap-2">
                    <button
                        onClick={handleRefresh}
                        disabled={refreshing}
                        className="p-2 rounded-lg border border-gray-200 hover:bg-gray-50 text-gray-500 transition-colors"
                        title="Refrescar"
                    >
                        <RefreshCw className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`} />
                    </button>
                    {employees.length === 0 && (
                        <button
                            onClick={handleSeed}
                            disabled={seeding}
                            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors disabled:opacity-60"
                        >
                            <Plus className="w-4 h-4" />
                            {seeding ? "Creando equipo..." : "Crear equipo inicial"}
                        </button>
                    )}
                </div>
            </div>

            {error && (
                <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
                    <AlertCircle className="w-4 h-4 shrink-0" />
                    {error}
                </div>
            )}

            {/* Organigrama */}
            {employees.length === 0 ? (
                <div className="text-center py-16 border-2 border-dashed border-gray-200 rounded-xl">
                    <Users2 className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                    <p className="text-gray-500 font-medium">Sin empleados aún</p>
                    <p className="text-sm text-gray-400 mt-1">Crea el equipo inicial con Ana, Carlos y Sofía</p>
                    <button
                        onClick={handleSeed}
                        disabled={seeding}
                        className="mt-4 px-5 py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors disabled:opacity-60"
                    >
                        {seeding ? "Creando..." : "Crear equipo inicial"}
                    </button>
                </div>
            ) : (
                <div>
                    <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">
                        Organigrama · {employees.length} empleados
                    </h2>
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                        {employees.map(emp => (
                            <EmployeeCard key={emp.id} employee={emp} onToggle={handleToggle} />
                        ))}
                    </div>
                </div>
            )}

            {/* Activity Feed */}
            <div>
                <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">
                    Actividad reciente
                </h2>
                {feed.length === 0 ? (
                    <div className="text-center py-10 bg-gray-50 rounded-xl border border-gray-100">
                        <p className="text-gray-400 text-sm">
                            Aún no hay actividad. Los empleados empezarán a trabajar en breve.
                        </p>
                    </div>
                ) : (
                    <div className="bg-white rounded-xl border border-gray-200 px-5 divide-y divide-gray-100 shadow-sm">
                        {feed.map(entry => (
                            <ActivityFeedItem key={entry.id} entry={entry} />
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
