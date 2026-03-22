"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import {
    RefreshCw, CheckCircle2, AlertCircle, Download,
    Server, Database, Cpu, Loader2, Shield,
} from "lucide-react";

interface HealthData {
    status: string;
    version: string;
    checks: Record<string, any>;
}

export default function ActualizacionesPage() {
    const [health, setHealth] = useState<HealthData | null>(null);
    const [loading, setLoading] = useState(true);
    const [checking, setChecking] = useState(false);
    const [updateResult, setUpdateResult] = useState<{
        update_available: boolean;
        latest_version?: string;
        changelog?: string;
    } | null>(null);
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

    async function checkForUpdates() {
        setChecking(true);
        setUpdateResult(null);
        setError("");
        try {
            const result = await api.system.checkUpdate();
            setUpdateResult(result);
        } catch {
            setUpdateResult({
                update_available: false,
            });
        } finally {
            setChecking(false);
        }
    }

    useEffect(() => {
        loadHealth();
    }, []);

    const checks = health?.checks || {};

    return (
        <div className="p-8 max-w-3xl mx-auto space-y-8">
            {/* Header */}
            <div>
                <h1 className="text-2xl font-bold text-white">Actualizaciones</h1>
                <p className="text-sm text-zinc-500 mt-1">
                    Estado del sistema y actualizaciones disponibles
                </p>
            </div>

            {error && (
                <div className="flex items-center gap-2 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-300 text-sm">
                    <AlertCircle className="w-4 h-4 flex-shrink-0" />
                    {error}
                </div>
            )}

            {/* Version actual */}
            <div className="bg-[#111113] border border-[#27272a] rounded-2xl p-6">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <div className="w-12 h-12 rounded-xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center">
                            <Shield className="w-6 h-6 text-indigo-400" />
                        </div>
                        <div>
                            <h2 className="text-lg font-semibold text-white">AutomatizaPyme</h2>
                            <p className="text-sm text-zinc-500">
                                {loading ? "Cargando..." : `Version ${health?.version || "desconocida"}`}
                            </p>
                        </div>
                    </div>
                    <button
                        onClick={checkForUpdates}
                        disabled={checking}
                        className="flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-medium transition"
                    >
                        {checking ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                            <RefreshCw className="w-4 h-4" />
                        )}
                        {checking ? "Comprobando..." : "Buscar actualizaciones"}
                    </button>
                </div>

                {/* Resultado de busqueda */}
                {updateResult && (
                    <div className={`mt-4 flex items-center gap-3 px-4 py-3 rounded-xl border ${
                        updateResult.update_available
                            ? "bg-amber-500/10 border-amber-500/20 text-amber-300"
                            : "bg-emerald-500/10 border-emerald-500/20 text-emerald-300"
                    }`}>
                        {updateResult.update_available ? (
                            <>
                                <Download className="w-4 h-4 flex-shrink-0" />
                                <div className="flex-1">
                                    <p className="text-sm font-medium">
                                        Nueva version disponible: {updateResult.latest_version}
                                    </p>
                                    {updateResult.changelog && (
                                        <p className="text-xs mt-1 opacity-80">{updateResult.changelog}</p>
                                    )}
                                </div>
                            </>
                        ) : (
                            <>
                                <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                                <p className="text-sm">Estas usando la version mas reciente</p>
                            </>
                        )}
                    </div>
                )}
            </div>

            {/* Estado del sistema */}
            <div className="bg-[#111113] border border-[#27272a] rounded-2xl overflow-hidden">
                <div className="px-6 py-4 border-b border-[#27272a] flex items-center justify-between">
                    <h2 className="text-sm font-semibold text-white flex items-center gap-2">
                        <Server className="w-4 h-4 text-zinc-400" />
                        Estado del sistema
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
                    {/* Servidor */}
                    <StatusRow
                        icon={<Server className="w-4 h-4" />}
                        label="Servidor API"
                        status={health ? "ok" : loading ? "loading" : "error"}
                        detail={health ? `Respondiendo correctamente` : "Sin conexion"}
                    />

                    {/* PostgreSQL */}
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

                    {/* Task Runner */}
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

            {/* Info de desarrollo */}
            <div className="text-xs text-zinc-600 text-center space-y-1">
                <p>Para aplicar actualizaciones de desarrollo:</p>
                <code className="block bg-zinc-900 text-zinc-400 px-3 py-2 rounded-lg font-mono">
                    cd desktop &amp;&amp; npm run sync
                </code>
                <p className="mt-2">Luego reinicia la aplicacion desde la bandeja del sistema.</p>
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
