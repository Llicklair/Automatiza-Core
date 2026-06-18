"use client";

import { useTranslations } from "next-intl";
import {
    RefreshCw, CheckCircle2, AlertCircle, Download,
    Server, Database, Cpu, Loader2, Terminal,
} from "lucide-react";
import { useActualizaciones } from "./_hooks/useActualizaciones";
import { UpdateChannelSelector } from "@/components/settings/UpdateChannelSelector";
import { PageContainer } from "@/components/shared/PageContainer";

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
    const t = useTranslations("configuracion");
    const { health, loading, error, updateStatus, updateError, downloadPercent, updateVersion, checks, loadHealth, checkForUpdates, installUpdate } = useActualizaciones();

    return (
        <PageContainer width="3xl" className="space-y-8">
            <div>
                <h1 className="text-2xl font-bold text-foreground">{t("actualizaciones.title")}</h1>
                <p className="text-sm text-muted-foreground mt-1">
                    {t("actualizaciones.subtitle")}
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
                            {t("actualizaciones.updatesTitle")}
                        </h2>
                        <p className="text-xs text-muted-foreground mt-1">
                            {health?.version ? t("actualizaciones.currentVersion", { version: health.version }) : t("actualizaciones.checkPrompt")}
                        </p>
                    </div>
                    <button
                        onClick={checkForUpdates}
                        disabled={["checking","downloading","downloaded"].includes(updateStatus)}
                        className="flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary disabled:opacity-50 text-foreground text-xs font-medium rounded-lg transition-colors"
                    >
                        {updateStatus === "checking" ? (
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                            <RefreshCw className="w-3.5 h-3.5" />
                        )}
                        {t("actualizaciones.checkUpdates")}
                    </button>
                </div>

                {updateStatus === "up_to_date" && (
                    <div className="mt-4 flex items-center gap-2 px-4 py-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-sm">
                        <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                        {t("actualizaciones.upToDate")}
                    </div>
                )}
                {updateStatus === "available" && (
                    <div className="mt-4 flex items-center gap-2 px-4 py-3 rounded-xl bg-primary/10 border border-primary/20 text-primary text-sm">
                        <Download className="w-4 h-4 flex-shrink-0" />
                        {updateVersion ? t("actualizaciones.newVersionDownloading", { version: updateVersion }) : t("actualizaciones.newVersionAvailableDownloading")}
                    </div>
                )}
                {updateStatus === "downloading" && (
                    <div className="mt-4 space-y-2 px-4 py-3 rounded-xl bg-primary/10 border border-primary/20">
                        <div className="flex items-center justify-between text-primary text-sm">
                            <span className="flex items-center gap-2">
                                <Loader2 className="w-4 h-4 animate-spin flex-shrink-0" />
                                {t("actualizaciones.downloading")}
                            </span>
                            <span className="text-xs font-mono">{downloadPercent}%</span>
                        </div>
                        <div className="w-full bg-primary/20 rounded-full h-1.5 overflow-hidden">
                            <div className="h-full bg-primary rounded-full transition-all duration-300" style={{ width: `${downloadPercent}%` }} />
                        </div>
                    </div>
                )}
                {updateStatus === "downloaded" && (
                    <div className="mt-4 flex items-center justify-between px-4 py-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
                        <span className="flex items-center gap-2 text-emerald-300 text-sm">
                            <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                            {t("actualizaciones.readyToInstall")}
                        </span>
                        <button
                            onClick={installUpdate}
                            className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-500 hover:bg-emerald-600 text-white text-xs font-medium rounded-lg transition-colors"
                        >
                            <Download className="w-3.5 h-3.5" />
                            {t("actualizaciones.installRestart")}
                        </button>
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
                        {t("actualizaciones.systemStatus")}
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
                        {t("actualizaciones.refresh")}
                    </button>
                </div>

                <div className="divide-y divide-border">
                    <StatusRow
                        icon={<Server className="w-4 h-4" />}
                        label={t("actualizaciones.apiServer")}
                        status={health ? "ok" : loading ? "loading" : "error"}
                        detail={health ? t("actualizaciones.respondingOk") : t("actualizaciones.noConnection")}
                    />
                    <StatusRow
                        icon={<Database className="w-4 h-4" />}
                        label={t("actualizaciones.database")}
                        status={
                            loading ? "loading"
                            : checks.postgres?.status === "up" ? "ok"
                            : "error"
                        }
                        detail={
                            checks.postgres?.status === "up"
                                ? t("actualizaciones.postgresLatency", { ms: checks.postgres.latency_ms?.toFixed(0) || "?" })
                                : checks.postgres?.error || t("actualizaciones.notAvailable")
                        }
                    />
                    <StatusRow
                        icon={<Cpu className="w-4 h-4" />}
                        label={t("actualizaciones.taskEngine")}
                        status={
                            loading ? "loading"
                            : checks.task_runner?.status === "up" ? "ok"
                            : "warning"
                        }
                        detail={
                            checks.task_runner?.status === "up"
                                ? t("actualizaciones.activeTasks", { count: checks.task_runner.active_tasks || 0 })
                                : t("actualizaciones.inactive")
                        }
                    />
                </div>
            </div>

            {/* Cómo actualizar */}
            <div className="bg-card border border-border rounded-2xl p-6 space-y-4">
                <h2 className="text-sm font-semibold text-foreground flex items-center gap-2">
                    <Terminal className="w-4 h-4 text-muted-foreground" />
                    {t("actualizaciones.howItWorksTitle")}
                </h2>
                <p className="text-sm text-muted-foreground">
                    {t.rich("actualizaciones.howItWorksIntro", {
                        strong: (chunks) => <strong className="text-foreground">{chunks}</strong>,
                    })}
                </p>
                <ol className="space-y-3 text-sm text-muted-foreground">
                    <li className="flex gap-3">
                        <span className="w-5 h-5 rounded-full bg-primary/20 border border-primary/20 text-primary text-xs font-bold flex items-center justify-center flex-shrink-0">1</span>
                        <span>{t("actualizaciones.step1")}</span>
                    </li>
                    <li className="flex gap-3">
                        <span className="w-5 h-5 rounded-full bg-primary/20 border border-primary/20 text-primary text-xs font-bold flex items-center justify-center flex-shrink-0">2</span>
                        <span>{t("actualizaciones.step2")}</span>
                    </li>
                    <li className="flex gap-3">
                        <span className="w-5 h-5 rounded-full bg-primary/20 border border-primary/20 text-primary text-xs font-bold flex items-center justify-center flex-shrink-0">3</span>
                        <span>{t.rich("actualizaciones.step3", {
                            strong: (chunks) => <strong className="text-foreground">{chunks}</strong>,
                        })}</span>
                    </li>
                </ol>
                <div className="flex items-start gap-2 px-3 py-2.5 rounded-lg bg-primary/5 border border-primary/15 text-muted-foreground text-xs">
                    <AlertCircle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
                    {t("actualizaciones.migrationsNote")}
                </div>
            </div>

            {/* DIS.UPD — Selector de canal stable/beta */}
            <div className="bg-card border border-border rounded-2xl p-6">
                <UpdateChannelSelector />
            </div>
        </PageContainer>
    );
}
