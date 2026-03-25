"use client";

import { useEffect, useState, useRef, useMemo } from "react";
import { api, Workflow, WorkflowExecution } from "@/lib/api";
import {
    Zap, Plus, RotateCw, Loader2,
    BrainCircuit, Sparkles, Send, CheckCircle2, AlertCircle, X,
} from "lucide-react";
import { logError } from "@/lib/logger";
import InfoBanner from "@/components/InfoBanner";
import { TEMPLATES } from "./_components/constants";
import WorkflowCard from "./_components/WorkflowCard";
import WorkflowFormModal from "./_components/WorkflowFormModal";

export default function WorkflowsPage() {
    const [workflows, setWorkflows] = useState<Workflow[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [showModal, setShowModal] = useState(false);
    const [editingWorkflow, setEditingWorkflow] = useState<Workflow | null>(null);
    const [runningId, setRunningId] = useState<string | null>(null);
    const [toast, setToast] = useState<{ msg: string; type: "ok" | "err" } | null>(null);
    const [expandedId, setExpandedId] = useState<string | null>(null);
    const [executions, setExecutions] = useState<Record<string, WorkflowExecution[]>>({});
    const [loadingExec, setLoadingExec] = useState<string | null>(null);
    const [refreshingExec, setRefreshingExec] = useState<string | null>(null);

    // Form
    const [name, setName] = useState("");
    const [description, setDescription] = useState("");
    const [triggerType, setTriggerType] = useState("event_based");
    const [actionType, setActionType] = useState("ai_task");
    const [actionIntent, setActionIntent] = useState("");
    const [triggerConfig, setTriggerConfig] = useState<any>({ events: ["any"] });
    const [executionMode, setExecutionMode] = useState<"reasoning" | "deterministic">("reasoning");

    // AI Parser
    const [nlQuery, setNlQuery] = useState("");
    const [isParsing, setIsParsing] = useState(false);
    const [parsedUiNodes, setParsedUiNodes] = useState<any[] | null>(null);
    const [parsedUiEdges, setParsedUiEdges] = useState<any[] | null>(null);
    const [graphKey, setGraphKey] = useState(0);

    // Context input per workflow
    const [contextInputId, setContextInputId] = useState<string | null>(null);
    const [contextText, setContextText] = useState("");

    // Live logs
    const [liveLogs, setLiveLogs] = useState<Record<string, string[]>>({});
    const logsRef = useRef<ReturnType<typeof setInterval> | null>(null);
    const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

    const defaultEditorNodes = useMemo(() => [
        { id: "trigger_default", type: "trigger", position: { x: 250, y: 0 }, data: { label: "Trigger", trigger_type: triggerType } },
        { id: "skill_default", type: "skill", position: { x: 250, y: 130 }, data: { label: "Agente IA", domain: "billing", description: actionIntent } },
    ], [triggerType, actionIntent]);
    const defaultEditorEdges = useMemo(() => [
        { id: "e-trigger_default-skill_default", source: "trigger_default", target: "skill_default" },
    ], []);

    // ─── Data loading ────────────────────────────────────────────────────────

    useEffect(() => { loadWorkflows(); }, []);

    // Auto-refresh polling for active executions
    useEffect(() => {
        if (!expandedId) {
            if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
            return;
        }
        const wfExecs = executions[expandedId] || [];
        const hasActive = wfExecs.some(e => e.status === "running" || e.status === "paused");
        if (hasActive) {
            pollRef.current = setInterval(() => { loadExecutions(expandedId); }, 4000);
        } else {
            if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
        }
        return () => { if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; } };
    }, [expandedId, executions]);

    // Live logs polling
    useEffect(() => {
        if (logsRef.current) { clearInterval(logsRef.current); logsRef.current = null; }
        if (!expandedId) return;
        const wfExecs = executions[expandedId] || [];
        const active = wfExecs.find(e => e.status === "running");
        if (!active) return;
        loadLogs(expandedId, active.id);
        logsRef.current = setInterval(async () => {
            const status = await loadLogs(expandedId, active.id);
            if (status !== "running") {
                clearInterval(logsRef.current!);
                logsRef.current = null;
                await loadExecutions(expandedId);
            }
        }, 2000);
        return () => { if (logsRef.current) { clearInterval(logsRef.current); logsRef.current = null; } };
    }, [expandedId, executions]);

    const loadWorkflows = async () => {
        setIsLoading(true);
        try { setWorkflows(await api.workflows.list()); }
        catch (e) { logError("automatizaciones/page", e); }
        finally { setIsLoading(false); }
    };

    const loadExecutions = async (id: string) => {
        setLoadingExec(id);
        try {
            const data = await api.workflows.executions(id);
            setExecutions(prev => ({ ...prev, [id]: data }));
        } catch (e) { logError("automatizaciones/page", e); }
        finally { setLoadingExec(null); }
    };

    const loadLogs = async (workflowId: string, executionId: string) => {
        try {
            const data = await api.workflows.executionLogs(workflowId, executionId);
            setLiveLogs(prev => ({ ...prev, [executionId]: data.lines }));
            return data.status;
        } catch { return "unknown"; }
    };

    // ─── Actions ─────────────────────────────────────────────────────────────

    const showToast = (msg: string, type: "ok" | "err") => {
        setToast({ msg, type });
        setTimeout(() => setToast(null), 5000);
    };

    const resetForm = () => {
        setName(""); setDescription(""); setTriggerType("event_based");
        setActionType("ai_task"); setActionIntent(""); setTriggerConfig({ events: ["any"] });
        setParsedUiNodes(null); setParsedUiEdges(null);
        setExecutionMode("reasoning"); setEditingWorkflow(null);
    };

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsSubmitting(true);
        try {
            await api.workflows.create({
                name, description, trigger_type: triggerType, trigger_config: triggerConfig,
                action_type: actionType, action_config: { instruction: actionIntent },
                execution_mode: executionMode,
                ui_nodes: parsedUiNodes || defaultEditorNodes,
                ui_edges: parsedUiEdges || defaultEditorEdges,
            });
            setShowModal(false); resetForm(); await loadWorkflows();
            showToast("Automatización creada correctamente", "ok");
        } catch (error: any) {
            showToast(error.message || "Error creando la regla", "err");
        } finally { setIsSubmitting(false); }
    };

    const handleEdit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!editingWorkflow) return;
        setIsSubmitting(true);
        try {
            const updated = await api.workflows.update(editingWorkflow.id, {
                name, description, trigger_type: triggerType, trigger_config: triggerConfig,
                action_type: actionType, action_config: { instruction: actionIntent },
                execution_mode: executionMode,
                ui_nodes: parsedUiNodes || defaultEditorNodes,
                ui_edges: parsedUiEdges || defaultEditorEdges,
            });
            setWorkflows(workflows.map(w => w.id === updated.id ? updated : w));
            setShowModal(false); resetForm();
            showToast("Automatización actualizada correctamente", "ok");
        } catch (error: any) {
            showToast(error.message || "Error al actualizar", "err");
        } finally { setIsSubmitting(false); }
    };

    const handleParseAI = async () => {
        if (!nlQuery.trim()) return;
        setIsParsing(true);
        try {
            const parsed = await api.workflows.parse(nlQuery);
            setName(parsed.name || ""); setDescription(parsed.description || "");
            setTriggerType(parsed.trigger_type || "event_based");
            setTriggerConfig(parsed.trigger_config || { events: ["any"] });
            setActionType(parsed.action_type || "ai_task");
            setActionIntent(parsed.action_config?.instruction || "");
            setParsedUiNodes(parsed.ui_nodes || null);
            setParsedUiEdges(parsed.ui_edges || null);
            setNlQuery(""); setShowModal(true);
            showToast("Borrador de regla creado por IA. Revisa y confirma.", "ok");
        } catch (e: any) {
            showToast("Error al procesar con IA: " + (e.message || "Fallo"), "err");
        } finally { setIsParsing(false); }
    };

    const handleDelete = async (id: string) => {
        try {
            await api.workflows.delete(id);
            setWorkflows(workflows.filter(w => w.id !== id));
            if (expandedId === id) { setExpandedId(null); }
            showToast("Automatización eliminada correctamente", "ok");
        } catch (e: any) { showToast(e.message || "Error al eliminar la automatización", "err"); }
    };

    const handleRun = async (id: string) => {
        setRunningId(id);
        try {
            await api.workflows.run(id);
            showToast("Automatización lanzada. El agente IA está procesando la instrucción.", "ok");
            if (expandedId === id) await loadExecutions(id);
        } catch (error: any) { showToast(error.message || "Error al ejecutar", "err"); }
        finally { setRunningId(null); }
    };

    const handleRunWithContext = async (wfId: string) => {
        setRunningId(wfId);
        try {
            await api.workflows.runWithContext(wfId, contextText);
            showToast("Automatización lanzada con el contexto indicado.", "ok");
            setContextInputId(null); setContextText("");
            if (expandedId === wfId) await loadExecutions(wfId);
        } catch (error: any) { showToast(error.message || "Error al ejecutar", "err"); }
        finally { setRunningId(null); }
    };

    const handleCancel = async (workflowId: string, executionId: string) => {
        try {
            await api.workflows.cancelExecution(workflowId, executionId);
            showToast("Ejecución cancelada.", "ok");
            await loadExecutions(workflowId);
        } catch (error: any) { showToast(error.message || "Error al cancelar", "err"); }
    };

    const handleResume = async (workflowId: string, executionId: string) => {
        try {
            await api.workflows.resumeExecution(workflowId, executionId);
            showToast("Ejecución reanudada. El motor de nodos continúa procesando.", "ok");
            await loadExecutions(workflowId);
        } catch (error: any) { showToast(error.message || "Error al reanudar", "err"); }
    };

    const toggleStatus = async (workflow: Workflow) => {
        try {
            const updated = await api.workflows.update(workflow.id, { is_active: !workflow.is_active });
            setWorkflows(workflows.map(w => w.id === updated.id ? updated : w));
        } catch (e) { logError("automatizaciones/page", e); }
    };

    const refreshExecutions = async (e: React.MouseEvent, id: string) => {
        e.stopPropagation();
        setRefreshingExec(id);
        try {
            const data = await api.workflows.executions(id);
            setExecutions(prev => ({ ...prev, [id]: data }));
        } catch (e) { logError("automatizaciones/page", e); }
        finally { setRefreshingExec(null); }
    };

    const toggleExpand = async (id: string) => {
        if (expandedId === id) { setExpandedId(null); }
        else { setExpandedId(id); if (!executions[id]) await loadExecutions(id); }
    };

    const openEdit = (wf: Workflow) => {
        setEditingWorkflow(wf); setName(wf.name); setDescription(wf.description || "");
        setTriggerType(wf.trigger_type); setTriggerConfig(wf.trigger_config || { events: ["any"] });
        setActionType(wf.action_type); setActionIntent(wf.action_config?.instruction || "");
        setExecutionMode(wf.execution_mode as "reasoning" | "deterministic" || "reasoning");
        setParsedUiNodes(wf.ui_nodes || null); setParsedUiEdges(wf.ui_edges || null);
        setShowModal(true);
    };

    const applyTemplate = (tpl: typeof TEMPLATES[0]) => {
        setEditingWorkflow(null); setName(tpl.name); setDescription(tpl.description);
        setTriggerType(tpl.trigger_type); setTriggerConfig(tpl.trigger_config);
        setActionType(tpl.action_type); setActionIntent(tpl.action_config.instruction);
        setExecutionMode("reasoning"); setParsedUiNodes(null); setParsedUiEdges(null);
        setShowModal(true);
    };

    const handleAddParallelBranch = () => {
        const allNodes: any[] = parsedUiNodes || defaultEditorNodes;
        const allEdges: any[] = parsedUiEdges || defaultEditorEdges;
        const source = allNodes.find(n => n.type === "trigger") || allNodes[0];
        if (!source) return;

        const childIds = new Set(allEdges.filter(e => e.source === source.id).map(e => e.target));
        const siblings = allNodes.filter(n => childIds.has(n.id));
        const SPACING = 290;
        const sourceX: number = source.position?.x ?? 250;
        const branchY: number = (source.position?.y ?? 0) + 170;
        const totalBranches = siblings.length + 1;
        const startX = sourceX - ((totalBranches - 1) * SPACING) / 2;

        const branchId = `skill_branch_${Date.now()}`;
        const branchLabel = `Agente IA (rama ${String.fromCharCode(65 + siblings.length)})`;

        const rebuiltNodes = allNodes.map(n => {
            const idx = siblings.findIndex(s => s.id === n.id);
            if (idx >= 0) return { ...n, position: { x: startX + idx * SPACING, y: branchY } };
            return n;
        });
        rebuiltNodes.push({
            id: branchId, type: "skill",
            position: { x: startX + siblings.length * SPACING, y: branchY },
            data: { label: branchLabel, domain: "billing", instruction: "" },
        });

        const otherEdges = allEdges.filter(e => e.source !== source.id);
        const siblingEdges = siblings.map(s => ({ id: `e-${source.id}-${s.id}`, source: source.id, target: s.id }));
        const newEdge = { id: `e-${source.id}-${branchId}`, source: source.id, target: branchId };

        setParsedUiNodes(rebuiltNodes);
        setParsedUiEdges([...otherEdges, ...siblingEdges, newEdge]);
        setGraphKey(k => k + 1);
    };

    // ─── Render ──────────────────────────────────────────────────────────────

    return (
        <div className="min-h-screen bg-[#09090b] text-white p-8">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-10">
                <div>
                    <h1 className="text-3xl font-light text-white flex items-center gap-3">
                        <div className="p-2 bg-indigo-500/10 rounded-xl relative">
                            <div className="absolute inset-0 bg-indigo-500/20 rounded-xl blur-xl" />
                            <Zap className="w-8 h-8 text-indigo-400 relative z-10" />
                        </div>
                        Motor de Automatizaciones
                    </h1>
                    <p className="text-zinc-400 mt-2 ml-14 text-sm max-w-2xl">
                        Define reglas y triggers para que tus Agentes de IA operen la empresa de forma autónoma.
                    </p>
                </div>
                <button onClick={() => setShowModal(true)}
                    className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2.5 rounded-full font-medium transition-all shadow-lg shadow-indigo-500/20">
                    <Plus className="w-4 h-4" /> Nueva Regla
                </button>
            </div>

            <InfoBanner id="automatizaciones-intro" title="¿Qué es una automatización?">
                <p>
                    Una automatización es una regla persistente: &quot;cada vez que pase X, haz Y&quot;.
                    Se ejecuta sola, sin que intervengas.
                    Ejemplo: <span className="text-indigo-300">&quot;Cada día 1 del mes, genera las nóminas de todos los empleados.&quot;</span>
                </p>
                <p className="mt-1">
                    <a href="/tareas" className="text-indigo-400 hover:text-indigo-300 underline underline-offset-2 transition">
                        ¿Solo necesitas algo puntual? Ir a Tareas →
                    </a>
                </p>
            </InfoBanner>

            {/* AI Generator Bar */}
            <div className="mb-10 bg-[#111113] border border-indigo-500/30 rounded-2xl p-6 relative overflow-hidden shadow-lg shadow-indigo-500/5">
                <div className="absolute top-0 right-0 p-4 opacity-5 blur-xl pointer-events-none">
                    <BrainCircuit className="w-48 h-48 text-indigo-500" />
                </div>
                <div className="relative z-10 flex flex-col md:flex-row gap-4 items-center">
                    <div className="flex-shrink-0 flex items-center justify-center w-12 h-12 rounded-full bg-indigo-500/10 text-indigo-400">
                        <Sparkles className="w-6 h-6" />
                    </div>
                    <div className="flex-1 w-full">
                        <h3 className="text-sm font-semibold text-white mb-2">Crear mediante Inteligencia Artificial</h3>
                        <div className="flex bg-[#09090b] border border-zinc-800 rounded-xl overflow-hidden focus-within:border-indigo-500 transition-colors">
                            <input type="text" value={nlQuery} onChange={(e) => setNlQuery(e.target.value)}
                                onKeyDown={(e) => e.key === 'Enter' && handleParseAI()}
                                placeholder="Ej: Cada día 1 del mes, envíale las nóminas a todos mis empleados."
                                className="flex-1 bg-transparent border-none text-white text-sm px-4 py-3 focus:outline-none focus:ring-0 placeholder:text-zinc-600" />
                            <button onClick={handleParseAI} disabled={isParsing || !nlQuery.trim()}
                                className="px-5 bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm transition-colors disabled:opacity-50 flex items-center gap-2">
                                {isParsing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                                {isParsing ? "Analizando..." : "Generar Regla"}
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            {/* Grid */}
            {isLoading ? (
                <div className="flex justify-center items-center h-64">
                    <RotateCw className="w-8 h-8 text-indigo-500 animate-spin" />
                </div>
            ) : workflows.length === 0 ? (
                <div className="space-y-8">
                    <div className="flex flex-col items-center justify-center py-12 text-center">
                        <div className="bg-indigo-500/10 w-20 h-20 rounded-full flex items-center justify-center mb-6 border border-indigo-500/20 shadow-lg shadow-indigo-500/10">
                            <Zap className="w-10 h-10 text-indigo-400" />
                        </div>
                        <h3 className="text-xl font-bold text-white mb-2">Sin automatizaciones todavía</h3>
                        <p className="text-zinc-400 max-w-md mb-8 text-sm">
                            Crea reglas para que la IA opere tu empresa de forma autónoma. Puedes empezar con una plantilla o describir lo que necesitas.
                        </p>
                        <button onClick={() => { resetForm(); setShowModal(true); }}
                            className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-6 py-3 rounded-xl transition-all shadow-lg font-medium">
                            <Plus className="w-5 h-5" /> Crear desde cero
                        </button>
                    </div>
                    <div>
                        <p className="text-xs text-zinc-500 uppercase tracking-wider mb-4 text-center">O empieza con una plantilla</p>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            {TEMPLATES.map((tpl, i) => {
                                const Icon = tpl.icon;
                                return (
                                    <button key={i} onClick={() => applyTemplate(tpl)}
                                        className={`text-left p-5 rounded-2xl border bg-[#111113] hover:bg-[#141416] transition-all group ${tpl.border} hover:border-opacity-60`}>
                                        <div className={`w-10 h-10 rounded-xl ${tpl.bg} flex items-center justify-center mb-3 border ${tpl.border}`}>
                                            <Icon className={`w-5 h-5 ${tpl.color}`} />
                                        </div>
                                        <h4 className="text-sm font-semibold text-white mb-1">{tpl.name}</h4>
                                        <p className="text-xs text-zinc-500 line-clamp-2">{tpl.description}</p>
                                        <p className={`text-xs font-medium mt-3 ${tpl.color} flex items-center gap-1`}>
                                            <Sparkles className="w-3 h-3" /> Usar plantilla
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
                        <span className="text-xs text-zinc-600">Plantillas:</span>
                        {TEMPLATES.map((tpl, i) => {
                            const Icon = tpl.icon;
                            return (
                                <button key={i} onClick={() => applyTemplate(tpl)}
                                    className={`inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full border bg-[#111113] hover:bg-[#141416] transition-all ${tpl.border} ${tpl.color}`}>
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
                                onContextInputToggle={(id) => {
                                    if (contextInputId === id) { setContextInputId(null); setContextText(""); }
                                    else { setContextInputId(id); setContextText(""); }
                                }}
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
    );
}
