"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { api, Workflow } from "@/lib/api";
import type { AIEmployee } from "@/lib/api/ai_employees";
import { logError } from "@/lib/logger";
import { TEMPLATES } from "../_components/constants";
import type { TriggerConfig, FlowNode, FlowEdge, ParsedWorkflow } from "./useAutomatizaciones";

interface AgentResult {
    output?: { response?: string };
    [key: string]: unknown;
}

// Detección ligera de dominio a partir del action_intent.
// Espejo reducido del _KEYWORD_MAP del backend (classifier.py): si una palabra
// clave aparece en el intent, asignamos ese dominio y etiqueta visible al nodo
// skill por defecto. Sin match → fallback genérico.
const DOMAIN_HINTS: ReadonlyArray<{ domain: string; label: string; keys: string[] }> = [
    { domain: "compliance",  label: "Compliance",   keys: ["modelo 303", "modelo 130", "modelo 111", "modelo 200", "modelo 390", "aeat", "hacienda", "impuesto", "fiscal"] },
    { domain: "hr",          label: "RRHH",         keys: ["nómina", "nóminas", "empleado", "vacaciones", "salario", "sueldo", "baja médica", "contrato laboral"] },
    { domain: "banking",     label: "Banca",        keys: ["saldo", "banco", "transacción", "transferencia", "iban", "extracto bancario", "psd2", "concilia"] },
    { domain: "marketing",   label: "Marketing",    keys: ["redes sociales", "instagram", "facebook", "linkedin", "post", "hashtag", "campaña", "contenido", "social media"] },
    { domain: "recruitment", label: "Reclutamiento",keys: ["candidato", "currículum", "curriculum", "vacante", "shortlist", "selección de personal", "entrevista"] },
    { domain: "rag",         label: "Base de conocimiento", keys: ["qué dice", "qué tenemos sobre", "según el documento", "según los documentos", "según la política", "consultar la documentación"] },
    { domain: "documents",   label: "Documentos",   keys: ["documento", "pdf", "contrato", "subir", "clasificar", "escanear", "analizar"] },
    { domain: "excel",       label: "Excel",        keys: ["excel", "csv", "hoja de cálculo", "cruzar", "exportar listado"] },
    { domain: "email",       label: "Correo",       keys: ["correo electrónico", "bandeja de entrada", "buzón", "inbox", "envía un email", "envía un correo", "responde el correo"] },
    { domain: "report",      label: "Informe",      keys: ["informe mensual", "snapshot", "resumen mensual", "cierre mensual", "informe de gestión"] },
    { domain: "crm",         label: "CRM",          keys: ["lead", "oportunidad", "cliente potencial", "embudo", "trato", "venta", "alta de cliente"] },
    { domain: "billing",     label: "Facturación",  keys: ["factura", "facturas", "facturar", "cobro", "presupuesto", "albarán", "iva"] },
];

function detectDomainFromIntent(intent: string): { domain: string; label: string } {
    const t = (intent || "").toLowerCase();
    for (const h of DOMAIN_HINTS) {
        if (h.keys.some((k) => t.includes(k))) return { domain: h.domain, label: h.label };
    }
    return { domain: "billing", label: "Agente IA" };
}

// Para un dominio dado, elige el mejor empleado disponible: prefiere custom
// (no built-in) sobre built-in. Devuelve la asignación que se inyectará al
// nodo skill: domain + label visible + employee_id (siempre que haya un AIEmployee
// real, sea built-in o custom — uniforma el tracking en activity_feed).
function pickEmployeeForDomain(
    domain: string,
    fallbackLabel: string,
    employees: AIEmployee[],
): { domain: string; label: string; employeeId?: string } {
    const candidates = employees.filter(
        (e) => e.domain === domain && e.status !== "blocked",
    );
    const custom = candidates.find((e) => !e.is_builtin);
    if (custom) {
        return { domain: "custom", label: custom.name, employeeId: custom.id };
    }
    const builtin = candidates.find((e) => e.is_builtin);
    if (builtin) {
        return { domain, label: builtin.name, employeeId: builtin.id };
    }
    return { domain, label: fallbackLabel };
}

const TRIGGER_LABELS: Record<string, string> = {
    event_based: "Evento",
    schedule_based: "Programación",
    manual: "Disparo manual",
};

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

    // Lista de AIEmployees del tenant (built-in + custom). Se carga una vez al
    // montar; se usa para etiquetar los nodos skill con el nombre real del
    // agente y, cuando hay un custom para el dominio detectado, asignarlo.
    const [employees, setEmployees] = useState<AIEmployee[]>([]);
    useEffect(() => {
        let cancelled = false;
        api.aiEmployees.list().then((list) => {
            if (!cancelled) setEmployees(list);
        }).catch((e) => logError("automatizaciones/employees", e));
        return () => { cancelled = true; };
    }, []);

    const detectAssignment = useCallback((intent: string) => {
        const hint = detectDomainFromIntent(intent);
        return pickEmployeeForDomain(hint.domain, hint.label, employees);
    }, [employees]);

    const defaultEditorNodes = useMemo(() => {
        const { domain, label, employeeId } = detectAssignment(actionIntent);
        const triggerLabel = TRIGGER_LABELS[triggerType] || "Trigger";
        const skillData: Record<string, unknown> = { label, domain, description: actionIntent };
        if (employeeId) skillData.employee_id = employeeId;
        return [
            { id: "trigger_default", type: "trigger", position: { x: 250, y: 0 }, data: { label: triggerLabel, trigger_type: triggerType } },
            { id: "skill_default", type: "skill", position: { x: 250, y: 130 }, data: skillData },
        ];
    }, [triggerType, actionIntent, detectAssignment]);

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
        // Trata array vacío como null para que el modal caiga al editor por
        // defecto en vez de mostrar un mapa de nodos en blanco.
        setParsedUiNodes((parsed.ui_nodes && parsed.ui_nodes.length > 0) ? parsed.ui_nodes : null);
        setParsedUiEdges((parsed.ui_edges && parsed.ui_edges.length > 0) ? parsed.ui_edges : null);
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
        const { domain: brDomain, label: brLabel, employeeId: brEmpId } = detectAssignment(actionIntent);
        const branchLabel = `${brLabel} (rama ${String.fromCharCode(65 + siblings.length)})`;

        const rebuiltNodes = allNodes.map(n => {
            const idx = siblings.findIndex(s => s.id === n.id);
            if (idx >= 0) return { ...n, position: { x: startX + idx * SPACING, y: branchY } };
            return n;
        });
        const branchData: Record<string, unknown> = { label: branchLabel, domain: brDomain, instruction: "" };
        if (brEmpId) branchData.employee_id = brEmpId;
        rebuiltNodes.push({
            id: branchId, type: "skill",
            position: { x: startX + siblings.length * SPACING, y: branchY },
            data: branchData,
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
