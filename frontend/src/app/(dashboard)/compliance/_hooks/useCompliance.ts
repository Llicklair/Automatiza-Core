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

export async function executeTaskAndWait(domain: string, intent: string, onProgress?: (msg: string) => void) {
    const task = await api.tasks.create(domain, intent);
    let currentTask = task;

    while (currentTask.status === "pending" || currentTask.status === "executing") {
        await new Promise(r => setTimeout(r, 2000));
        currentTask = await api.tasks.get(task.id);
        if (onProgress && currentTask.status === "executing") {
            onProgress("Procesando información...");
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
