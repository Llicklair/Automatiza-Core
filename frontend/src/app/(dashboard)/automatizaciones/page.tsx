"use client";

import { useEffect, useState, useRef, useMemo } from "react";
import { api, Workflow, WorkflowExecution } from "@/lib/api";
import {
    Zap, Plus, Play, PlayCircle,
    Calendar, CheckCircle2, RotateCw, Loader2, X,
    AlertCircle, ChevronDown, ChevronUp, Activity,
    BrainCircuit, Sparkles, Send, Pause, Info, Cpu, GitFork,
    Clock, RefreshCw
} from "lucide-react";
import WorkflowGraph from "@/components/Workflows/WorkflowGraph";

const TRIGGER_CONFIG: Record<string, { label: string; icon: React.ElementType; cls: string; title: string }> = {
    event_based: {
        label: "Eventual",
        icon: Zap,
        cls: "text-amber-400 bg-amber-500/10 border-amber-500/20",
        title: "Se dispara cuando ocurre un evento en el ERP (factura creada, empleado modificado, etc.)",
    },
    schedule_based: {
        label: "De tiempo",
        icon: Clock,
        cls: "text-blue-400 bg-blue-500/10 border-blue-500/20",
        title: "Se ejecuta en una programación de tiempo definida (cron).",
    },
    manual: {
        label: "Constante",
        icon: RefreshCw,
        cls: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
        title: "Disponible en todo momento. Se lanza a demanda desde la UI o la API.",
    },
};

const EXEC_STATUS: Record<string, { label: string; cls: string }> = {
    running: { label: "Ejecutando", cls: "text-blue-400 bg-blue-500/10 border-blue-500/20" },
    completed: { label: "Completada", cls: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20" },
    success: { label: "Completada", cls: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20" },
    failed: { label: "Error", cls: "text-red-400 bg-red-500/10 border-red-500/20" },
    paused: { label: "Pausada", cls: "text-orange-400 bg-orange-500/10 border-orange-500/20" },
    pending: { label: "Pendiente", cls: "text-zinc-400 bg-zinc-800 border-zinc-700" },
};

export default function WorkflowsPage() {
    const [workflows, setWorkflows] = useState<Workflow[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [showModal, setShowModal] = useState(false);
    const [runningId, setRunningId] = useState<string | null>(null);
    const [toast, setToast] = useState<{ msg: string; type: "ok" | "err" } | null>(null);
    const [expandedId, setExpandedId] = useState<string | null>(null);
    const [executions, setExecutions] = useState<Record<string, WorkflowExecution[]>>({});
    const [loadingExec, setLoadingExec] = useState<string | null>(null);

    // Form
    const [name, setName] = useState("");
    const [description, setDescription] = useState("");
    const [triggerType, setTriggerType] = useState("event_based");
    const [actionType, setActionType] = useState("ai_task");
    const [actionIntent, setActionIntent] = useState("");
    const [triggerConfig, setTriggerConfig] = useState<any>({ events: ["any"] });

    // Execution mode
    const [executionMode, setExecutionMode] = useState<"reasoning" | "deterministic">("reasoning");

    // AI Parser
    const [nlQuery, setNlQuery] = useState("");
    const [isParsing, setIsParsing] = useState(false);
    const [parsedUiNodes, setParsedUiNodes] = useState<any[] | null>(null);
    const [parsedUiEdges, setParsedUiEdges] = useState<any[] | null>(null);

    // Live execution tracking
    const [liveExecId, setLiveExecId] = useState<string | null>(null);

    // Default nodes for the editor when creating from scratch
    const defaultEditorNodes = useMemo(() => [
        { id: "trigger_default", type: "trigger", position: { x: 250, y: 0 }, data: { label: "Trigger", trigger_type: triggerType } },
        { id: "skill_default", type: "skill", position: { x: 250, y: 130 }, data: { label: "Agente IA", domain: "billing", description: actionIntent } },
    ], [triggerType, actionIntent]);
    const defaultEditorEdges = useMemo(() => [
        { id: "e-trigger_default-skill_default", source: "trigger_default", target: "skill_default" },
    ], []);
    const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

    // Detects fan-out (parallel branches) in a set of ui_edges
    const hasFanOut = (edges: any[] | null | undefined): boolean => {
        if (!edges || edges.length === 0) return false;
        const counts: Record<string, number> = {};
        for (const e of edges) {
            const src = e.source;
            if (src) counts[src] = (counts[src] || 0) + 1;
        }
        return Object.values(counts).some(v => v >= 2);
    };

    // Adds a parallel branch fan-out to the parsed workflow preview
    const handleAddParallelBranch = () => {
        if (!parsedUiNodes || !parsedUiEdges) return;

        // Find the last non-trigger node to use as the fan-out source
        const nonTrigger = [...parsedUiNodes].reverse().find(n => n.type !== "trigger");
        if (!nonTrigger) return;

        const branchId = `parallel_branch_${Date.now()}`;
        const sourceNode = nonTrigger;
        const baseY = (sourceNode.position?.y ?? 150) + 130;
        const baseX = (sourceNode.position?.x ?? 250) + 180;

        const newNode = {
            id: branchId,
            type: "skill",
            position: { x: baseX, y: baseY },
            data: { label: "Agente IA (paralelo)", domain: "billing", description: "Rama paralela" },
        };
        const newEdge = {
            id: `e-${sourceNode.id}-${branchId}`,
            source: sourceNode.id,
            target: branchId,
        };

        setParsedUiNodes([...parsedUiNodes, newNode]);
        setParsedUiEdges([...parsedUiEdges, newEdge]);
    };

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

    const loadWorkflows = async () => {
        setIsLoading(true);
        try {
            setWorkflows(await api.workflows.list());
        } catch (e) { console.error(e); }
        finally { setIsLoading(false); }
    };

    const showToast = (msg: string, type: "ok" | "err") => {
        setToast({ msg, type });
        setTimeout(() => setToast(null), 5000);
    };

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsSubmitting(true);
        try {
            await api.workflows.create({
                name,
                description,
                trigger_type: triggerType,
                trigger_config: triggerConfig,
                action_type: actionType,
                action_config: { instruction: actionIntent },
                execution_mode: executionMode,
                ui_nodes: parsedUiNodes || defaultEditorNodes,
                ui_edges: parsedUiEdges || defaultEditorEdges,
            });
            setShowModal(false);
            resetForm();
            await loadWorkflows();
            showToast("Automatización creada correctamente", "ok");
        } catch (error: any) {
            showToast(error.message || "Error creando la regla", "err");
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleParseAI = async () => {
        if (!nlQuery.trim()) return;
        setIsParsing(true);
        try {
            const parsed = await api.workflows.parse(nlQuery);
            setName(parsed.name || "");
            setDescription(parsed.description || "");
            setTriggerType(parsed.trigger_type || "event_based");
            setTriggerConfig(parsed.trigger_config || { events: ["any"] });
            setActionType(parsed.action_type || "ai_task");
            setActionIntent(parsed.action_config?.instruction || "");
            setParsedUiNodes(parsed.ui_nodes || null);
            setParsedUiEdges(parsed.ui_edges || null);

            setNlQuery("");
            setShowModal(true);
            showToast("Borrador de regla creado por IA. Revisa y confirma.", "ok");
        } catch (e: any) {
            showToast("Error al procesar con IA: " + (e.message || "Fallo"), "err");
        } finally {
            setIsParsing(false);
        }
    };

    const handleDelete = async (id: string) => {
        try {
            await api.workflows.delete(id);
            setWorkflows(workflows.filter(w => w.id !== id));
            if (expandedId === id) { setExpandedId(null); setLiveExecId(null); }
            showToast("Automatización eliminada correctamente", "ok");
        } catch (e: any) {
            showToast(e.message || "Error al eliminar la automatización", "err");
        }
    };

    const handleRun = async (id: string) => {
        setRunningId(id);
        try {
            await api.workflows.run(id);
            showToast("Automatización lanzada. El agente IA está procesando la instrucción.", "ok");
            // Recargar ejecuciones si está expandida
            if (expandedId === id) await loadExecutions(id);
        } catch (error: any) {
            showToast(error.message || "Error al ejecutar", "err");
        } finally {
            setRunningId(null);
        }
    };

    const handleResume = async (workflowId: string, executionId: string) => {
        try {
            await api.workflows.resumeExecution(workflowId, executionId);
            showToast("Ejecución reanudada. El motor de nodos continúa procesando.", "ok");
            await loadExecutions(workflowId);
        } catch (error: any) {
            showToast(error.message || "Error al reanudar", "err");
        }
    };

    const toggleStatus = async (workflow: Workflow) => {
        try {
            const updated = await api.workflows.update(workflow.id, { is_active: !workflow.is_active });
            setWorkflows(workflows.map(w => w.id === updated.id ? updated : w));
        } catch (e) { console.error(e); }
    };

    const loadExecutions = async (id: string) => {
        setLoadingExec(id);
        try {
            const data = await api.workflows.executions(id);
            setExecutions(prev => ({ ...prev, [id]: data }));
        } catch (e) { console.error(e); }
        finally { setLoadingExec(null); }
    };

    const toggleExpand = async (id: string) => {
        if (expandedId === id) {
            setExpandedId(null);
            setLiveExecId(null);
        } else {
            setExpandedId(id);
            setLiveExecId(null);
            if (!executions[id]) await loadExecutions(id);
        }
    };

    const resetForm = () => {
        setName(""); setDescription(""); setTriggerType("event_based");
        setActionType("ai_task"); setActionIntent(""); setTriggerConfig({ events: ["any"] });
        setParsedUiNodes(null); setParsedUiEdges(null);
        setExecutionMode("reasoning");
    };

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
                <button
                    onClick={() => setShowModal(true)}
                    className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2.5 rounded-full font-medium transition-all shadow-lg shadow-indigo-500/20"
                >
                    <Plus className="w-4 h-4" /> Nueva Regla
                </button>
            </div>

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
                            <input
                                type="text"
                                value={nlQuery}
                                onChange={(e) => setNlQuery(e.target.value)}
                                onKeyDown={(e) => e.key === 'Enter' && handleParseAI()}
                                placeholder="Ej: Cada día 1 del mes, envíale las nóminas a todos mis empleados."
                                className="flex-1 bg-transparent border-none text-white text-sm px-4 py-3 focus:outline-none focus:ring-0 placeholder:text-zinc-600"
                            />
                            <button
                                onClick={handleParseAI}
                                disabled={isParsing || !nlQuery.trim()}
                                className="px-5 bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm transition-colors disabled:opacity-50 flex items-center gap-2"
                            >
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
                <div className="flex flex-col items-center justify-center h-96 border border-dashed border-zinc-800 rounded-3xl bg-zinc-900/50">
                    <div className="p-4 bg-zinc-800/50 rounded-full mb-4">
                        <Zap className="w-10 h-10 text-zinc-500" />
                    </div>
                    <h3 className="text-xl font-medium text-white mb-2">No hay automatizaciones activas</h3>
                    <p className="text-zinc-400 mb-6 text-center max-w-sm text-sm">
                        Agrega reglas para que la IA escuche eventos ERP y actúe por ti.
                    </p>
                    <button onClick={() => setShowModal(true)} className="text-indigo-400 hover:text-indigo-300 font-medium text-sm">
                        Crear la primera regla
                    </button>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6 items-start">
                    {workflows.map((wf) => {
                        const isExpanded = expandedId === wf.id;
                        const wfExecs = executions[wf.id] || [];
                        const activeExec = wfExecs.find(e => e.status === "running" || e.status === "paused");
                        const lastExec = wfExecs[0];

                        // Construir capas de nodos para el mapa visual
                        const nodeLayers: any[][] = (() => {
                            if (wf.ui_nodes && wf.ui_nodes.length > 0) {
                                const sorted = [...wf.ui_nodes].sort((a: any, b: any) => (a.position?.y ?? 0) - (b.position?.y ?? 0));
                                const layers: any[][] = [];
                                let current: any[] = [];
                                let lastY = -9999;
                                for (const nd of sorted) {
                                    const y = nd.position?.y ?? 0;
                                    if (y - lastY > 60 && current.length > 0) { layers.push(current); current = []; }
                                    current.push(nd);
                                    lastY = y;
                                }
                                if (current.length > 0) layers.push(current);
                                return layers;
                            }
                            const triggerDesc = wf.trigger_config?.events
                                ? `Evento: ${(wf.trigger_config.events as string[]).join(", ")}`
                                : wf.trigger_config?.cron
                                    ? `Cron: ${wf.trigger_config.cron}`
                                    : "Inicio de la automatización";
                            return [
                                [{ id: "trigger", type: "trigger", data: { label: TRIGGER_CONFIG[wf.trigger_type]?.label ?? wf.trigger_type, description: triggerDesc } }],
                                [{ id: "agent", type: "skill", data: { label: "Agente IA", description: wf.action_config?.instruction || "Ejecutar automatización" } }],
                            ];
                        })();

                        return (
                            <div key={wf.id} className="bg-[#111113] border border-zinc-800 rounded-2xl overflow-hidden hover:border-indigo-500/30 transition-all group relative flex flex-col">
                                <div className="absolute -top-16 -right-16 w-32 h-32 bg-indigo-500/10 rounded-full blur-3xl group-hover:bg-indigo-500/15 transition-all pointer-events-none" />

                                {/* ── Cabecera de la automatización ─────────────────── */}
                                <div className="px-5 pt-4 pb-3 relative z-10">
                                    <div className="flex items-start justify-between gap-2 mb-2">
                                        <div className="flex-1 min-w-0">
                                            <h3 className="text-sm font-semibold text-white truncate leading-tight">{wf.name}</h3>
                                            {wf.description && (
                                                <p className="text-[11px] text-zinc-500 mt-0.5 line-clamp-1">{wf.description}</p>
                                            )}
                                        </div>
                                        <div className="flex items-center gap-1.5 flex-shrink-0 mt-0.5">
                                            {lastExec && (
                                                <span className={`text-[10px] px-1.5 py-0.5 rounded border font-medium ${(EXEC_STATUS[lastExec.status] ?? EXEC_STATUS.pending).cls}`}>
                                                    {(EXEC_STATUS[lastExec.status] ?? EXEC_STATUS.pending).label}
                                                </span>
                                            )}
                                            <button
                                                onClick={() => handleRun(wf.id)}
                                                disabled={runningId === wf.id || !wf.is_active}
                                                className="p-1.5 text-zinc-400 hover:text-emerald-400 bg-zinc-800/50 hover:bg-emerald-400/10 rounded-lg transition-colors disabled:opacity-40"
                                                title="Ejecutar ahora"
                                            >
                                                {runningId === wf.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <PlayCircle className="w-4 h-4" />}
                                            </button>
                                            <button
                                                onClick={() => handleDelete(wf.id)}
                                                className="p-1.5 text-zinc-400 hover:text-red-400 bg-zinc-800/50 hover:bg-red-400/10 rounded-lg transition-colors"
                                                title="Eliminar automatización"
                                            >
                                                <X className="w-4 h-4" />
                                            </button>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <button
                                            onClick={() => toggleStatus(wf)}
                                            className={`w-8 h-4 rounded-full transition-colors flex items-center px-0.5 flex-shrink-0 ${wf.is_active ? "bg-indigo-600" : "bg-zinc-700"}`}
                                            title={wf.is_active ? "Desactivar" : "Activar"}
                                        >
                                            <div className={`w-3 h-3 rounded-full bg-white transition-transform ${wf.is_active ? "translate-x-4" : "translate-x-0"}`} />
                                        </button>
                                        <span className={`text-[11px] ${wf.is_active ? "text-indigo-400" : "text-zinc-500"}`}>
                                            {wf.is_active ? "Activa" : "Pausada"}
                                        </span>
                                        <span className="text-zinc-700">·</span>
                                        {(() => {
                                            const tc = TRIGGER_CONFIG[wf.trigger_type];
                                            if (!tc) return <span className="text-[11px] text-zinc-500">{wf.trigger_type}</span>;
                                            const TIcon = tc.icon;
                                            return (
                                                <span
                                                    className={`flex items-center gap-0.5 text-[10px] px-1.5 py-0.5 rounded-full border font-semibold ${tc.cls}`}
                                                    title={tc.title}
                                                >
                                                    <TIcon className="w-2.5 h-2.5" />
                                                    {tc.label}
                                                </span>
                                            );
                                        })()}
                                        <span className="text-zinc-700">·</span>
                                        {wf.execution_mode === "deterministic" ? (
                                            <span
                                                className="flex items-center gap-0.5 text-[10px] px-1.5 py-0.5 rounded-full border font-semibold text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
                                                title="Los pasos están precompilados. Se ejecutan sin LLM, con coste cero y velocidad máxima."
                                            >
                                                <Cpu className="w-2.5 h-2.5" />
                                                Determinista
                                            </span>
                                        ) : (
                                            <span
                                                className="flex items-center gap-0.5 text-[10px] px-1.5 py-0.5 rounded-full border font-semibold text-blue-400 bg-blue-500/10 border-blue-500/20"
                                                title="El orquestador LLM interpreta la instrucción en tiempo real en cada ejecución."
                                            >
                                                <BrainCircuit className="w-2.5 h-2.5" />
                                                Con IA
                                            </span>
                                        )}
                                        {hasFanOut(wf.ui_edges) && (
                                            <>
                                                <span className="text-zinc-700">·</span>
                                                <span
                                                    className="flex items-center gap-0.5 text-[10px] px-1.5 py-0.5 rounded-full border font-semibold text-violet-400 bg-violet-500/10 border-violet-500/20"
                                                    title="Este workflow ejecuta ramas en paralelo mediante asyncio.gather"
                                                >
                                                    <GitFork className="w-2.5 h-2.5" />
                                                    Paralelo
                                                </span>
                                            </>
                                        )}
                                        {activeExec && (
                                            <>
                                                <span className="text-zinc-700">·</span>
                                                <span className="flex items-center gap-1 text-[11px] text-blue-400">
                                                    <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
                                                    {activeExec.status === "paused" ? "Pausada" : "Ejecutando"}
                                                </span>
                                            </>
                                        )}
                                    </div>
                                </div>

                                {/* ── Mapa de nodos con hilos ───────────────────────── */}
                                <div className="px-5 pb-5 pt-1 border-t border-zinc-800/50 space-y-0">
                                    {nodeLayers.map((layer, layerIdx) => {
                                        const prevLayer = nodeLayers[layerIdx - 1];
                                        const prevCompleted = prevLayer?.every((n: any) =>
                                            activeExec?.node_states?.[n.id]?.status === "completed"
                                        );

                                        return (
                                            <div key={layerIdx}>
                                                {/* Hilo conector entre capas */}
                                                {layerIdx > 0 && (
                                                    <div className="flex justify-center items-center py-0" style={{ height: 28 }}>
                                                        <div className="flex flex-col items-center">
                                                            <div className={`w-px h-3 ${prevCompleted ? "bg-emerald-600/70" : "bg-zinc-700"}`} />
                                                            <div className={`w-2 h-2 rounded-full border-2 ${prevCompleted ? "border-emerald-600 bg-emerald-600/30" : "border-zinc-600 bg-zinc-800"}`} />
                                                            <div className={`w-px h-3 ${prevCompleted ? "bg-emerald-600/70" : "bg-zinc-700"}`} />
                                                        </div>
                                                    </div>
                                                )}

                                                {/* Nodos de esta capa */}
                                                <div className={`flex gap-2 ${layerIdx === 0 ? "mt-3" : ""}`}>
                                                    {layer.map((node: any) => {
                                                        const ns = activeExec?.node_states?.[node.id];
                                                        const status = ns?.status;
                                                        const isCurrentNode = activeExec?.current_node_id === node.id;
                                                        const isRunning = status === "running" || isCurrentNode;
                                                        const isDone = status === "completed";
                                                        const isFailed = status === "failed";
                                                        const isPausedNode = status === "paused";
                                                        const isTrigger = node.type === "trigger";

                                                        const cardBorder = isRunning ? "border-blue-500/50"
                                                            : isDone ? "border-emerald-500/30"
                                                            : isFailed ? "border-red-500/40"
                                                            : isPausedNode ? "border-orange-500/40"
                                                            : isTrigger ? "border-indigo-500/20"
                                                            : "border-zinc-800";

                                                        const cardBg = isRunning ? "bg-blue-500/[0.04]"
                                                            : isDone ? "bg-emerald-500/[0.03]"
                                                            : "bg-[#0c0c0e]";

                                                        const iconCls = isTrigger ? "bg-indigo-500/10 text-indigo-400"
                                                            : isRunning ? "bg-blue-500/10 text-blue-400"
                                                            : isDone ? "bg-emerald-500/10 text-emerald-400"
                                                            : isFailed ? "bg-red-500/10 text-red-400"
                                                            : isPausedNode ? "bg-orange-500/10 text-orange-400"
                                                            : "bg-zinc-800/70 text-zinc-400";

                                                        const TriggerIcon = TRIGGER_CONFIG[wf.trigger_type]?.icon ?? Zap;
                                                        const Icon = isTrigger ? TriggerIcon : BrainCircuit;

                                                        const description = node.data?.description
                                                            || node.data?.action
                                                            || (isTrigger ? "Escuchando evento..." : "Procesando...");

                                                        return (
                                                            <div
                                                                key={node.id}
                                                                className={`flex-1 rounded-xl px-3 py-2.5 border ${cardBorder} ${cardBg} relative overflow-hidden transition-all`}
                                                            >
                                                                {isRunning && (
                                                                    <div className="absolute inset-0 animate-pulse bg-blue-500/[0.06] pointer-events-none" />
                                                                )}
                                                                <div className="flex items-start gap-2.5 relative">
                                                                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5 ${iconCls}`}>
                                                                        <Icon className="w-3.5 h-3.5" />
                                                                    </div>
                                                                    <div className="flex-1 min-w-0">
                                                                        <div className="flex items-center justify-between gap-1 mb-0.5">
                                                                            <span className="text-xs font-semibold text-white leading-tight truncate">
                                                                                {node.data?.label || node.type}
                                                                            </span>
                                                                            {status && (
                                                                                <span className={`text-[9px] font-semibold flex-shrink-0 ${isRunning ? "text-blue-400"
                                                                                    : isDone ? "text-emerald-400"
                                                                                    : isFailed ? "text-red-400"
                                                                                    : isPausedNode ? "text-orange-400" : "text-zinc-500"
                                                                                    }`}>
                                                                                    {isRunning ? "Ejecutando" : isDone ? "Completado" : isFailed ? "Error" : isPausedNode ? "Pausado" : status}
                                                                                </span>
                                                                            )}
                                                                        </div>
                                                                        <p className="text-[11px] text-zinc-500 leading-snug line-clamp-2">
                                                                            {description}
                                                                        </p>
                                                                    </div>
                                                                </div>
                                                            </div>
                                                        );
                                                    })}
                                                </div>
                                            </div>
                                        );
                                    })}

                                    {/* Botón reanudar si está pausada */}
                                    {activeExec?.status === "paused" && (
                                        <div className="mt-3 flex justify-center">
                                            <button
                                                onClick={() => handleResume(wf.id, activeExec.id)}
                                                className="flex items-center gap-1.5 px-4 py-1.5 bg-orange-500/10 hover:bg-orange-500/20 text-orange-400 rounded-full text-xs font-semibold transition-colors border border-orange-500/20"
                                            >
                                                <Pause className="w-3 h-3" /> Reanudar ejecución
                                            </button>
                                        </div>
                                    )}
                                </div>

                                {/* ── Toggle historial ──────────────────────────── */}
                                <button
                                    onClick={() => toggleExpand(wf.id)}
                                    className="w-full flex items-center justify-between px-5 py-2.5 border-t border-zinc-800/60 hover:bg-white/[0.02] transition text-xs text-zinc-500 hover:text-zinc-300 mt-auto"
                                >
                                    <span className="flex items-center gap-1.5">
                                        <Activity className="w-3.5 h-3.5" />
                                        Historial de ejecuciones
                                        {wfExecs.length > 0 && (
                                            <span className="bg-zinc-800 text-zinc-400 rounded-full px-1.5 py-0.5 text-[10px] font-medium">
                                                {wfExecs.length}
                                            </span>
                                        )}
                                    </span>
                                    {loadingExec === wf.id
                                        ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                        : isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />
                                    }
                                </button>

                                {/* ── Historial expandible ──────────────────────── */}
                                {isExpanded && (
                                    <div className="border-t border-zinc-800/60 bg-[#0d0d0f] max-h-64 overflow-y-auto">
                                        <div className="px-5 py-3 border-b border-zinc-800/50 bg-[#111113] flex justify-between items-center sticky top-0 z-10">
                                            <h4 className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider">Últimas Ejecuciones</h4>
                                            <button onClick={() => loadExecutions(wf.id)} className="text-[11px] text-zinc-500 hover:text-zinc-300 flex items-center gap-1 transition">
                                                <RotateCw className="w-3 h-3" /> Actualizar
                                            </button>
                                        </div>
                                        {wfExecs.length === 0 ? (
                                            <div className="py-8 text-center text-xs text-zinc-600 flex flex-col items-center justify-center">
                                                <Activity className="w-6 h-6 mb-2 text-zinc-800" />
                                                Sin ejecuciones registradas.
                                            </div>
                                        ) : (
                                            <div className="divide-y divide-zinc-800/50">
                                                {wfExecs.slice(0, 10).map(ex => {
                                                    const st = EXEC_STATUS[ex.status] ?? { label: ex.status, cls: "text-zinc-400 bg-zinc-800 border-zinc-700" };
                                                    return (
                                                        <div key={ex.id} className="px-5 py-3 hover:bg-white/[0.01] transition-colors">
                                                            <div className="flex items-center justify-between mb-1">
                                                                <div className="flex items-center gap-2">
                                                                    <span className={`text-[10px] px-1.5 py-0.5 rounded border font-semibold ${st.cls}`}>
                                                                        {st.label}
                                                                    </span>
                                                                    {ex.status === "paused" && (
                                                                        <button
                                                                            onClick={() => handleResume(wf.id, ex.id)}
                                                                            className="text-[9px] text-orange-400 bg-orange-500/10 hover:bg-orange-500/20 px-1.5 py-0.5 rounded font-semibold transition-colors"
                                                                        >
                                                                            Reanudar
                                                                        </button>
                                                                    )}
                                                                </div>
                                                                <span className="text-[10px] text-zinc-500 font-mono">
                                                                    {new Date(ex.started_at).toLocaleString("es-ES", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })}
                                                                </span>
                                                            </div>
                                                            {ex.result_log && (
                                                                <p className="text-[11px] text-zinc-400 font-mono leading-relaxed line-clamp-2">{ex.result_log}</p>
                                                            )}
                                                        </div>
                                                    );
                                                })}
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        );
                    })}
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

            {/* Modal creación */}
            {showModal && (
                <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                    <div className="bg-[#111113] border border-zinc-800 rounded-2xl w-full max-w-3xl overflow-hidden shadow-2xl max-h-[90vh] overflow-y-auto">
                        <div className="p-6 border-b border-zinc-800 flex justify-between items-center">
                            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                                <Zap className="w-5 h-5 text-indigo-400" /> Nueva Regla de Automatización
                            </h2>
                            <button onClick={() => setShowModal(false)} className="text-zinc-400 hover:text-white transition">
                                <X className="w-5 h-5" />
                            </button>
                        </div>
                        <form onSubmit={handleCreate} className="p-6 space-y-4">
                            <div>
                                <label className="block text-xs text-zinc-400 mb-1.5 uppercase tracking-wider">Nombre de la regla *</label>
                                <input required type="text" value={name} onChange={e => setName(e.target.value)}
                                    placeholder="Ej: Alerta facturas vencidas"
                                    className="w-full bg-[#09090b] border border-zinc-800 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-indigo-500 transition" />
                            </div>
                            <div>
                                <label className="block text-xs text-zinc-400 mb-1.5 uppercase tracking-wider">Descripción</label>
                                <textarea value={description} onChange={e => setDescription(e.target.value)}
                                    placeholder="¿Qué hace esta regla?"
                                    className="w-full bg-[#09090b] border border-zinc-800 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-indigo-500 transition resize-none h-16" />
                            </div>
                            <div className="grid grid-cols-2 gap-4 pt-3 border-t border-zinc-800/50">
                                <div>
                                    <label className="block text-xs font-semibold text-indigo-400 mb-1.5 uppercase tracking-wider">Trigger (Cuándo)</label>
                                    <select value={triggerType} onChange={e => setTriggerType(e.target.value)}
                                        className="w-full bg-[#09090b] border border-zinc-800 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-indigo-500">
                                        <option value="event_based">⚡ Eventual — Al ocurrir un Evento ERP</option>
                                        <option value="schedule_based">🕐 De tiempo — Programación (Cron)</option>
                                        <option value="manual">🔄 Constante — A Demanda</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-xs font-semibold text-emerald-400 mb-1.5 uppercase tracking-wider">Acción (Qué)</label>
                                    <select value={actionType} onChange={e => setActionType(e.target.value)}
                                        className="w-full bg-[#09090b] border border-zinc-800 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-emerald-500">
                                        <option value="ai_task">Lanzar Agente IA</option>
                                        <option value="notify">Notificación</option>
                                        <option value="webhook">Llamar Webhook</option>
                                    </select>
                                </div>
                            </div>

                            {triggerType !== "manual" && (
                                <div>
                                    <label className="block text-xs text-zinc-400 mb-1.5 uppercase tracking-wider">Configuración del Trigger</label>
                                    <input type="text"
                                        value={triggerType === 'schedule_based' ? (triggerConfig.cron || "") : (triggerConfig.events ? triggerConfig.events.join(", ") : "")}
                                        onChange={e => {
                                            const val = e.target.value;
                                            if (triggerType === 'schedule_based') {
                                                setTriggerConfig({ cron: val });
                                            } else {
                                                setTriggerConfig({ events: val.split(",").map(v => v.trim()).filter(Boolean) });
                                            }
                                        }}
                                        placeholder={triggerType === 'schedule_based' ? "Ej: 0 9 * * 1 (Cada Lunes a las 9)" : "Ej: invoice_created, invoice_paid"}
                                        className="w-full bg-[#09090b] border border-zinc-800 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-indigo-500 transition"
                                    />
                                    <p className="text-[10px] text-zinc-500 mt-1">
                                        {triggerType === 'schedule_based' ? 'Expresión CRON' : 'Eventos separados por coma (ej: invoice_paid)'}
                                    </p>
                                </div>
                            )}

                            <div>
                                <label className="block text-xs text-zinc-400 mb-1.5 uppercase tracking-wider">
                                    Instrucción para el Agente IA *
                                    <span className="text-zinc-600 ml-1 normal-case">(en lenguaje natural)</span>
                                </label>
                                <textarea required rows={3} value={actionIntent} onChange={e => setActionIntent(e.target.value)}
                                    placeholder="Ej: Revisa todas las facturas con más de 30 días sin pagar y genera un recordatorio para cada cliente con el importe pendiente"
                                    className="w-full bg-[#09090b] border border-zinc-800 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-emerald-500 transition resize-none" />
                            </div>

                            {/* Execution mode selector */}
                            <div className="pt-3 border-t border-zinc-800/50">
                                <label className="block text-xs text-zinc-400 mb-2 uppercase tracking-wider">Modo de ejecución</label>
                                <div className="grid grid-cols-2 gap-3">
                                    <button
                                        type="button"
                                        onClick={() => setExecutionMode("reasoning")}
                                        className={`flex flex-col items-start gap-1 rounded-xl px-4 py-3 border text-left transition-all ${executionMode === "reasoning"
                                            ? "border-blue-500/50 bg-blue-500/10 text-blue-300"
                                            : "border-zinc-800 bg-[#09090b] text-zinc-400 hover:border-zinc-700"}`}
                                    >
                                        <div className="flex items-center gap-2">
                                            <BrainCircuit className="w-4 h-4" />
                                            <span className="text-xs font-semibold">Con IA</span>
                                        </div>
                                        <p className="text-[10px] leading-snug opacity-70">
                                            El LLM interpreta la instrucción en tiempo real. Flexible y adaptable, pero consume tokens en cada ejecución.
                                        </p>
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => setExecutionMode("deterministic")}
                                        className={`flex flex-col items-start gap-1 rounded-xl px-4 py-3 border text-left transition-all ${executionMode === "deterministic"
                                            ? "border-emerald-500/50 bg-emerald-500/10 text-emerald-300"
                                            : "border-zinc-800 bg-[#09090b] text-zinc-400 hover:border-zinc-700"}`}
                                    >
                                        <div className="flex items-center gap-2">
                                            <Cpu className="w-4 h-4" />
                                            <span className="text-xs font-semibold">Determinista</span>
                                        </div>
                                        <p className="text-[10px] leading-snug opacity-70">
                                            Los pasos se compilan una vez al crear la regla. Ejecución directa sin LLM: coste cero y máxima velocidad.
                                        </p>
                                    </button>
                                </div>
                                {executionMode === "deterministic" && (
                                    <div className="mt-2 flex items-start gap-2 bg-emerald-500/5 border border-emerald-500/15 rounded-lg px-3 py-2">
                                        <Info className="w-3.5 h-3.5 text-emerald-400 mt-0.5 flex-shrink-0" />
                                        <p className="text-[10px] text-emerald-300/80 leading-relaxed">
                                            Al guardar, se realizará una llamada extra al LLM para precompilar los pasos exactos. A partir de entonces, cada ejecución es instantánea y sin coste de IA.
                                        </p>
                                    </div>
                                )}
                            </div>

                            {/* Editor visual de nodos */}
                            <div className="pt-3 border-t border-zinc-800/50">
                                <div className="flex items-center justify-between mb-2">
                                    <p className="text-[10px] text-zinc-500 uppercase tracking-wider flex items-center gap-1.5">
                                        <BrainCircuit className="w-3 h-3 text-indigo-400" /> Editor visual de agentes
                                    </p>
                                    <div className="flex items-center gap-2">
                                        {hasFanOut(parsedUiEdges) && (
                                            <span className="flex items-center gap-1 text-[9px] px-2 py-0.5 rounded-full border font-semibold text-violet-400 bg-violet-500/10 border-violet-500/20">
                                                <GitFork className="w-2.5 h-2.5" />
                                                Ejecución paralela
                                            </span>
                                        )}
                                        <button
                                            type="button"
                                            onClick={handleAddParallelBranch}
                                            className="flex items-center gap-1 text-[9px] px-2 py-0.5 rounded-full border font-semibold text-violet-300 bg-violet-500/10 border-violet-500/20 hover:bg-violet-500/20 transition-colors"
                                            title="Añade una rama paralela al último nodo del grafo"
                                        >
                                            <GitFork className="w-2.5 h-2.5" />
                                            Añadir rama paralela
                                        </button>
                                    </div>
                                </div>
                                <div className="h-72 rounded-xl overflow-hidden border border-zinc-800">
                                    <WorkflowGraph
                                        nodes={parsedUiNodes || defaultEditorNodes}
                                        edges={parsedUiEdges || defaultEditorEdges}
                                        editable
                                        onNodesChange={(n) => setParsedUiNodes(n)}
                                        onEdgesChange={(e) => setParsedUiEdges(e)}
                                    />
                                </div>
                            </div>
                            <div className="pt-4 flex justify-end gap-3 border-t border-zinc-800/50">
                                <button type="button" onClick={() => setShowModal(false)} className="px-5 py-2.5 text-zinc-400 hover:text-white transition text-sm">Cancelar</button>
                                <button type="submit" disabled={isSubmitting}
                                    className="bg-indigo-600 hover:bg-indigo-500 text-white px-6 py-2.5 rounded-lg font-medium text-sm transition disabled:opacity-50 flex items-center gap-2">
                                    {isSubmitting && <Loader2 className="w-4 h-4 animate-spin" />}
                                    {isSubmitting ? "Guardando..." : "Crear Regla"}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
