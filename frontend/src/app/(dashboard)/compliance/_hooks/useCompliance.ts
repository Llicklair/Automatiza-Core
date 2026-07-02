"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { waitForTask, TaskTimeoutError } from "@/lib/api/tasks";

export type Tab = "calendario" | "boe" | "consulta";

export interface Vencimiento {
    modelo: string;
    nombre: string;
    descripcion: string;
    fecha_limite: string;
    dias_restantes: number;
    tipo: string;
    urgente_dias: number;
}

// Timeout duro de polling. El agente IA puede tardar, pero si supera este
// umbral lo más probable es un cuelgue (LLM caído, scraper bloqueado, etc.).
const TASK_POLL_TIMEOUT_MS = 90_000;
const TASK_POLL_INTERVAL_MS = 2_000;

type Translator = (key: string, values?: Record<string, string | number>) => string;

export async function executeTaskAndWait(
    domain: string,
    intent: string,
    t: Translator,
    onProgress?: (msg: string) => void,
) {
    const task = await api.tasks.create(domain, intent);
    const start = Date.now();

    // El polling vive en waitForTask; este interval solo mantiene la
    // granularidad del callback de progreso (segundos transcurridos).
    const progressTimer = onProgress
        ? setInterval(() => {
            const elapsed = Math.round((Date.now() - start) / 1000);
            onProgress(t("hook.progress", { elapsed }));
        }, TASK_POLL_INTERVAL_MS)
        : null;

    let currentTask;
    try {
        currentTask = await waitForTask(task.id, {
            timeoutMs: TASK_POLL_TIMEOUT_MS,
            intervalMs: TASK_POLL_INTERVAL_MS,
        });
    } catch (err) {
        if (err instanceof TaskTimeoutError) {
            throw new Error(t("hook.timeout", { seconds: TASK_POLL_TIMEOUT_MS / 1000 }));
        }
        throw err;
    } finally {
        if (progressTimer) clearInterval(progressTimer);
    }

    if (currentTask.status === "failed") {
        throw new Error(currentTask.error_message || t("hook.taskError"));
    }

    const results: any[] = currentTask.agent_results || [];
    if (results.length > 0) {
        return results[results.length - 1].output || {};
    }

    return {};
}

export function useCompliance() {
    const [tab, setTab] = useState<Tab>("calendario");
    return { tab, setTab };
}
