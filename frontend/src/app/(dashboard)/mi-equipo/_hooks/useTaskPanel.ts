import { useEffect, useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { api, type Task } from "@/lib/api";
import { surfaceIfConnectivity } from "@/lib/api/errors";
import type { AIEmployee } from "@/lib/api/ai_employees";
import { useAiChatStore } from "@/stores/aiChat";
import { useNotificationStore } from "@/stores/notifications";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";
import { useAgentStream } from "@/hooks/useAgentStream";
import { usePolling } from "@/lib/hooks/usePolling";

export function useTaskPanel(isActive: boolean) {
    const t = useTranslations("miEquipo");
    const tc = useTranslations("common");
    const toast = useToastStore();
    const [tasks, setTasks] = useState<Task[]>([]);
    const [loading, setLoading] = useState(true);
    const [showNew, setShowNew] = useState(false);
    const [domain, setDomain] = useState("coordinator");
    const [selectedEmployeeId, setSelectedEmployeeId] = useState<string | null>(null);
    const [employees, setEmployees] = useState<AIEmployee[]>([]);
    const [intent, setIntent] = useState("");
    const [creating, setCreating] = useState(false);
    const [error, setError] = useState("");
    const [chatQuery, setChatQuery] = useState("");
    // Hilo de chat ÚNICO compartido con AiChatBar (dashboard) — vive en el store.
    const aiChat = useAiChatStore();
    // UI.COST — task_id congelado tras cancel/complete para mostrar modal de coste.
    const [costModal, setCostModal] = useState<{ taskId: string; reason: "cancelled" | "completed" } | null>(null);
    const stream = useAgentStream(aiChat.activeTaskId);
    const chatProgress = useMemo(() => {
        for (let i = stream.events.length - 1; i >= 0; i--) {
            const e = stream.events[i];
            if (typeof e.summary === "string" && e.summary.trim()) return e.summary;
        }
        return null;
    }, [stream.events]);
    const refreshKey = useNotificationStore((s) => s.refreshKey);

    const load = () => {
        setLoading(true);
        api.tasks.list({ limit: 50 })
            .then(setTasks)
            .catch((err) => { surfaceIfConnectivity(err); })
            .finally(() => setLoading(false));
    };

    const loadSilent = () => {
        api.tasks.list({ limit: 50 })
            .then(setTasks)
            .catch(() => { });
    };

    const hasActive = tasks.some(task => !["done", "failed", "cancelled"].includes(task.status));

    useEffect(() => {
        if (isActive) load();
     
    }, [refreshKey, isActive]);

    // NOTA: anteriormente había un navigationGuard aquí que impedía cambiar
    // de página mientras una task estaba activa. Eliminado: las tasks viven
    // en backend y siguen ejecutándose aunque el usuario navegue; al volver
    // a la pestaña, el polling y el WebSocket re-sincronizan el estado.

    usePolling(loadSilent, hasActive ? 2000 : 10000, { enabled: isActive });

    useEffect(() => {
        if (showNew) {
            api.aiEmployees.list().then(setEmployees).catch(() => {});
        }
    }, [showNew]);

    async function handleChat() {
        if (!chatQuery.trim() || aiChat.sending) return;
        const userText = chatQuery.trim();
        setChatQuery("");
        await aiChat.send(userText, {
            noResponse: t("taskPanel.noResponse"),
            timeout: t("taskPanel.aiTimeout"),
            sendError: t("taskPanel.couldNotProcess"),
        });
    }

    async function stopChat() {
        // UI.AGT — botón "Detener": cancela la task en backend + cierra stream local.
        const idAtStop = aiChat.activeTaskId;
        await stream.stop();
        aiChat.markStopped(t("taskPanel.generationStopped"));
        // UI.COST — abre modal con tokens consumidos antes de detener.
        if (idAtStop) {
            setCostModal({ taskId: idAtStop, reason: "cancelled" });
        }
    }

    async function createTask(e: React.FormEvent) {
        e.preventDefault();
        if (!intent.trim()) return;
        setCreating(true);
        setError("");
        try {
            const meta = selectedEmployeeId
                ? { addressed_employee_id: selectedEmployeeId, addressed_employee_domain: domain }
                : undefined;
            const newTask = await api.tasks.create(domain, intent, meta);
            setShowNew(false);
            setIntent("");
            setSelectedEmployeeId(null);
            if (newTask && typeof newTask === "object" && "id" in newTask) {
                setTasks(prev => [newTask as Task, ...prev]);
            } else {
                loadSilent();
            }
        } catch (err: unknown) {
            if (surfaceIfConnectivity(err)) return;
            setError(err instanceof Error ? err.message : t("taskPanel.errorCreating"));
        } finally {
            setCreating(false);
        }
    }

    async function replyToTask(parentTaskId: string, domain: string, reply: string) {
        const newTask = await api.tasks.create(domain, reply, undefined, parentTaskId);
        if (newTask && typeof newTask === "object" && "id" in newTask) {
            setTasks(prev => [newTask as Task, ...prev]);
        }
    }

    async function cancelTask(id: string) {
        if (!await showConfirm({ message: t("taskPanel.confirmCancel"), confirmLabel: tc("cancel"), confirmVariant: "danger" })) return;
        try {
            await api.tasks.cancel(id);
        } catch (err: any) {
            if (!surfaceIfConnectivity(err)) toast.error(err.message || t("taskPanel.errorCancelling"));
        }
        load();
    }

    async function cleanupTasks() {
        if (tasks.length === 0) return;
        const active = tasks.filter(task => !["done", "failed", "cancelled"].includes(task.status));
        const msg = active.length > 0
            ? t("taskPanel.confirmCleanupActive", { count: active.length })
            : t("taskPanel.confirmCleanupHistory", { count: tasks.length });
        if (!await showConfirm({ message: msg, confirmLabel: tc("delete"), confirmVariant: "danger" })) return;
        try {
            await api.tasks.cleanup();
            load();
        } catch {
            toast.error(t("taskPanel.errorCleanup"));
        }
    }

    const activeTasks = tasks.filter(task => task.domain !== "chat" && !["done", "failed", "cancelled"].includes(task.status));
    const doneTasks = tasks.filter(task => task.domain !== "chat" && ["done", "failed", "cancelled"].includes(task.status));

    return {
        tasks, loading, showNew, setShowNew, domain, setDomain,
        selectedEmployeeId, setSelectedEmployeeId, employees,
        intent, setIntent, creating, error,
        chatQuery, setChatQuery,
        chatLoading: aiChat.sending,
        chatMessages: aiChat.messages,
        setChatMessages: aiChat.setMessages,
        handleChat, createTask, replyToTask, cancelTask, cleanupTasks,
        load, activeTasks, doneTasks,
        chatTaskId: aiChat.activeTaskId, chatProgress, stopChat,
        chatStreaming: aiChat.activeTaskId !== null && stream.status === "streaming",
        costModal,
        closeCostModal: () => setCostModal(null),
    };
}
