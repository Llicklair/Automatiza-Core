"use client";

import { useTranslations } from "next-intl";
import {
    Zap, Plus, RotateCw, Loader2,
    BrainCircuit, Sparkles, Send, CheckCircle2, AlertCircle, X,
    Bot,
} from "lucide-react";
import InfoBanner from "@/components/InfoBanner";
import { ErrorBoundary } from "@/components/ui/ErrorBoundary";
import { buildTemplates } from "./_components/constants";
import WorkflowCard from "./_components/WorkflowCard";
import WorkflowFormModal from "./_components/WorkflowFormModal";
import { useAutomatizaciones } from "./_hooks/useAutomatizaciones";

export default function WorkflowsPage() {
    const t = useTranslations("automatizaciones");
    const TEMPLATES = buildTemplates(t);
    const {
        workflows, isLoading, isSubmitting, showModal, setShowModal,
        editingWorkflow, runningId, toast, setToast,
        expandedId, executions, loadingExec, refreshingExec,
        name, setName, description, setDescription,
        triggerType, setTriggerType, actionType, setActionType,
        actionIntent, setActionIntent, triggerConfig, setTriggerConfig,
        executionMode, setExecutionMode,
        nlQuery, setNlQuery, isParsing,
        parsedUiNodes, setParsedUiNodes, parsedUiEdges, setParsedUiEdges,
        graphKey, canBeDeterministic, modeLockedByAI,
        contextInputId, contextText, setContextText,
        chatLoading, chatResponse, setChatResponse,
        liveLogs, defaultEditorNodes, defaultEditorEdges,
        resetForm, handleCreate, handleEdit, handleSmartInput,
        handleDelete, handleRun, handleRunWithContext,
        handleCancel, handleResume, toggleStatus,
        refreshExecutions, toggleExpand, openEdit,
        applyTemplate, handleAddParallelBranch, toggleContextInput,
    } = useAutomatizaciones();

    return (
        <ErrorBoundary section="automatizaciones">
        <div className="min-h-screen bg-background text-foreground p-8">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-10">
                <div>
                    <h1 className="text-3xl font-light text-foreground flex items-center gap-3">
                        <div className="p-2 bg-primary/10 rounded-xl relative">
                            <div className="absolute inset-0 bg-primary/20 rounded-xl blur-xl" />
                            <Zap className="w-8 h-8 text-primary relative z-10" />
                        </div>
                        {t("header.title")}
                    </h1>
                    <p className="text-muted-foreground mt-2 ml-14 text-sm max-w-2xl">
                        {t("header.subtitle")}
                    </p>
                </div>
                <button onClick={() => setShowModal(true)}
                    className="flex items-center gap-2 bg-primary hover:bg-primary text-foreground px-5 py-2.5 rounded-full font-medium transition-all shadow-lg shadow-primary/20">
                    <Plus className="w-4 h-4" /> {t("header.newRule")}
                </button>
            </div>

            <InfoBanner id="automatizaciones-intro" title={t("intro.title")}>
                <p>
                    {t("intro.body")}{" "}
                    <span className="text-primary">{t("intro.example")}</span>
                </p>
                <p className="mt-1">
                    <a href="/mi-equipo?tab=tareas" className="text-primary hover:text-primary underline underline-offset-2 transition">
                        {t("intro.punctualLink")}
                    </a>
                </p>
            </InfoBanner>

            {/* AI Input */}
            <div className="mb-10 bg-card border border-primary/30 rounded-2xl p-6 relative shadow-lg shadow-primary/5">
                <div className="absolute top-0 right-0 p-4 opacity-5 blur-xl pointer-events-none overflow-hidden rounded-2xl">
                    <BrainCircuit className="w-48 h-48 text-primary" />
                </div>
                <div className="relative z-10 flex flex-col md:flex-row gap-4 items-center">
                    <div className="flex-shrink-0 flex items-center justify-center w-12 h-12 rounded-full bg-primary/10 text-primary">
                        <Sparkles className="w-6 h-6" />
                    </div>
                    <div className="flex-1 w-full">
                        <h3 className="text-sm font-semibold text-foreground mb-2">{t("ai.title")}</h3>
                        <p className="text-xs text-muted-foreground mb-2">{t("ai.subtitle")}</p>
                        <div className="flex bg-background border border-border rounded-xl overflow-hidden focus-within:border-primary transition-colors">
                            <input type="text" value={nlQuery}
                                onChange={(e) => { setNlQuery(e.target.value); if (chatResponse) setChatResponse(null); }}
                                onKeyDown={(e) => e.key === 'Enter' && handleSmartInput()}
                                placeholder={t("ai.placeholder")}
                                className="flex-1 bg-transparent border-none text-foreground text-sm px-4 py-3 focus:outline-none focus:ring-0 placeholder:text-muted-foreground/60" />
                            <button onClick={handleSmartInput} disabled={(isParsing || chatLoading) || !nlQuery.trim()}
                                className="px-5 bg-primary hover:bg-primary text-foreground font-medium text-sm transition-colors disabled:opacity-50 flex items-center gap-2">
                                {(isParsing || chatLoading) ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                                {(isParsing || chatLoading) ? t("ai.thinking") : t("ai.send")}
                            </button>
                        </div>
                    </div>
                </div>
                {chatResponse && (
                    <div className="relative z-10 mt-5 ml-16">
                        <div className="flex gap-3 items-start">
                            <div className="p-1.5 rounded-lg bg-primary/20 flex-shrink-0">
                                <Bot className="w-4 h-4 text-primary" />
                            </div>
                            <div className="flex-1 bg-background border border-primary/20 rounded-2xl rounded-tl-sm px-5 py-4">
                                <p className="text-sm text-foreground leading-relaxed whitespace-pre-wrap">{chatResponse}</p>
                            </div>
                        </div>
                    </div>
                )}
            </div>

            {/* Grid */}
            {isLoading ? (
                <div className="flex justify-center items-center h-64">
                    <RotateCw className="w-8 h-8 text-primary animate-spin" />
                </div>
            ) : workflows.length === 0 ? (
                <div className="space-y-8">
                    <div className="flex flex-col items-center justify-center py-12 text-center">
                        <div className="bg-primary/10 w-20 h-20 rounded-full flex items-center justify-center mb-6 border border-primary/20 shadow-lg shadow-primary/10">
                            <Zap className="w-10 h-10 text-primary" />
                        </div>
                        <h3 className="text-xl font-bold text-foreground mb-2">{t("empty.title")}</h3>
                        <p className="text-muted-foreground max-w-md mb-8 text-sm">
                            {t("empty.body")}
                        </p>
                        <button onClick={() => { resetForm(); setShowModal(true); }}
                            className="inline-flex items-center gap-2 bg-primary hover:bg-primary text-foreground px-6 py-3 rounded-xl transition-all shadow-lg font-medium">
                            <Plus className="w-5 h-5" /> {t("empty.createFromScratch")}
                        </button>
                    </div>
                    <div>
                        <p className="text-xs text-muted-foreground uppercase tracking-wider mb-4 text-center">{t("empty.orStartTemplate")}</p>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            {TEMPLATES.map((tpl, i) => {
                                const Icon = tpl.icon;
                                return (
                                    <button key={i} onClick={() => applyTemplate(tpl)}
                                        className={`text-left p-5 rounded-2xl border bg-card hover:bg-muted transition-all group ${tpl.border} hover:border-opacity-60`}>
                                        <div className={`w-10 h-10 rounded-xl ${tpl.bg} flex items-center justify-center mb-3 border ${tpl.border}`}>
                                            <Icon className={`w-5 h-5 ${tpl.color}`} />
                                        </div>
                                        <h4 className="text-sm font-semibold text-foreground mb-1">{tpl.name}</h4>
                                        <p className="text-xs text-muted-foreground line-clamp-2">{tpl.description}</p>
                                        <p className={`text-xs font-medium mt-3 ${tpl.color} flex items-center gap-1`}>
                                            <Sparkles className="w-3 h-3" /> {t("templates.use")}
                                        </p>
                                    </button>
                                );
                            })}
                        </div>
                    </div>
                </div>
            ) : (
                <div>
                    <div className="mb-6 flex items-center gap-2 flex-wrap">
                        <span className="text-xs text-muted-foreground/60">{t("templates.label")}</span>
                        {TEMPLATES.map((tpl, i) => {
                            const Icon = tpl.icon;
                            return (
                                <button key={i} onClick={() => applyTemplate(tpl)}
                                    className={`inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full border bg-card hover:bg-muted transition-all ${tpl.border} ${tpl.color}`}>
                                    <Icon className="w-3 h-3" /> {tpl.name}
                                </button>
                            );
                        })}
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6 items-start">
                        {workflows.map((wf) => (
                            <WorkflowCard
                                key={wf.id}
                                wf={wf}
                                isExpanded={expandedId === wf.id}
                                wfExecs={executions[wf.id] || []}
                                runningId={runningId}
                                loadingExec={loadingExec}
                                refreshingExec={refreshingExec}
                                contextInputId={contextInputId}
                                contextText={contextText}
                                liveLogs={liveLogs}
                                onToggleExpand={toggleExpand}
                                onRun={handleRun}
                                onDelete={handleDelete}
                                onEdit={openEdit}
                                onToggleStatus={toggleStatus}
                                onRefreshExecutions={refreshExecutions}
                                onCancel={handleCancel}
                                onResume={handleResume}
                                onContextInputToggle={toggleContextInput}
                                onContextTextChange={setContextText}
                                onRunWithContext={handleRunWithContext}
                            />
                        ))}
                    </div>
                </div>
            )}

            {/* Toast */}
            {toast && (
                <div className={`fixed bottom-6 right-6 z-50 flex items-center gap-3 px-5 py-3 rounded-2xl shadow-2xl text-sm font-medium ${toast.type === "ok" ? "bg-emerald-500/10 border border-emerald-500/20 text-emerald-400" : "bg-red-500/10 border border-red-500/20 text-red-400"}`}>
                    {toast.type === "ok" ? <CheckCircle2 className="w-5 h-5 flex-shrink-0" /> : <AlertCircle className="w-5 h-5 flex-shrink-0" />}
                    <span className="max-w-xs">{toast.msg}</span>
                    <button onClick={() => setToast(null)} className="ml-2 opacity-60 hover:opacity-100"><X className="w-4 h-4" /></button>
                </div>
            )}

            {/* Modal */}
            {showModal && (
                <WorkflowFormModal
                    editingWorkflow={editingWorkflow}
                    isSubmitting={isSubmitting}
                    name={name} setName={setName}
                    description={description} setDescription={setDescription}
                    triggerType={triggerType} setTriggerType={setTriggerType}
                    triggerConfig={triggerConfig} setTriggerConfig={setTriggerConfig}
                    actionType={actionType} setActionType={setActionType}
                    actionIntent={actionIntent} setActionIntent={setActionIntent}
                    executionMode={executionMode} setExecutionMode={setExecutionMode}
                    canBeDeterministic={canBeDeterministic}
                    modeLockedByAI={modeLockedByAI}
                    parsedUiNodes={parsedUiNodes} setParsedUiNodes={setParsedUiNodes}
                    parsedUiEdges={parsedUiEdges} setParsedUiEdges={setParsedUiEdges}
                    defaultEditorNodes={defaultEditorNodes}
                    defaultEditorEdges={defaultEditorEdges}
                    graphKey={graphKey}
                    onClose={() => setShowModal(false)}
                    onSubmit={editingWorkflow ? handleEdit : handleCreate}
                    onAddParallelBranch={handleAddParallelBranch}
                />
            )}
        </div>
        </ErrorBoundary>
    );
}
