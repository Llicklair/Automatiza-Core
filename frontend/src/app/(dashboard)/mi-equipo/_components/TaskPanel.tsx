"use client";

import { Plus, RefreshCw, Trash2, Bot, Loader2 } from "lucide-react";
import { useTranslations } from "next-intl";
import InfoBanner from "@/components/InfoBanner";
import { ErrorBoundary } from "@/components/ui/ErrorBoundary";
import { CostModal } from "@/components/ai/CostModal";
import { TaskRow } from "./TaskRow";
import { ChatSection } from "./ChatSection";
import { NewTaskModal } from "./NewTaskModal";
import { useTaskPanel } from "../_hooks/useTaskPanel";

interface TaskPanelProps {
    isActive: boolean;
}

export function TaskPanel({ isActive }: TaskPanelProps) {
    const t = useTranslations("miEquipo");
    const tp = useTaskPanel(isActive);

    return (
        <ErrorBoundary section="tareas">
        <div>
            {/* Header con acciones */}
            <div className="flex items-center justify-between mb-6">
                <p className="text-sm text-muted-foreground">
                    {t("taskPanel.subtitle")}
                </p>
                <div className="flex items-center gap-3">
                    <button
                        onClick={tp.load}
                        className="p-2 rounded-lg border border-border text-muted-foreground hover:text-foreground hover:border-border transition"
                        title={t("taskPanel.refresh")}
                     aria-label={t("taskPanel.refresh")}>
                        <RefreshCw className="w-4 h-4" aria-hidden="true" />
                    </button>
                    <button
                        onClick={tp.cleanupTasks}
                        disabled={tp.tasks.length === 0}
                        className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-red-500/20 text-red-400/70 hover:text-red-400 hover:bg-red-500/10 text-xs font-medium transition disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:bg-transparent disabled:hover:text-red-400/70"
                        title={t("taskPanel.cleanupTitle")}
                    >
                        <Trash2 className="w-3.5 h-3.5" />
                        {t("taskPanel.cleanup")}{(tp.activeTasks.length + tp.doneTasks.length) > 0 ? ` (${tp.activeTasks.length + tp.doneTasks.length})` : ""}
                    </button>
                    <button
                        onClick={() => tp.setShowNew(true)}
                        className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-primary hover:bg-primary text-foreground text-sm font-medium transition shadow-lg shadow-primary/20"
                    >
                        <Plus className="w-4 h-4" /> {t("taskPanel.newTask")}
                    </button>
                </div>
            </div>

            <InfoBanner id="tareas-intro" title={t("taskPanel.infoTitle")}>
                <p>
                    {t.rich("taskPanel.infoBody", {
                        example: (chunks) => <span className="text-primary">{chunks}</span>,
                    })}
                </p>
                <p className="mt-1">
                    <a href="/automatizaciones" className="text-primary hover:text-primary underline underline-offset-2 transition">
                        {t("taskPanel.infoLink")}
                    </a>
                </p>
            </InfoBanner>

            {/* Chat con la IA */}
            <ChatSection
                chatMessages={tp.chatMessages}
                setChatMessages={tp.setChatMessages}
                chatQuery={tp.chatQuery}
                setChatQuery={tp.setChatQuery}
                chatLoading={tp.chatLoading}
                onSend={tp.handleChat}
                progressSummary={tp.chatProgress}
                onStop={tp.stopChat}
                isStreaming={tp.chatStreaming}
            />

            {/* Modal nueva tarea */}
            {tp.showNew && (
                <NewTaskModal
                    domain={tp.domain}
                    setDomain={tp.setDomain}
                    selectedEmployeeId={tp.selectedEmployeeId}
                    setSelectedEmployeeId={tp.setSelectedEmployeeId}
                    employees={tp.employees}
                    intent={tp.intent}
                    setIntent={tp.setIntent}
                    creating={tp.creating}
                    error={tp.error}
                    onClose={() => tp.setShowNew(false)}
                    onSubmit={tp.createTask}
                />
            )}

            {/* Lista de tareas activas */}
            {tp.activeTasks.length > 0 && (
                <div className="mb-6">
                    <h2 className="text-xs text-muted-foreground uppercase tracking-wider mb-3 font-medium">{t("taskPanel.inProgress", { n: tp.activeTasks.length })}</h2>
                    <div className="rounded-xl border border-border bg-card overflow-hidden">
                        <div className="grid grid-cols-12 gap-4 px-6 py-3 border-b border-border text-xs font-medium text-muted-foreground uppercase tracking-wide">
                            <div className="col-span-5">{t("taskPanel.colInstruction")}</div>
                            <div className="col-span-2">{t("taskPanel.colAgent")}</div>
                            <div className="col-span-2">{t("taskPanel.colStatus")}</div>
                            <div className="col-span-2">{t("taskPanel.colCreated")}</div>
                            <div className="col-span-1 text-right">{t("taskPanel.colAction")}</div>
                        </div>
                        {tp.activeTasks.map(task => (
                            <TaskRow key={task.id} task={task} cancelTask={tp.cancelTask} onReply={tp.replyToTask} />
                        ))}
                    </div>
                </div>
            )}

            {/* Historial */}
            <div>
                <h2 className="text-xs text-muted-foreground uppercase tracking-wider mb-3 font-medium">{t("taskPanel.history")}</h2>
                <div className="rounded-xl border border-border bg-card overflow-hidden">
                    <div className="grid grid-cols-12 gap-4 px-6 py-3 border-b border-border text-xs font-medium text-muted-foreground uppercase tracking-wide">
                        <div className="col-span-5">{t("taskPanel.colInstruction")}</div>
                        <div className="col-span-2">{t("taskPanel.colAgent")}</div>
                        <div className="col-span-2">{t("taskPanel.colStatus")}</div>
                        <div className="col-span-2">{t("taskPanel.colCreated")}</div>
                        <div className="col-span-1 text-right">{t("taskPanel.colAction")}</div>
                    </div>
                    {tp.loading ? (
                        <div className="py-14 flex items-center justify-center gap-2 text-muted-foreground text-sm">
                            <Loader2 className="w-4 h-4 animate-spin" /> {t("taskPanel.loading")}
                        </div>
                    ) : tp.doneTasks.length === 0 && tp.activeTasks.length === 0 ? (
                        <div className="py-14 text-center">
                            <Bot className="w-8 h-8 text-muted-foreground mx-auto mb-3" />
                            <p className="text-muted-foreground text-sm">{t("taskPanel.emptyTitle")}</p>
                            <p className="text-muted-foreground text-xs mt-1">{t("taskPanel.emptyHint")}</p>
                        </div>
                    ) : tp.doneTasks.length === 0 ? (
                        <div className="py-8 text-center text-muted-foreground text-xs">{t("taskPanel.noneCompleted")}</div>
                    ) : (
                        tp.doneTasks.map(task => (
                            <TaskRow key={task.id} task={task} cancelTask={tp.cancelTask} onReply={tp.replyToTask} />
                        ))
                    )}
                </div>
            </div>

            {/* UI.COST — modal post-abort con tokens y € estimados */}
            {tp.costModal && (
                <CostModal
                    taskId={tp.costModal.taskId}
                    reason={tp.costModal.reason}
                    onClose={tp.closeCostModal}
                />
            )}
        </div>
        </ErrorBoundary>
    );
}
