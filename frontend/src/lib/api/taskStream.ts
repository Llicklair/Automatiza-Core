/**
 * UI.AGT — cliente del endpoint SSE `/api/v1/tasks/{task_id}/stream`.
 *
 * Consume el stream con `fetch()` + `ReadableStream` (no EventSource —
 * EventSource no permite enviar el JWT en `Authorization` header).
 * Cancelable via `AbortController` propio del caller.
 */

import { BASE, getToken } from "./client";

export interface TaskProgressEvent {
    type: string;
    task_id?: string;
    step?: number;
    total_steps?: number;
    agent?: string;
    summary?: string;
    success?: boolean;
    /** Eventos arbitrarios del backend — pasthrough. */
    [key: string]: unknown;
}

/**
 * Abre un stream SSE para una task. Llama `onEvent` por cada evento.
 * Devuelve una promise que resuelve cuando el stream cierra (limpio o
 * por abort). El caller puede cancelar con `controller.abort()`.
 */
export async function streamTaskEvents(
    taskId: string,
    onEvent: (event: TaskProgressEvent) => void,
    controller: AbortController,
): Promise<void> {
    const token = getToken();
    if (!token) throw new Error("No autenticado");

    const url = `${BASE}/api/v1/tasks/${taskId}/stream`;
    const response = await fetch(url, {
        method: "GET",
        headers: {
            Authorization: `Bearer ${token}`,
            Accept: "text/event-stream",
        },
        signal: controller.signal,
    });

    if (!response.ok) {
        throw new Error(`SSE stream failed: ${response.status}`);
    }
    if (!response.body) {
        throw new Error("SSE stream sin body");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    try {
        while (true) {
            const { done, value } = await reader.read();
            if (done) return;

            buffer += decoder.decode(value, { stream: true });

            // SSE separa eventos con `\n\n`. Procesamos enteros y dejamos resto.
            let separatorIdx: number;
            while ((separatorIdx = buffer.indexOf("\n\n")) !== -1) {
                const frame = buffer.slice(0, separatorIdx);
                buffer = buffer.slice(separatorIdx + 2);

                for (const line of frame.split("\n")) {
                    if (!line.startsWith("data:")) continue;
                    const payload = line.slice(5).trim();
                    if (!payload) continue;
                    try {
                        const parsed = JSON.parse(payload) as TaskProgressEvent;
                        onEvent(parsed);
                    } catch {
                        // Ignorar payloads malformados (logs, comentarios SSE).
                    }
                }
            }
        }
    } catch (err) {
        if (controller.signal.aborted) return; // cancel limpio del caller
        throw err;
    } finally {
        try { reader.releaseLock(); } catch { /* ignore */ }
    }
}

/**
 * Cancela una task en ejecución (UI.AGT — botón "Detener").
 * Llama `DELETE /api/v1/tasks/{task_id}` que ya marca cancelled en BD
 * + interrumpe el asyncio.Task del orquestador.
 */
export async function cancelTask(taskId: string): Promise<void> {
    const token = getToken();
    if (!token) throw new Error("No autenticado");

    const response = await fetch(`${BASE}/api/v1/tasks/${taskId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok && response.status !== 204) {
        throw new Error(`Cancel failed: ${response.status}`);
    }
}

export interface TaskCost {
    task_id: string;
    task_status: string | null;
    tokens_in: number;
    tokens_out: number;
    tokens_total: number;
    cost_eur: number;
    trace_count: number;
    agents: { agent: string; tokens: number; cost_eur: number }[];
}

/** UI.COST — resumen de tokens y coste estimado en EUR para una task. */
export async function fetchTaskCost(taskId: string): Promise<TaskCost> {
    const token = getToken();
    if (!token) throw new Error("No autenticado");

    const response = await fetch(`${BASE}/api/v1/tasks/${taskId}/cost`, {
        method: "GET",
        headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) {
        throw new Error(`Task cost fetch failed: ${response.status}`);
    }
    return (await response.json()) as TaskCost;
}
