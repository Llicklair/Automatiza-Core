"use client";

import { useTranslations } from "next-intl";
import { Zap, X, Loader2, BrainCircuit, Cpu, Info, GitFork } from "lucide-react";
import { Workflow } from "@/lib/api";
import WorkflowGraph from "@/components/Workflows/WorkflowGraph";
import ScheduleBuilder from "./ScheduleBuilder";
import { hasFanOut } from "./constants";

interface WorkflowFormModalProps {
    editingWorkflow: Workflow | null;
    isSubmitting: boolean;
    name: string;
    setName: (v: string) => void;
    description: string;
    setDescription: (v: string) => void;
    triggerType: string;
    setTriggerType: (v: string) => void;
    triggerConfig: any;
    setTriggerConfig: (v: any) => void;
    actionType: string;
    setActionType: (v: string) => void;
    actionIntent: string;
    setActionIntent: (v: string) => void;
    executionMode: "reasoning" | "deterministic";
    setExecutionMode: (v: "reasoning" | "deterministic") => void;
    canBeDeterministic: boolean | null;
    modeLockedByAI: boolean;
    parsedUiNodes: any[] | null;
    setParsedUiNodes: (v: any[] | null) => void;
    parsedUiEdges: any[] | null;
    setParsedUiEdges: (v: any[] | null) => void;
    defaultEditorNodes: any[];
    defaultEditorEdges: any[];
    graphKey: number;
    onClose: () => void;
    onSubmit: (e: React.FormEvent) => void;
    onAddParallelBranch: () => void;
}

export default function WorkflowFormModal({
    editingWorkflow, isSubmitting,
    name, setName, description, setDescription,
    triggerType, setTriggerType, triggerConfig, setTriggerConfig,
    actionType, setActionType, actionIntent, setActionIntent,
    executionMode, setExecutionMode, canBeDeterministic, modeLockedByAI,
    parsedUiNodes, setParsedUiNodes, parsedUiEdges, setParsedUiEdges,
    defaultEditorNodes, defaultEditorEdges, graphKey,
    onClose, onSubmit, onAddParallelBranch,
}: WorkflowFormModalProps) {
    const t = useTranslations("automatizaciones");
    return (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-card border border-border rounded-2xl w-full max-w-3xl overflow-hidden shadow-2xl max-h-[90vh] overflow-y-auto">
                <div className="p-6 border-b border-border flex justify-between items-center">
                    <h2 className="text-lg font-semibold text-foreground flex items-center gap-2">
                        <Zap className="w-5 h-5 text-primary" />
                        {editingWorkflow ? t("modal.editTitle") : t("modal.newTitle")}
                    </h2>
                    <button onClick={onClose} className="text-muted-foreground hover:text-foreground transition" aria-label={t("modal.close")}>
                        <X className="w-5 h-5" aria-hidden="true" />
                    </button>
                </div>
                <form onSubmit={onSubmit} className="p-6 space-y-4">
                    <div>
                        <label className="block text-xs text-muted-foreground mb-1.5 uppercase tracking-wider">{t("modal.ruleName")}</label>
                        <input required type="text" value={name} onChange={e => setName(e.target.value)}
                            placeholder={t("modal.ruleNamePlaceholder")}
                            className="w-full bg-background border border-border rounded-lg px-4 py-2.5 text-foreground text-sm focus:outline-none focus:border-primary transition" />
                    </div>
                    <div>
                        <label className="block text-xs text-muted-foreground mb-1.5 uppercase tracking-wider">{t("modal.description")}</label>
                        <textarea value={description} onChange={e => setDescription(e.target.value)}
                            placeholder={t("modal.descriptionPlaceholder")}
                            className="w-full bg-background border border-border rounded-lg px-4 py-2.5 text-foreground text-sm focus:outline-none focus:border-primary transition resize-none h-16" />
                    </div>
                    <div className="grid grid-cols-2 gap-4 pt-3 border-t border-border">
                        <div>
                            <label className="block text-xs font-semibold text-primary mb-1.5 uppercase tracking-wider">{t("modal.triggerWhen")}</label>
                            <select value={triggerType} onChange={e => setTriggerType(e.target.value)}
                                className="w-full bg-background border border-border rounded-lg px-4 py-2.5 text-foreground text-sm focus:outline-none focus:border-primary">
                                <option value="event_based">{t("modal.triggerEventOption")}</option>
                                <option value="schedule_based">{t("modal.triggerScheduleOption")}</option>
                                <option value="manual">{t("modal.triggerManualOption")}</option>
                            </select>
                        </div>
                        <div>
                            <label className="block text-xs font-semibold text-emerald-400 mb-1.5 uppercase tracking-wider">{t("modal.actionWhat")}</label>
                            <select value={actionType} onChange={e => setActionType(e.target.value)}
                                className="w-full bg-background border border-border rounded-lg px-4 py-2.5 text-foreground text-sm focus:outline-none focus:border-emerald-500">
                                <option value="ai_task">{t("modal.actionAiTask")}</option>
                                <option value="notify">{t("modal.actionNotify")}</option>
                                <option value="webhook">{t("modal.actionWebhook")}</option>
                            </select>
                        </div>
                    </div>

                    {triggerType === "schedule_based" && (
                        <ScheduleBuilder value={triggerConfig.cron || "0 9 * * 1"} onChange={cron => setTriggerConfig({ cron })} />
                    )}
                    {triggerType === "event_based" && (
                        <div>
                            <label className="block text-xs text-muted-foreground mb-2 uppercase tracking-wider">{t("modal.eventTrigger")}</label>
                            <div className="grid grid-cols-2 gap-2">
                                {[
                                    { value: "invoice_created", label: t("events.invoiceCreated") },
                                    { value: "invoice_paid", label: t("events.invoicePaid") },
                                    { value: "client_created", label: t("events.clientCreated") },
                                    { value: "document_uploaded", label: t("events.documentUploaded") },
                                    { value: "any", label: t("events.any") },
                                ].map(ev => {
                                    const selected = (triggerConfig.events || []).includes(ev.value);
                                    return (
                                        <button
                                            key={ev.value}
                                            type="button"
                                            onClick={() => {
                                                const cur: string[] = triggerConfig.events || [];
                                                setTriggerConfig({ events: selected ? cur.filter((e: string) => e !== ev.value) : [...cur, ev.value] });
                                            }}
                                            className={`text-left px-3 py-2 rounded-lg border text-xs transition-all ${selected ? "border-primary/60 bg-primary/10 text-primary" : "border-border bg-background text-muted-foreground hover:border-border"}`}
                                        >
                                            {ev.label}
                                        </button>
                                    );
                                })}
                            </div>
                        </div>
                    )}

                    <div>
                        <label className="block text-xs text-muted-foreground mb-1.5 uppercase tracking-wider">
                            {t("modal.instructionLabel")}
                            <span className="text-muted-foreground/60 ml-1 normal-case">{t("modal.instructionHint")}</span>
                        </label>
                        <textarea required rows={3} value={actionIntent} onChange={e => setActionIntent(e.target.value)}
                            placeholder={t("modal.instructionPlaceholder")}
                            className="w-full bg-background border border-border rounded-lg px-4 py-2.5 text-foreground text-sm focus:outline-none focus:border-emerald-500 transition resize-none" />
                    </div>

                    {/* Execution mode selector */}
                    <div className="pt-3 border-t border-border">
                        <label className="block text-xs text-muted-foreground mb-2 uppercase tracking-wider">{t("modal.executionMode")}</label>
                        {canBeDeterministic === true && (
                            <div className="mb-3 flex items-start gap-2 bg-emerald-500/8 border border-emerald-500/25 rounded-lg px-3 py-2">
                                <Info className="w-3.5 h-3.5 text-emerald-400 mt-0.5 flex-shrink-0" />
                                <p className="text-[11px] text-emerald-300/90 leading-relaxed">
                                    {t.rich("modal.deterministicHint", { strong: (chunks) => <strong>{chunks}</strong> })}
                                </p>
                            </div>
                        )}
                        {canBeDeterministic === false && (
                            <div className="mb-3 flex items-start gap-2 bg-blue-500/8 border border-blue-500/25 rounded-lg px-3 py-2">
                                <Info className="w-3.5 h-3.5 text-blue-400 mt-0.5 flex-shrink-0" />
                                <p className="text-[11px] text-blue-300/90 leading-relaxed">
                                    {t.rich("modal.reasoningHint", { strong: (chunks) => <strong>{chunks}</strong> })}
                                </p>
                            </div>
                        )}
                        {modeLockedByAI ? (
                            // Modo decidido por la IA — solo lectura
                            <div className={`flex flex-col items-start gap-1 rounded-xl px-4 py-3 border cursor-default select-none ${
                                executionMode === "deterministic"
                                    ? "border-emerald-500/50 bg-emerald-500/10 text-emerald-300"
                                    : "border-blue-500/50 bg-blue-500/10 text-blue-300"
                            }`}>
                                <div className="flex items-center gap-2">
                                    {executionMode === "deterministic"
                                        ? <Cpu className="w-4 h-4" />
                                        : <BrainCircuit className="w-4 h-4" />}
                                    <span className="text-xs font-semibold">
                                        {executionMode === "deterministic" ? t("modal.deterministic") : t("modal.withAi")} · {t("modal.decidedByAi")}
                                    </span>
                                </div>
                                <p className="text-[10px] leading-snug opacity-70">
                                    {executionMode === "deterministic"
                                        ? t("modal.deterministicDesc")
                                        : t("modal.withAiDesc")}
                                </p>
                            </div>
                        ) : (
                            // Modo elegido por el usuario — interactivo
                            <div className="grid grid-cols-2 gap-3">
                                <button type="button" onClick={() => setExecutionMode("reasoning")}
                                    className={`flex flex-col items-start gap-1 rounded-xl px-4 py-3 border text-left transition-all ${executionMode === "reasoning"
                                        ? "border-blue-500/50 bg-blue-500/10 text-blue-300"
                                        : "border-border bg-background text-muted-foreground hover:border-border"}`}>
                                    <div className="flex items-center gap-2">
                                        <BrainCircuit className="w-4 h-4" />
                                        <span className="text-xs font-semibold">{t("modal.withAi")}</span>
                                    </div>
                                    <p className="text-[10px] leading-snug opacity-70">
                                        {t("modal.withAiDesc")}
                                    </p>
                                </button>
                                <button type="button" onClick={() => setExecutionMode("deterministic")}
                                    className={`flex flex-col items-start gap-1 rounded-xl px-4 py-3 border text-left transition-all ${executionMode === "deterministic"
                                        ? "border-emerald-500/50 bg-emerald-500/10 text-emerald-300"
                                        : "border-border bg-background text-muted-foreground hover:border-border"}`}>
                                    <div className="flex items-center gap-2">
                                        <Cpu className="w-4 h-4" />
                                        <span className="text-xs font-semibold">{t("modal.deterministic")}</span>
                                    </div>
                                    <p className="text-[10px] leading-snug opacity-70">
                                        {t("modal.deterministicDesc")}
                                    </p>
                                </button>
                            </div>
                        )}
                        {executionMode === "deterministic" && (
                            <div className="mt-2 flex items-start gap-2 bg-emerald-500/5 border border-emerald-500/15 rounded-lg px-3 py-2">
                                <Info className="w-3.5 h-3.5 text-emerald-400 mt-0.5 flex-shrink-0" />
                                <p className="text-[10px] text-emerald-300/80 leading-relaxed">
                                    {t("modal.deterministicNotice")}
                                </p>
                            </div>
                        )}
                        {executionMode === "deterministic" && canBeDeterministic === false && (
                            <div className="mt-2 flex items-start gap-2 bg-amber-500/10 border border-amber-500/30 rounded-lg px-3 py-2">
                                <Info className="w-3.5 h-3.5 text-amber-400 mt-0.5 flex-shrink-0" />
                                <p className="text-[10px] text-amber-300/90 leading-relaxed">
                                    {t.rich("modal.deterministicWarning", { strong: (chunks) => <strong>{chunks}</strong> })}
                                </p>
                            </div>
                        )}
                    </div>

                    {/* Editor visual de nodos */}
                    <div className="pt-3 border-t border-border">
                        <div className="flex items-center justify-between mb-2">
                            <p className="text-[10px] text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
                                <BrainCircuit className="w-3 h-3 text-primary" /> {t("modal.visualEditor")}
                            </p>
                            <div className="flex items-center gap-2">
                                {hasFanOut(parsedUiEdges) && (
                                    <span className="flex items-center gap-1 text-[9px] px-2 py-0.5 rounded-full border font-semibold text-violet-400 bg-violet-500/10 border-violet-500/20">
                                        <GitFork className="w-2.5 h-2.5" />
                                        {t("modal.parallelExecution")}
                                    </span>
                                )}
                                <button
                                    type="button"
                                    onClick={onAddParallelBranch}
                                    className="flex items-center gap-1 text-[9px] px-2 py-0.5 rounded-full border font-semibold text-violet-300 bg-violet-500/10 border-violet-500/20 hover:bg-violet-500/20 transition-colors"
                                    title={t("modal.addParallelBranchTitle")}
                                >
                                    <GitFork className="w-2.5 h-2.5" />
                                    {t("modal.addParallelBranch")}
                                </button>
                            </div>
                        </div>
                        <div className="h-72 rounded-xl overflow-hidden border border-border">
                            <WorkflowGraph
                                key={graphKey}
                                nodes={(parsedUiNodes && parsedUiNodes.length > 0) ? parsedUiNodes : defaultEditorNodes}
                                edges={(parsedUiEdges && parsedUiEdges.length > 0) ? parsedUiEdges : defaultEditorEdges}
                                editable
                                onNodesChange={(n) => setParsedUiNodes(n)}
                                onEdgesChange={(e) => setParsedUiEdges(e)}
                            />
                        </div>
                    </div>
                    <div className="pt-4 flex justify-end gap-3 border-t border-border">
                        <button type="button" onClick={onClose} className="px-5 py-2.5 text-muted-foreground hover:text-foreground transition text-sm">{t("modal.cancel")}</button>
                        <button type="submit" disabled={isSubmitting}
                            className="bg-primary hover:bg-primary text-foreground px-6 py-2.5 rounded-lg font-medium text-sm transition disabled:opacity-50 flex items-center gap-2">
                            {isSubmitting && <Loader2 className="w-4 h-4 animate-spin" />}
                            {isSubmitting ? t("modal.saving") : editingWorkflow ? t("modal.saveChanges") : t("modal.createRule")}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
