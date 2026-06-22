"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
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

export type UpdateStatus = "idle" | "checking" | "available" | "downloading" | "downloaded" | "up_to_date" | "error";

const eAPI = typeof window !== "undefined" ? (window as any).electronAPI : null;

export function useActualizaciones() {
    const t = useTranslations("configuracion");
    const [health, setHealth] = useState<HealthData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [updateStatus, setUpdateStatus] = useState<UpdateStatus>("idle");
    const [updateError, setUpdateError] = useState("");
    const [downloadPercent, setDownloadPercent] = useState(0);
    const [updateVersion, setUpdateVersion] = useState("");

    const loadHealth = useCallback(async () => {
        setLoading(true);
        setError("");
        try {
            const data = await api.system.health();
            setHealth(data);
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : t("actualizaciones.connectError"));
        } finally {
            setLoading(false);
        }
    }, [t]);

    async function checkForUpdates() {
        setUpdateStatus("checking");
        setUpdateError("");
        if (!eAPI) {
            // Fuera de Electron (desarrollo web)
            setTimeout(() => setUpdateStatus("up_to_date"), 800);
            return;
        }
        eAPI.checkForUpdates();
    }

    function installUpdate() {
        eAPI?.installUpdate();
    }

    // Suscribirse a eventos IPC del proceso principal
    useEffect(() => {
        if (!eAPI) return;

        eAPI.onUpdateAvailable((info: { version: string }) => {
            setUpdateVersion(info.version);
            setUpdateStatus("available");
        });
        eAPI.onUpdateNotAvailable(() => setUpdateStatus("up_to_date"));
        eAPI.onUpdateDownloadProgress((p: { percent: number }) => {
            setDownloadPercent(p.percent);
            setUpdateStatus("downloading");
        });
        eAPI.onUpdateDownloaded(() => setUpdateStatus("downloaded"));
        eAPI.onUpdateError((msg: string) => {
            setUpdateStatus("error");
            setUpdateError(msg);
        });

        return () => eAPI.removeUpdateListeners();
    }, []);

    useEffect(() => { loadHealth(); }, [loadHealth]);

    const checks = health?.checks || {};

    return {
        health, loading, error,
        updateStatus, updateError, downloadPercent, updateVersion,
        checks, loadHealth, checkForUpdates, installUpdate,
    };
}
