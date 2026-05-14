/**
 * UI.AGT — hook React que consume el stream SSE de una task del agente.
 *
 * Provee:
 *   - `events`: lista cronológica de eventos recibidos
 *   - `status`: "idle" | "streaming" | "completed" | "cancelled" | "error"
 *   - `stop()`: dispara cancelación (DELETE /tasks/{id}) y aborta el SSE
 *
 * El consumer típico (ChatSection) lo invoca cuando `instruct()` devuelve
 * un `task_id`, y muestra skeleton + último `summary` mientras `streaming`.
 */

"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
    cancelTask,
    streamTaskEvents,
    type TaskProgressEvent,
} from "@/lib/api/taskStream";

export type AgentStreamStatus =
    | "idle"
    | "streaming"
    | "completed"
    | "cancelled"
    | "error";

interface UseAgentStreamResult {
    events: TaskProgressEvent[];
    status: AgentStreamStatus;
    error: string | null;
    stop: () => Promise<void>;
}

export function useAgentStream(taskId: string | null): UseAgentStreamResult {
    const [events, setEvents] = useState<TaskProgressEvent[]>([]);
    const [status, setStatus] = useState<AgentStreamStatus>("idle");
    const [error, setError] = useState<string | null>(null);
    const controllerRef = useRef<AbortController | null>(null);

    useEffect(() => {
        if (!taskId) return;

        setEvents([]);
        setError(null);
        setStatus("streaming");
        const controller = new AbortController();
        controllerRef.current = controller;

        streamTaskEvents(
            taskId,
            (event) => {
                setEvents((prev) => [...prev, event]);
                // Detectamos fin del stream por evento terminal.
                const type = String(event.type ?? "");
                if (type === "task_completed") setStatus("completed");
                else if (type === "task_failed") setStatus("error");
            },
            controller,
        )
            .then(() => {
                // Stream cerró limpio sin evento terminal: lo consideramos completed.
                setStatus((prev) => (prev === "streaming" ? "completed" : prev));
            })
            .catch((err: Error) => {
                if (controller.signal.aborted) {
                    setStatus("cancelled");
                    return;
                }
                setError(err.message);
                setStatus("error");
            });

        return () => {
            controller.abort();
            controllerRef.current = null;
        };
    }, [taskId]);

    const stop = useCallback(async () => {
        if (!taskId) return;
        try {
            await cancelTask(taskId);
        } catch (err) {
            // Mostramos el error pero igualmente cerramos el stream local.
            setError(err instanceof Error ? err.message : String(err));
        }
        controllerRef.current?.abort();
        setStatus("cancelled");
    }, [taskId]);

    return { events, status, error, stop };
}
