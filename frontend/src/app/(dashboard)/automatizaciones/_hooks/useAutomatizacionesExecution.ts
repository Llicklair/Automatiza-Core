"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { api, WorkflowExecution } from "@/lib/api";
import { logError } from "@/lib/logger";
import { usePolling } from "@/lib/hooks/usePolling";

export function useAutomatizacionesExecution(
    showToast: (msg: string, type: "ok" | "err") => void,
) {
    const t = useTranslations("automatizaciones");
    const [runningId, setRunningId] = useState<string | null>(null);
    const [expandedId, setExpandedId] = useState<string | null>(null);
    const [executions, setExecutions] = useState<Record<string, WorkflowExecution[]>>({});
    const [loadingExec, setLoadingExec] = useState<string | null>(null);
    const [refreshingExec, setRefreshingExec] = useState<string | null>(null);

    // Context input per workflow
    const [contextInputId, setContextInputId] = useState<string | null>(null);
    const [contextText, setContextText] = useState("");

    // Live logs
    const [liveLogs, setLiveLogs] = useState<Record<string, string[]>>({});
    const logsRef = useRef<ReturnType<typeof setInterval> | null>(null);

    const loadExecutions = useCallback(async (id: string) => {
        setLoadingExec(id);
        try {
            const data = await api.workflows.executions(id);
            setExecutions(prev => ({ ...prev, [id]: data }));
        } catch (e) { logError("automatizaciones/page", e); }
        finally { setLoadingExec(null); }
    }, []);

    const loadLogs = useCallback(async (workflowId: string, executionId: string) => {
        try {
            const data = await api.workflows.executionLogs(workflowId, executionId);
            setLiveLogs(prev => ({ ...prev, [executionId]: data.lines }));
            return data.status;
        } catch { return "unknown"; }
    }, []);

    // Auto-refresh polling for active executions
    const expandedExecs = expandedId ? (executions[expandedId] || []) : [];
    const hasActiveExec = expandedExecs.some(e => e.status === "running" || e.status === "paused");
    usePolling(
        () => { if (expandedId) loadExecutions(expandedId); },
        4000,
        { enabled: !!expandedId && hasActiveExec },
    );

    // Live logs polling
    useEffect(() => {
        if (logsRef.current) { clearInterval(logsRef.current); logsRef.current = null; }
        if (!expandedId) return;
        const wfExecs = executions[expandedId] || [];
        const active = wfExecs.find(e => e.status === "running");
        if (!active) return;
        loadLogs(expandedId, active.id);
        logsRef.current = setInterval(async () => {
            const status = await loadLogs(expandedId, active.id);
            if (status !== "running") {
                clearInterval(logsRef.current!);
                logsRef.current = null;
                await loadExecutions(expandedId);
            }
        }, 2000);
        return () => { if (logsRef.current) { clearInterval(logsRef.current); logsRef.current = null; } };
    }, [expandedId, executions, loadExecutions, loadLogs]);

    const handleRun = async (id: string) => {
        setRunningId(id);
        try {
            await api.workflows.run(id);
            showToast(t("toast.launched"), "ok");
            if (expandedId === id) await loadExecutions(id);
        } catch (error: unknown) { showToast(error instanceof Error ? error.message : t("toast.runError"), "err"); }
        finally { setRunningId(null); }
    };

    const handleRunWithContext = async (wfId: string) => {
        setRunningId(wfId);
        try {
            await api.workflows.runWithContext(wfId, contextText);
            showToast(t("toast.launchedWithContext"), "ok");
            setContextInputId(null); setContextText("");
            if (expandedId === wfId) await loadExecutions(wfId);
        } catch (error: unknown) { showToast(error instanceof Error ? error.message : t("toast.runError"), "err"); }
        finally { setRunningId(null); }
    };

    const handleCancel = async (workflowId: string, executionId: string) => {
        try {
            await api.workflows.cancelExecution(workflowId, executionId);
            showToast(t("toast.cancelled"), "ok");
            await loadExecutions(workflowId);
        } catch (error: unknown) { showToast(error instanceof Error ? error.message : t("toast.cancelError"), "err"); }
    };

    const handleResume = async (workflowId: string, executionId: string) => {
        try {
            await api.workflows.resumeExecution(workflowId, executionId);
            showToast(t("toast.resumed"), "ok");
            await loadExecutions(workflowId);
        } catch (error: unknown) { showToast(error instanceof Error ? error.message : t("toast.resumeError"), "err"); }
    };

    const refreshExecutions = async (e: React.MouseEvent, id: string) => {
        e.stopPropagation();
        setRefreshingExec(id);
        try {
            const data = await api.workflows.executions(id);
            setExecutions(prev => ({ ...prev, [id]: data }));
        } catch (e) { logError("automatizaciones/page", e); }
        finally { setRefreshingExec(null); }
    };

    const toggleExpand = async (id: string) => {
        if (expandedId === id) { setExpandedId(null); }
        else { setExpandedId(id); if (!executions[id]) await loadExecutions(id); }
    };

    const toggleContextInput = (id: string) => {
        if (contextInputId === id) { setContextInputId(null); setContextText(""); }
        else { setContextInputId(id); setContextText(""); }
    };

    return {
        runningId, expandedId, setExpandedId,
        executions, loadingExec, refreshingExec,
        contextInputId, contextText, setContextText,
        liveLogs,
        loadExecutions,
        handleRun, handleRunWithContext,
        handleCancel, handleResume,
        refreshExecutions, toggleExpand, toggleContextInput,
    };
}
