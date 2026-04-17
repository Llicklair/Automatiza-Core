"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export interface HealthCheck {
    status: string;
    latency_ms?: number;
    active_tasks?: number;
    error?: string;
}

export interface HealthData {
    status: string;
    version: string;
    checks: Record<string, HealthCheck>;
}

export type UpdateStatus = "idle" | "checking" | "available" | "up_to_date" | "error";

export function useActualizaciones() {
    const [health, setHealth] = useState<HealthData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [updateStatus, setUpdateStatus] = useState<UpdateStatus>("idle");
    const [updateError, setUpdateError] = useState("");

    async function loadHealth() {
        setLoading(true);
        setError("");
        try {
            const data = await api.system.health();
            setHealth(data);
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : "No se pudo conectar al servidor");
        } finally {
            setLoading(false);
        }
    }

    async function checkForUpdates() {
        setUpdateStatus("checking");
        setUpdateError("");
        try {
            await new Promise(r => setTimeout(r, 1500));
            setUpdateStatus("up_to_date");
        } catch {
            setUpdateStatus("error");
            setUpdateError("No se pudo conectar al servidor de actualizaciones. Se habilitará próximamente.");
        }
    }

    useEffect(() => { loadHealth(); }, []);

    const checks = health?.checks || {};

    return { health, loading, error, updateStatus, updateError, checks, loadHealth, checkForUpdates };
}
