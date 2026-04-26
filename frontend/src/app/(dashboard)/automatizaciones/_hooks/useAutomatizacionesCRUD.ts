"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { api, Workflow } from "@/lib/api";
import { logError } from "@/lib/logger";
import { TEMPLATES } from "../_components/constants";
import type { TriggerConfig, FlowNode, FlowEdge, ParsedWorkflow } from "./useAutomatizaciones";

interface AgentResult {
    output?: { response?: string };
    [key: string]: unknown;
}

export function useAutomatizacionesCRUD() {
    const [workflows, setWorkflows] = useState<Workflow[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [showModal, setShowModal] = useState(false);
    const [editingWorkflow, setEditingWorkflow] = useState<Workflow | null>(null);
    const [toast, setToast] = useState<{ msg: string; type: "ok" | "err" } | null>(null);

    // Form state
    const [name, setName] = useState("");
    const [description, setDescription] = useState("");
    const [triggerType, setTriggerType] = useState("event_based");
    const [actionType, setActionType] = useState("ai_task");
    const [actionIntent, setActionIntent] = useState("");
    const [triggerConfig, setTriggerConfig] = useState<TriggerConfig>({ events: ["any"] });
    const [executionMode, setExecutionMode] = useState<"reasoning" | "deterministic">("reasoning");

    // AI Parser state
    const [nlQuery, setNlQuery] = useState("");
    const [isParsing, setIsParsing] = useState(false);
    const [parsedUiNodes, setParsedUiNodes] = useState<FlowNode[] | null>(null);
    const [parsedUiEdges, setParsedUiEdges] = useState<FlowEdge[] | null>(null);
    const [graphKey, setGraphKey] = useState(0);
    const [canBeDeterministic, setCanBeDeterministic] = useState<boolean | null>(null);
    const [modeLockedByAI, setModeLockedByAI] = useState(false);

    // Chat inline
    const [chatLoading, setChatLoading] = useState(false);
    const [chatResponse, setChatResponse] = useState<string | null>(null);

    const defaultEditorNodes = useMemo(() => [
        { id: "trigger_default", type: "trigger", position: { x: 250, y: 0 }, data: { label: "Trigger", trigger_type: triggerType } },
        { id: "skill_default", type: "skill", position: { x: 250, y: 130 }, data: { label: "Agente IA", domain: "billing", description: actionIntent } },
    ], [triggerType, actionIntent]);

    const defaultEditorEdges = useMemo(() => [
        { id: "e-trigger_default-skill_default", source: "trigger_default", target: "skill_default" },
    ], []);

    const showToast = (msg: string, type: "ok" | "err") => {
        setToast({ msg, type });
        setTimeout(() => setToast(null), 5000);
    };

    const resetForm = () => {
        setName(""); setDescription(""); setTriggerType("event_based");
        setActionType("ai_task"); setActionIntent("");
        setTriggerConfig({ events: ["any"] });
        setParsedUiNodes(null); setParsedUiEdges(null);
        setExecutionMode("reasoning"); setEditingWorkflow(null);
        setCanBeDeterministic(null); setModeLockedByAI(false);
    };

    const loadWorkflows = useCallback(async () => {
        setIsLoading(true);
        try { setWorkflows(await api.workflows.list()); }
        catch (e) { logError("automatizaciones/page", e); }
        finally { setIsLoading(false); }
    }, []);

    useEffect(() => { loadWorkflows(); }, [loadWorkflows]);

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
        } catch (error: unknown) {
            showToast(error instanceof Error ? error.message : "Error creando la regla", "err");
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
        } catch (error: unknown) {
            showToast(error instanceof Error ? error.message : "Error al actualizar", "err");
        } finally { setIsSubmitting(false); }
    };

    const handleDelete = async (id: string, expandedId: string | null, setExpandedId: (id: string | null) => void) => {
        try {
            await api.workflows.delete(id);
            setWorkflows(workflows.filter(w => w.id !== id));
            if (expandedId === id) { setExpandedId(null); }
            showToast("Automatización eliminada correctamente", "ok");
        } catch (e: unknown) { showToast(e instanceof Error ? e.message : "Error al eliminar la automatización", "err"); }
    };

    const toggleStatus = async (workflow: Workflow) => {
        try {
            const updated = await api.workflows.update(workflow.id, { is_active: !workflow.is_active });
            setWorkflows(workflows.map(w => w.id === updated.id ? updated : w));
        } catch (e) { logError("automatizaciones/page", e); }
    };

    const _isQuestion = (text: string): boolean => {
        const t = text.trim();
        const tl = t.toLowerCase();
        const workflowKeywords = [
            "cada ", "cada\n", "cuando ", "al ", "si ", "diariamente", "semanalmente",
            "mensualmente", "todos los", "todas las", "cada vez", "automáticamente",
            "en cuanto", "tras ", "después de", "antes de", "a las ", "a partir",
        ];
        if (workflowKeywords.some(k => tl.includes(k))) return false;
        if (t.startsWith("¿") || t.endsWith("?")) {
            const actionVerbs = ["crea", "genera", "envía", "haz", "registra", "sube", "programa"];
            return !actionVerbs.some(v => tl.includes(v));
        }
        const questionStarts = [
            "cuántas", "cuántos", "cuánto", "cuándo", "dónde", "cómo",
            "qué es", "qué son", "hay ", "tiene ", "está", "se ejecut",
            "terminó", "ha terminado", "funcionó", "falló",
            "explica", "diferencia", "ayuda", "hola", "buenas", "gracias",
        ];
        return questionStarts.some(q => tl.startsWith(q));
    };

    const _openModalWithParsed = (parsed: ParsedWorkflow) => {
        setName(parsed.name || ""); setDescription(parsed.description || "");
        setTriggerType(parsed.trigger_type || "event_based");
        setTriggerConfig(parsed.trigger_config || { events: ["any"] });
        setActionType(parsed.action_type || "ai_task");
        setActionIntent(parsed.action_config?.instruction || "");
        setParsedUiNodes(parsed.ui_nodes || null);
        setParsedUiEdges(parsed.ui_edges || null);
        setExecutionMode(parsed.can_be_deterministic ? "deterministic" : "reasoning");
        setCanBeDeterministic(parsed.can_be_deterministic ?? null);
        setModeLockedByAI(true);
        setShowModal(true);
    };

    const handleSmartInput = async () => {
        if (!nlQuery.trim()) return;
        if (_isQuestion(nlQuery)) {
            setChatLoading(true);
            setChatResponse(null);
            const question = nlQuery;
            setNlQuery("");
            try {
                const task = await api.tasks.create("chat", question, { context: "workflows" });
                const taskId = task.id;
                let found = false;
                for (let i = 0; i < 30; i++) {
                    await new Promise(r => setTimeout(r, 1000));
                    const updated = await api.tasks.get(taskId);
                    if (updated.status === "done" || updated.status === "failed") {
                        const results = updated.agent_results as AgentResult[] | undefined;
                        if (Array.isArray(results)) {
                            for (let j = results.length - 1; j >= 0; j--) {
                                if (results[j]?.output?.response) {
                                    setChatResponse(results[j].output!.response!);
                                    found = true;
                                    break;
                                }
                            }
                        }
                        if (!found) setChatResponse(updated.error_message || "No se obtuvo respuesta.");
                        break;
                    }
                }
            } catch (e: unknown) {
                setChatResponse(`Error: ${e instanceof Error ? e.message : "No se pudo procesar la pregunta"}`);
            } finally { setChatLoading(false); }
        } else {
            setIsParsing(true);
            try {
                const parsed = await api.workflows.parse(nlQuery);
                setNlQuery("");
                _openModalWithParsed(parsed);
            } catch (e: unknown) {
                showToast("Error al procesar con IA: " + (e instanceof Error ? e.message : "Fallo"), "err");
            } finally { setIsParsing(false); }
        }
    };

    const openEdit = (wf: Workflow) => {
        setEditingWorkflow(wf); setName(wf.name); setDescription(wf.description || "");
        setTriggerType(wf.trigger_type);
        setTriggerConfig((wf.trigger_config as TriggerConfig) || { events: ["any"] });
        setActionType(wf.action_type); setActionIntent(wf.action_config?.instruction || "");
        setExecutionMode(wf.execution_mode as "reasoning" | "deterministic" || "reasoning");
        setParsedUiNodes((wf.ui_nodes as FlowNode[]) || null);
        setParsedUiEdges((wf.ui_edges as FlowEdge[]) || null);
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
        const allNodes: FlowNode[] = parsedUiNodes || defaultEditorNodes;
        const allEdges: FlowEdge[] = parsedUiEdges || defaultEditorEdges;
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

    return {
        // State
        workflows, setWorkflows, isLoading, isSubmitting, showModal, setShowModal,
        editingWorkflow, toast, setToast,
        // Form
        name, setName, description, setDescription,
        triggerType, setTriggerType, actionType, setActionType,
        actionIntent, setActionIntent, triggerConfig, setTriggerConfig,
        executionMode, setExecutionMode,
        // AI Parser
        nlQuery, setNlQuery, isParsing,
        parsedUiNodes, setParsedUiNodes, parsedUiEdges, setParsedUiEdges,
        graphKey, canBeDeterministic, modeLockedByAI,
        // Chat
        chatLoading, chatResponse, setChatResponse,
        // Computed
        defaultEditorNodes, defaultEditorEdges,
        // Actions
        showToast, resetForm, loadWorkflows,
        handleCreate, handleEdit, handleDelete,
        toggleStatus, handleSmartInput,
        openEdit, applyTemplate, handleAddParallelBranch,
    };
}
