"use client";

import { useState } from "react";
import { api } from "@/lib/api";

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
const TERMINAL_STATUSES = new Set(["done", "failed", "awaiting_approval"]);

export async function executeTaskAndWait(domain: string, intent: string, onProgress?: (msg: string) => void) {
    const task = await api.tasks.create(domain, intent);
    let currentTask = task;
    const start = Date.now();

    while (!TERMINAL_STATUSES.has(currentTask.status)) {
        if (Date.now() - start > TASK_POLL_TIMEOUT_MS) {
            throw new Error(
                `La consulta está tardando demasiado (>${TASK_POLL_TIMEOUT_MS / 1000}s). ` +
                "Puede que el agente esté sobrecargado. Vuelve a intentarlo en unos segundos.",
            );
        }
        await new Promise(r => setTimeout(r, TASK_POLL_INTERVAL_MS));
        currentTask = await api.tasks.get(task.id);
        if (onProgress) {
            const elapsed = Math.round((Date.now() - start) / 1000);
            onProgress(`Procesando información... (${elapsed}s)`);
        }
    }

    if (currentTask.status === "failed") {
        throw new Error(currentTask.error_message || "Error al ejecutar la tarea");
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
