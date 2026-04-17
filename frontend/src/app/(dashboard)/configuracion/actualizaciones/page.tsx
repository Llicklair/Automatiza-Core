"use client";

import {
    RefreshCw, CheckCircle2, AlertCircle, Download,
    Server, Database, Cpu, Loader2, Terminal,
} from "lucide-react";
import { useActualizaciones } from "./_hooks/useActualizaciones";

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
        loading: "text-muted-foreground",
    };
    const statusIcons = {
        ok: <CheckCircle2 className="w-4 h-4 text-emerald-400" />,
        error: <AlertCircle className="w-4 h-4 text-red-400" />,
        warning: <AlertCircle className="w-4 h-4 text-amber-400" />,
        loading: <Loader2 className="w-4 h-4 text-muted-foreground animate-spin" />,
    };

    return (
        <div className="flex items-center justify-between px-6 py-4">
            <div className="flex items-center gap-3">
                <span className="text-muted-foreground">{icon}</span>
                <div>
                    <p className="text-sm text-foreground font-medium">{label}</p>
                    <p className={`text-xs ${statusStyles[status]}`}>{detail}</p>
                </div>
            </div>
            {statusIcons[status]}
        </div>
    );
}

export default function ActualizacionesPage() {
    const { health, loading, error, updateStatus, updateError, checks, loadHealth, checkForUpdates } = useActualizaciones();

    return (
        <div className="p-8 max-w-3xl mx-auto space-y-8">
            <div>
                <h1 className="text-2xl font-bold text-foreground">Sistema</h1>
                <p className="text-sm text-muted-foreground mt-1">
                    Estado de los servicios y guía de actualización
                </p>
            </div>

            {error && (
                <div className="flex items-center gap-2 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-300 text-sm">
                    <AlertCircle className="w-4 h-4 flex-shrink-0" />
                    {error}
                </div>
            )}

            {/* Buscar actualizaciones */}
            <div className="bg-card border border-border rounded-2xl p-6">
                <div className="flex items-center justify-between">
                    <div>
                        <h2 className="text-sm font-semibold text-foreground flex items-center gap-2">
                            <Download className="w-4 h-4 text-muted-foreground" />
                            Actualizaciones
                        </h2>
                        <p className="text-xs text-muted-foreground mt-1">
                            {health?.version ? `Versión actual: v${health.version}` : "Comprueba si hay una nueva versión disponible."}
                        </p>
                    </div>
                    <button
                        onClick={checkForUpdates}
                        disabled={updateStatus === "checking"}
                        className="flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary disabled:opacity-50 text-foreground text-xs font-medium rounded-lg transition-colors"
                    >
                        {updateStatus === "checking" ? (
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                            <RefreshCw className="w-3.5 h-3.5" />
                        )}
                        Buscar actualizaciones
                    </button>
                </div>

                {updateStatus === "up_to_date" && (
                    <div className="mt-4 flex items-center gap-2 px-4 py-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-sm">
                        <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                        Estás usando la última versión disponible.
                    </div>
                )}
                {updateStatus === "available" && (
                    <div className="mt-4 flex items-center gap-2 px-4 py-3 rounded-xl bg-primary/10 border border-primary/20 text-primary text-sm">
                        <Download className="w-4 h-4 flex-shrink-0" />
                        Hay una nueva versión disponible. La actualización automática se habilitará próximamente.
                    </div>
                )}
                {updateStatus === "error" && (
                    <div className="mt-4 flex items-center gap-2 px-4 py-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-300 text-sm">
                        <AlertCircle className="w-4 h-4 flex-shrink-0" />
                        {updateError}
                    </div>
                )}
            </div>

            {/* Estado del sistema */}
            <div className="bg-card border border-border rounded-2xl overflow-hidden">
                <div className="px-6 py-4 border-b border-border flex items-center justify-between">
                    <h2 className="text-sm font-semibold text-foreground flex items-center gap-2">
                        <Server className="w-4 h-4 text-muted-foreground" />
                        Estado del sistema
                        {health?.version && (
                            <span className="text-xs text-muted-foreground font-normal ml-1">
                                v{health.version}
                            </span>
                        )}
                    </h2>
                    <button
                        onClick={loadHealth}
                        disabled={loading}
                        className="text-xs text-muted-foreground hover:text-foreground transition flex items-center gap-1"
                    >
                        <RefreshCw className={`w-3 h-3 ${loading ? "animate-spin" : ""}`} />
                        Actualizar
                    </button>
                </div>

                <div className="divide-y divide-border">
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
            <div className="bg-card border border-border rounded-2xl p-6 space-y-4">
                <h2 className="text-sm font-semibold text-foreground flex items-center gap-2">
                    <Terminal className="w-4 h-4 text-muted-foreground" />
                    Cómo aplicar una actualización
                </h2>
                <p className="text-sm text-muted-foreground">
                    AutomatizaPyme se actualiza sincronizando el código fuente con la app instalada.
                    No requiere reinstalar el <code className="text-foreground">.exe</code>.
                </p>
                <ol className="space-y-3 text-sm text-muted-foreground">
                    <li className="flex gap-3">
                        <span className="w-5 h-5 rounded-full bg-primary/20 border border-primary/20 text-primary text-xs font-bold flex items-center justify-center flex-shrink-0">1</span>
                        <span>Descarga o actualiza el código fuente del proyecto.</span>
                    </li>
                    <li className="flex gap-3">
                        <span className="w-5 h-5 rounded-full bg-primary/20 border border-primary/20 text-primary text-xs font-bold flex items-center justify-center flex-shrink-0">2</span>
                        <div>
                            <span>Abre un terminal en la carpeta del proyecto y ejecuta:</span>
                            <code className="block mt-1.5 bg-card text-foreground px-3 py-2 rounded-lg font-mono text-xs">
                                cd desktop &amp;&amp; npm run sync
                            </code>
                            <p className="text-xs text-muted-foreground mt-1">
                                Si hay cambios en el frontend, usa <code className="text-muted-foreground">npm run sync:rebuild</code> en su lugar.
                            </p>
                        </div>
                    </li>
                    <li className="flex gap-3">
                        <span className="w-5 h-5 rounded-full bg-primary/20 border border-primary/20 text-primary text-xs font-bold flex items-center justify-center flex-shrink-0">3</span>
                        <span>Reinicia la aplicación desde la bandeja del sistema: clic derecho → <strong className="text-foreground">Salir</strong>, luego vuelve a abrirla.</span>
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
