"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api, type Task } from "@/lib/api";

export function useAgentPolling() {
    const [status, setStatus] = useState<string>("idle");
    const [result, setResult] = useState<unknown>(null);
    const [error, setError] = useState<string | null>(null);
    const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

    const stop = useCallback(() => {
        if (intervalRef.current) { clearInterval(intervalRef.current); intervalRef.current = null; }
    }, []);

    const launch = useCallback(async (intent: string) => {
        stop(); setResult(null); setError(null); setStatus("creating");
        try {
            const task = await api.tasks.create("banking", intent);
            setStatus("polling");
            intervalRef.current = setInterval(async () => {
                try {
                    const t: Task = await api.tasks.get(task.id);
                    if (t.status === "done" || t.status === "failed" || t.status === "cancelled") {
                        stop();
                        setStatus(t.status === "done" ? "done" : "failed");
                        setResult(t.agent_results ?? t.plan);
                        if (t.error_message) setError(t.error_message);
                    }
                } catch { /* keep polling */ }
            }, 2000);
        } catch (e) {
            setStatus("failed");
            setError(e instanceof Error ? e.message : "Error al crear la tarea");
        }
    }, [stop]);

    useEffect(() => () => stop(), [stop]);
    return { launch, status, result, error };
}

export function extractOutput(result: unknown): Record<string, unknown> {
    if (!result) return {};
    const arr = Array.isArray(result) ? result : [result];
    for (const item of arr) {
        const out = (item as Record<string, unknown>).output ?? item;
        if (typeof out === "object" && out !== null) return out as Record<string, unknown>;
    }
    return {};
}
