"use client";

import { useEffect, useState } from "react";
import { useNotificationSocket } from "@/lib/hooks/useNotificationSocket";

export type NodeStatus = "idle" | "running" | "completed" | "failed";

export interface NodeRuntimeState {
    nodeId: string;
    status: NodeStatus;
    startedAt?: number;     // ms epoch
    completedAt?: number;   // ms epoch
    elapsedMs?: number;     // calculado en vivo si running
    agent?: string;
    instruction?: string;
    label?: string;
    resultSummary?: string;
    error?: string;
}

/**
 * Suscripción a eventos WS de ejecución de workflow:
 *   - workflow_node_started   → marca node como running con startedAt.
 *   - workflow_node_completed → marca como completed con duración real.
 *   - workflow_node_failed    → marca como failed con error visible.
 *
 * `tick` interno fuerza re-render cada segundo para refrescar elapsedMs
 * mientras el nodo está running. Si executionId es null, el hook es no-op.
 */
export function useWorkflowExecution(executionId: string | null): Record<string, NodeRuntimeState> {
    const [nodes, setNodes] = useState<Record<string, NodeRuntimeState>>({});
    const [, setTick] = useState(0);

    // Reset al cambiar de execution
    useEffect(() => {
        setNodes({});
    }, [executionId]);

    // Tick cada segundo para refrescar elapsedMs de los nodos running.
    useEffect(() => {
        if (!executionId) return;
        const hasRunning = Object.values(nodes).some((n) => n.status === "running");
        if (!hasRunning) return;
        const id = setInterval(() => setTick((t) => t + 1), 1000);
        return () => clearInterval(id);
    }, [executionId, nodes]);

    useNotificationSocket({
        workflow_node_started: (msg) => {
            const msgExecId = msg.execution_id as string | undefined;
            if (!executionId || msgExecId !== executionId) return;
            const nodeId = msg.node_id as string;
            if (!nodeId) return;
            setNodes((prev) => ({
                ...prev,
                [nodeId]: {
                    nodeId,
                    status: "running",
                    startedAt: Date.now(),
                    agent: msg.agent as string | undefined,
                    instruction: msg.instruction as string | undefined,
                    label: msg.label as string | undefined,
                },
            }));
        },
        workflow_node_completed: (msg) => {
            const msgExecId = msg.execution_id as string | undefined;
            if (!executionId || msgExecId !== executionId) return;
            const nodeId = msg.node_id as string;
            if (!nodeId) return;
            setNodes((prev) => ({
                ...prev,
                [nodeId]: {
                    ...(prev[nodeId] ?? { nodeId, status: "idle" as NodeStatus }),
                    nodeId,
                    status: "completed",
                    completedAt: Date.now(),
                    resultSummary: msg.result_summary as string | undefined,
                },
            }));
        },
        workflow_node_failed: (msg) => {
            const msgExecId = msg.execution_id as string | undefined;
            if (!executionId || msgExecId !== executionId) return;
            const nodeId = msg.node_id as string;
            if (!nodeId) return;
            setNodes((prev) => ({
                ...prev,
                [nodeId]: {
                    ...(prev[nodeId] ?? { nodeId, status: "idle" as NodeStatus }),
                    nodeId,
                    status: "failed",
                    completedAt: Date.now(),
                    error: msg.error as string | undefined,
                },
            }));
        },
    });

    // Calcular elapsedMs en vivo
    const enriched: Record<string, NodeRuntimeState> = {};
    for (const [id, state] of Object.entries(nodes)) {
        let elapsedMs: number | undefined;
        if (state.startedAt) {
            const end = state.completedAt ?? Date.now();
            elapsedMs = end - state.startedAt;
        }
        enriched[id] = { ...state, elapsedMs };
    }
    return enriched;
}

export function formatElapsed(ms?: number): string {
    if (!ms || ms < 0) return "0s";
    const s = Math.floor(ms / 1000);
    if (s < 60) return `${s}s`;
    const m = Math.floor(s / 60);
    const r = s % 60;
    return `${m}m ${r}s`;
}
