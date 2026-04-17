"use client";

import { useEffect } from "react";
import { useNavigationGuard } from "@/stores/navigationGuard";
import { useAutomatizacionesCRUD } from "./useAutomatizacionesCRUD";
import { useAutomatizacionesExecution } from "./useAutomatizacionesExecution";

// ─── Types (re-exported for consumers) ───────────────────────────────────────

export interface TriggerConfig {
    events?: string[];
    cron?: string;
    [key: string]: unknown;
}

export interface FlowNode {
    id: string;
    type: string;
    position: { x: number; y: number };
    data: Record<string, unknown>;
}

export interface FlowEdge {
    id: string;
    source: string;
    target: string;
}

export interface ParsedWorkflow {
    name?: string;
    description?: string;
    trigger_type?: string;
    trigger_config?: TriggerConfig;
    action_type?: string;
    action_config?: { instruction?: string };
    ui_nodes?: FlowNode[];
    ui_edges?: FlowEdge[];
    can_be_deterministic?: boolean;
}

// ─── Composed hook ────────────────────────────────────────────────────────────

export function useAutomatizaciones() {
    const crud = useAutomatizacionesCRUD();
    const execution = useAutomatizacionesExecution(crud.showToast);

    // Wrap handleDelete to inject expandedId/setExpandedId from execution
    const handleDelete = (id: string) =>
        crud.handleDelete(id, execution.expandedId, execution.setExpandedId);

    // ─── Navigation guard ────────────────────────────────────────────────────
    const setGuard = useNavigationGuard((s) => s.setGuard);
    useEffect(() => {
        const active =
            crud.showModal || crud.isParsing || crud.chatLoading ||
            crud.isSubmitting || execution.runningId !== null;
        setGuard(active, "Hay una automatización en curso. Si cambias de sección perderás el progreso.");
        return () => { if (active) setGuard(false); };
    }, [crud.showModal, crud.isParsing, crud.chatLoading, crud.isSubmitting, execution.runningId, setGuard]);

    return {
        // ── State ──
        workflows: crud.workflows,
        isLoading: crud.isLoading,
        isSubmitting: crud.isSubmitting,
        showModal: crud.showModal,
        setShowModal: crud.setShowModal,
        editingWorkflow: crud.editingWorkflow,
        runningId: execution.runningId,
        toast: crud.toast,
        setToast: crud.setToast,
        expandedId: execution.expandedId,
        executions: execution.executions,
        loadingExec: execution.loadingExec,
        refreshingExec: execution.refreshingExec,
        // ── Form ──
        name: crud.name, setName: crud.setName,
        description: crud.description, setDescription: crud.setDescription,
        triggerType: crud.triggerType, setTriggerType: crud.setTriggerType,
        actionType: crud.actionType, setActionType: crud.setActionType,
        actionIntent: crud.actionIntent, setActionIntent: crud.setActionIntent,
        triggerConfig: crud.triggerConfig, setTriggerConfig: crud.setTriggerConfig,
        executionMode: crud.executionMode, setExecutionMode: crud.setExecutionMode,
        // ── AI Parser ──
        nlQuery: crud.nlQuery, setNlQuery: crud.setNlQuery,
        isParsing: crud.isParsing,
        parsedUiNodes: crud.parsedUiNodes, setParsedUiNodes: crud.setParsedUiNodes,
        parsedUiEdges: crud.parsedUiEdges, setParsedUiEdges: crud.setParsedUiEdges,
        graphKey: crud.graphKey,
        canBeDeterministic: crud.canBeDeterministic,
        modeLockedByAI: crud.modeLockedByAI,
        // ── Context ──
        contextInputId: execution.contextInputId,
        contextText: execution.contextText,
        setContextText: execution.setContextText,
        // ── Chat ──
        chatLoading: crud.chatLoading,
        chatResponse: crud.chatResponse,
        setChatResponse: crud.setChatResponse,
        // ── Live logs ──
        liveLogs: execution.liveLogs,
        // ── Computed ──
        defaultEditorNodes: crud.defaultEditorNodes,
        defaultEditorEdges: crud.defaultEditorEdges,
        // ── Actions ──
        resetForm: crud.resetForm,
        handleCreate: crud.handleCreate,
        handleEdit: crud.handleEdit,
        handleSmartInput: crud.handleSmartInput,
        handleDelete,
        handleRun: execution.handleRun,
        handleRunWithContext: execution.handleRunWithContext,
        handleCancel: execution.handleCancel,
        handleResume: execution.handleResume,
        toggleStatus: crud.toggleStatus,
        refreshExecutions: execution.refreshExecutions,
        toggleExpand: execution.toggleExpand,
        openEdit: crud.openEdit,
        applyTemplate: crud.applyTemplate,
        handleAddParallelBranch: crud.handleAddParallelBranch,
        toggleContextInput: execution.toggleContextInput,
    };
}
