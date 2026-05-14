import { useEffect, useMemo, useState } from "react";
import { api, type Task } from "@/lib/api";
import type { AIEmployee } from "@/lib/api/ai_employees";
import { useNotificationStore } from "@/stores/notifications";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";
import { useAgentStream } from "@/hooks/useAgentStream";

export function useTaskPanel(isActive: boolean) {
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
    const [chatLoading, setChatLoading] = useState(false);
    const [chatMessages, setChatMessages] = useState<{ role: "user" | "assistant"; content: string }[]>([]);
    // UI.AGT — task_id activo del chat para suscribir SSE de progreso.
    const [chatTaskId, setChatTaskId] = useState<string | null>(null);
    // UI.COST — task_id congelado tras cancel/complete para mostrar modal de coste.
    const [costModal, setCostModal] = useState<{ taskId: string; reason: "cancelled" | "completed" } | null>(null);
    const stream = useAgentStream(chatTaskId);
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
            .catch(() => { })
            .finally(() => setLoading(false));
    };

    const loadSilent = () => {
        api.tasks.list({ limit: 50 })
            .then(setTasks)
            .catch(() => { });
    };

    const hasActive = tasks.some(t => !["done", "failed", "cancelled"].includes(t.status));

    useEffect(() => {
        if (isActive) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [refreshKey, isActive]);

    // NOTA: anteriormente había un navigationGuard aquí que impedía cambiar
    // de página mientras una task estaba activa. Eliminado: las tasks viven
    // en backend y siguen ejecutándose aunque el usuario navegue; al volver
    // a la pestaña, el polling y el WebSocket re-sincronizan el estado.

    useEffect(() => {
        if (!isActive) return;
        const interval = setInterval(loadSilent, hasActive ? 2000 : 10000);
        return () => clearInterval(interval);
    }, [hasActive, isActive]);

    useEffect(() => {
        if (showNew) {
            api.aiEmployees.list().then(setEmployees).catch(() => {});
        }
    }, [showNew]);

    async function handleChat() {
        if (!chatQuery.trim() || chatLoading) return;
        const userText = chatQuery.trim();
        setChatQuery("");
        setChatLoading(true);
        setChatMessages(prev => [...prev, { role: "user", content: userText }]);
        try {
            const task = await api.tasks.create("chat", userText);
            setChatTaskId(task.id);
            let answer = "";
            for (let i = 0; i < 30; i++) {
                await new Promise(r => setTimeout(r, 1000));
                const updated = await api.tasks.get(task.id);
                if (updated.status === "done" || updated.status === "failed") {
                    const results = updated.agent_results as any[];
                    if (Array.isArray(results)) {
                        for (let j = results.length - 1; j >= 0; j--) {
                            if (results[j]?.output?.response) {
                                answer = results[j].output.response;
                                break;
                            }
                        }
                    }
                    if (!answer) answer = updated.error_message ? `Error: ${updated.error_message}` : "No se obtuvo respuesta.";
                    break;
                }
            }
            if (!answer) answer = "La IA tardó demasiado. Inténtalo de nuevo.";
            setChatMessages(prev => [...prev, { role: "assistant", content: answer }]);
        } catch (e: any) {
            setChatMessages(prev => [...prev, { role: "assistant", content: `Error: ${e.message || "No se pudo procesar"}` }]);
        } finally {
            setChatLoading(false);
            setChatTaskId(null);
        }
    }

    async function stopChat() {
        // UI.AGT — botón "Detener": cancela la task en backend + cierra stream local.
        const idAtStop = chatTaskId;
        await stream.stop();
        setChatLoading(false);
        setChatMessages(prev => [...prev, { role: "assistant", content: "Generación detenida por el usuario." }]);
        setChatTaskId(null);
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
            setError(err instanceof Error ? err.message : "Error al crear la tarea");
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
        if (!await showConfirm({ message: "¿Cancelar esta tarea?", confirmLabel: "Cancelar", confirmVariant: "danger" })) return;
        try {
            await api.tasks.cancel(id);
        } catch (err: any) {
            toast.error(err.message || "Error al cancelar la tarea");
        }
        load();
    }

    async function cleanupTasks() {
        if (tasks.length === 0) return;
        const active = tasks.filter(t => !["done", "failed", "cancelled"].includes(t.status));
        const msg = active.length > 0
            ? `¿Eliminar todas las tareas? ${active.length} tarea(s) activa(s) serán canceladas.`
            : `¿Eliminar ${tasks.length} tarea(s) del historial?`;
        if (!await showConfirm({ message: msg, confirmLabel: "Eliminar", confirmVariant: "danger" })) return;
        try {
            await api.tasks.cleanup();
            load();
        } catch {
            toast.error("Error al limpiar tareas");
        }
    }

    const activeTasks = tasks.filter(t => t.domain !== "chat" && !["done", "failed", "cancelled"].includes(t.status));
    const doneTasks = tasks.filter(t => t.domain !== "chat" && ["done", "failed", "cancelled"].includes(t.status));

    return {
        tasks, loading, showNew, setShowNew, domain, setDomain,
        selectedEmployeeId, setSelectedEmployeeId, employees,
        intent, setIntent, creating, error,
        chatQuery, setChatQuery, chatLoading, chatMessages, setChatMessages,
        handleChat, createTask, replyToTask, cancelTask, cleanupTasks,
        load, activeTasks, doneTasks,
        chatTaskId, chatProgress, stopChat,
        chatStreaming: chatTaskId !== null && stream.status === "streaming",
        costModal,
        closeCostModal: () => setCostModal(null),
    };
}
