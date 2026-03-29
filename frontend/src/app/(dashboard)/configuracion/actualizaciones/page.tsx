"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import {
    RefreshCw, CheckCircle2, AlertCircle,
    Server, Database, Cpu, Loader2, Terminal,
} from "lucide-react";

interface HealthData {
    status: string;
    version: string;
    checks: Record<string, any>;
}

export default function ActualizacionesPage() {
    const [health, setHealth] = useState<HealthData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    async function loadHealth() {
        setLoading(true);
        setError("");
        try {
            const data = await api.system.health();
            setHealth(data);
        } catch (e: any) {
            setError(e.message || "No se pudo conectar al servidor");
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => { loadHealth(); }, []);

    const checks = health?.checks || {};

    return (
        <div className="p-8 max-w-3xl mx-auto space-y-8">
            {/* Header */}
            <div>
                <h1 className="text-2xl font-bold text-white">Sistema</h1>
                <p className="text-sm text-zinc-500 mt-1">
                    Estado de los servicios y guía de actualización
                </p>
            </div>

            {error && (
                <div className="flex items-center gap-2 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-300 text-sm">
                    <AlertCircle className="w-4 h-4 flex-shrink-0" />
                    {error}
                </div>
            )}

            {/* Estado del sistema */}
            <div className="bg-[#111113] border border-[#27272a] rounded-2xl overflow-hidden">
                <div className="px-6 py-4 border-b border-[#27272a] flex items-center justify-between">
                    <h2 className="text-sm font-semibold text-white flex items-center gap-2">
                        <Server className="w-4 h-4 text-zinc-400" />
                        Estado del sistema
                        {health?.version && (
                            <span className="text-xs text-zinc-500 font-normal ml-1">
                                v{health.version}
                            </span>
                        )}
                    </h2>
                    <button
                        onClick={loadHealth}
                        disabled={loading}
                        className="text-xs text-zinc-500 hover:text-zinc-300 transition flex items-center gap-1"
                    >
                        <RefreshCw className={`w-3 h-3 ${loading ? "animate-spin" : ""}`} />
                        Actualizar
                    </button>
                </div>

                <div className="divide-y divide-[#27272a]">
                    <StatusRow
                        icon={<Server className="w-4 h-4" />}
                        label="Servidor API"
                        status={health ? "ok" : loading ? "loading" : "error"}
                        detail={health ? "Respondiendo correctamente" : "Sin conexión"}
                    />
                    <StatusRow
                        icon={<Database className="w-4 h-4" />}
                        label="Base de datos"
                        status={
                            loading ? "loading"
                            : checks.postgres?.status === "up" ? "ok"
                            : "error"
                        }
                        detail={
                            checks.postgres?.status === "up"
                                ? `PostgreSQL — ${checks.postgres.latency_ms?.toFixed(0) || "?"}ms`
                                : checks.postgres?.error || "No disponible"
                        }
                    />
                    <StatusRow
                        icon={<Cpu className="w-4 h-4" />}
                        label="Motor de tareas"
                        status={
                            loading ? "loading"
                            : checks.task_runner?.status === "up" ? "ok"
                            : "warning"
                        }
                        detail={
                            checks.task_runner?.status === "up"
                                ? `${checks.task_runner.active_tasks || 0} tareas activas`
                                : "Inactivo"
                        }
                    />
                </div>
            </div>

            {/* Cómo actualizar */}
            <div className="bg-[#111113] border border-[#27272a] rounded-2xl p-6 space-y-4">
                <h2 className="text-sm font-semibold text-white flex items-center gap-2">
                    <Terminal className="w-4 h-4 text-zinc-400" />
                    Cómo aplicar una actualización
                </h2>
                <p className="text-sm text-zinc-400">
                    AutomatizaPyme se actualiza sincronizando el código fuente con la app instalada.
                    No requiere reinstalar el <code className="text-zinc-300">.exe</code>.
                </p>
                <ol className="space-y-3 text-sm text-zinc-400">
                    <li className="flex gap-3">
                        <span className="w-5 h-5 rounded-full bg-indigo-600/20 border border-indigo-500/30 text-indigo-400 text-xs font-bold flex items-center justify-center flex-shrink-0">1</span>
                        <span>Descarga o actualiza el código fuente del proyecto.</span>
                    </li>
                    <li className="flex gap-3">
                        <span className="w-5 h-5 rounded-full bg-indigo-600/20 border border-indigo-500/30 text-indigo-400 text-xs font-bold flex items-center justify-center flex-shrink-0">2</span>
                        <div>
                            <span>Abre un terminal en la carpeta del proyecto y ejecuta:</span>
                            <code className="block mt-1.5 bg-zinc-900 text-zinc-300 px-3 py-2 rounded-lg font-mono text-xs">
                                cd desktop &amp;&amp; npm run sync
                            </code>
                            <p className="text-xs text-zinc-500 mt-1">
                                Si hay cambios en el frontend, usa <code className="text-zinc-400">npm run sync:rebuild</code> en su lugar.
                            </p>
                        </div>
                    </li>
                    <li className="flex gap-3">
                        <span className="w-5 h-5 rounded-full bg-indigo-600/20 border border-indigo-500/30 text-indigo-400 text-xs font-bold flex items-center justify-center flex-shrink-0">3</span>
                        <span>Reinicia la aplicación desde la bandeja del sistema: clic derecho → <strong className="text-zinc-300">Salir</strong>, luego vuelve a abrirla.</span>
                    </li>
                </ol>
                <div className="flex items-start gap-2 px-3 py-2.5 rounded-lg bg-amber-500/5 border border-amber-500/15 text-amber-300/80 text-xs">
                    <AlertCircle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
                    Si el sync incluye nuevas dependencias Python o migraciones de base de datos, el reinicio las aplicará automáticamente.
                </div>
            </div>
        </div>
    );
}

function StatusRow({ icon, label, status, detail }: {
    icon: React.ReactNode;
    label: string;
    status: "ok" | "error" | "warning" | "loading";
    detail: string;
}) {
    const statusStyles = {
        ok: "text-emerald-400",
        error: "text-red-400",
        warning: "text-amber-400",
        loading: "text-zinc-500",
    };
    const statusIcons = {
        ok: <CheckCircle2 className="w-4 h-4 text-emerald-400" />,
        error: <AlertCircle className="w-4 h-4 text-red-400" />,
        warning: <AlertCircle className="w-4 h-4 text-amber-400" />,
        loading: <Loader2 className="w-4 h-4 text-zinc-500 animate-spin" />,
    };

    return (
        <div className="flex items-center justify-between px-6 py-4">
            <div className="flex items-center gap-3">
                <span className="text-zinc-500">{icon}</span>
                <div>
                    <p className="text-sm text-zinc-200 font-medium">{label}</p>
                    <p className={`text-xs ${statusStyles[status]}`}>{detail}</p>
                </div>
            </div>
            {statusIcons[status]}
        </div>
    );
}
