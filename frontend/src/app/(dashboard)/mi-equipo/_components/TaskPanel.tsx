"use client";

import { useEffect, useState } from "react";
import { api, type Task } from "@/lib/api";
import type { AIEmployee } from "@/lib/api/ai_employees";
import { useNotificationStore } from "@/stores/notifications";
import { Plus, X, Bot, AlertCircle, Loader2, RefreshCw, MessageSquare, Trash2 } from "lucide-react";
import InfoBanner from "@/components/InfoBanner";
import { ErrorBoundary } from "@/components/ui/ErrorBoundary";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";
import { useNavigationGuard } from "@/stores/navigationGuard";
import { TaskRow } from "./TaskRow";
import { COORDINATOR_OPTION } from "./task-constants";
import { DOMAIN_ICON } from "./EmployeeCard";

interface TaskPanelProps {
    isActive: boolean;
}

export function TaskPanel({ isActive }: TaskPanelProps) {
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
    const refreshKey = useNotificationStore((s) => s.refreshKey);
    const setGuard = useNavigationGuard((s) => s.setGuard);

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

    useEffect(() => {
        if (!isActive) return;
        const active = showNew || creating || chatLoading || hasActive;
        setGuard(active, "Hay una tarea IA en ejecución. Si cambias de sección perderás el progreso visible.");
        return () => { if (active) setGuard(false); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [showNew, creating, chatLoading, hasActive, isActive]);

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

    return (
        <ErrorBoundary section="tareas">
        <div>
            {/* Header con acciones */}
            <div className="flex items-center justify-between mb-6">
                <p className="text-sm text-muted-foreground">
                    Asigna una instrucción a un agente — él se encargará del resto.
                </p>
                <div className="flex items-center gap-3">
                    <button
                        onClick={load}
                        className="p-2 rounded-lg border border-border text-muted-foreground hover:text-foreground hover:border-border transition"
                        title="Actualizar"
                    >
                        <RefreshCw className="w-4 h-4" />
                    </button>
                    <button
                        onClick={cleanupTasks}
                        disabled={tasks.length === 0}
                        className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-red-500/20 text-red-400/70 hover:text-red-400 hover:bg-red-500/10 text-xs font-medium transition disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:bg-transparent disabled:hover:text-red-400/70"
                        title="Eliminar todas las tareas — las activas se cancelan"
                    >
                        <Trash2 className="w-3.5 h-3.5" />
                        Limpiar{(activeTasks.length + doneTasks.length) > 0 ? ` (${activeTasks.length + doneTasks.length})` : ""}
                    </button>
                    <button
                        onClick={() => setShowNew(true)}
                        className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-primary hover:bg-primary text-foreground text-sm font-medium transition shadow-lg shadow-primary/20"
                    >
                        <Plus className="w-4 h-4" /> Nueva tarea
                    </button>
                </div>
            </div>

            <InfoBanner id="tareas-intro" title="¿Qué es una tarea?">
                <p>
                    Una tarea es una instrucción puntual que le das a un agente IA: &quot;hazme esto ahora&quot;.
                    Elige el agente adecuado, describe lo que necesitas, y él se encarga.
                    Ejemplo: <span className="text-primary">&quot;Genera la factura de enero para ACME S.L.&quot;</span>
                </p>
                <p className="mt-1">
                    <a href="/automatizaciones" className="text-primary hover:text-primary underline underline-offset-2 transition">
                        ¿Buscas reglas automáticas? Ir a Automatizaciones →
                    </a>
                </p>
            </InfoBanner>

            {/* Chat con la IA */}
            <div className="mb-8 bg-card border border-primary/20 rounded-2xl overflow-hidden shadow-lg shadow-primary/20">
                <div className="flex items-center justify-between px-5 py-3 border-b border-primary/20">
                    <div className="flex items-center gap-2 text-primary text-sm font-medium">
                        <Bot className="w-4 h-4" /> Asistente IA
                    </div>
                    {chatMessages.length > 0 && (
                        <button onClick={() => setChatMessages([])} className="text-xs text-muted-foreground hover:text-muted-foreground transition">
                            Limpiar conversación
                        </button>
                    )}
                </div>
                {chatMessages.length > 0 && (
                    <div className="px-5 py-4 space-y-4 max-h-80 overflow-y-auto">
                        {chatMessages.map((msg, i) => (
                            msg.role === "user" ? (
                                <div key={i} className="flex justify-end">
                                    <div className="bg-primary/20 border border-primary/20 rounded-2xl rounded-tr-sm px-4 py-2.5 max-w-[80%]">
                                        <p className="text-sm text-primary-foreground leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                                    </div>
                                </div>
                            ) : (
                                <div key={i} className="flex gap-2.5 items-start">
                                    <div className="p-1.5 rounded-lg bg-primary/20 flex-shrink-0 mt-0.5">
                                        <Bot className="w-3.5 h-3.5 text-primary" />
                                    </div>
                                    <div className="bg-background border border-border rounded-2xl rounded-tl-sm px-4 py-2.5 max-w-[85%]">
                                        <p className="text-sm text-foreground leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                                    </div>
                                </div>
                            )
                        ))}
                        {chatLoading && (
                            <div className="flex gap-2.5 items-center">
                                <div className="p-1.5 rounded-lg bg-primary/20 flex-shrink-0">
                                    <Bot className="w-3.5 h-3.5 text-primary" />
                                </div>
                                <div className="bg-background border border-border rounded-2xl rounded-tl-sm px-4 py-2.5">
                                    <Loader2 className="w-4 h-4 animate-spin text-primary" />
                                </div>
                            </div>
                        )}
                    </div>
                )}
                <div className="px-5 py-4">
                    <div className="flex bg-background border border-border rounded-xl overflow-hidden focus-within:border-primary transition-colors">
                        <input type="text" value={chatQuery}
                            onChange={(e) => setChatQuery(e.target.value)}
                            onKeyDown={(e) => e.key === "Enter" && handleChat()}
                            placeholder="Pregunta lo que quieras... ej: ¿Cuántas facturas pendientes tengo?"
                            className="flex-1 bg-transparent border-none text-foreground text-sm px-4 py-3 focus:outline-none focus:ring-0 placeholder:text-muted-foreground" />
                        <button onClick={handleChat} disabled={chatLoading || !chatQuery.trim()}
                            className="px-5 bg-primary hover:bg-primary text-foreground font-medium text-sm transition-colors disabled:opacity-50 flex items-center gap-2">
                            <MessageSquare className="w-4 h-4" />
                            Enviar
                        </button>
                    </div>
                </div>
            </div>

            {/* Modal nueva tarea */}
            {showNew && (
                <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4" onClick={() => { setShowNew(false); setSelectedEmployeeId(null); setDomain("coordinator"); }}>
                    <div className="w-full max-w-lg rounded-2xl border border-border bg-card overflow-hidden"
                        onClick={e => e.stopPropagation()}>
                        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
                            <h2 className="font-semibold text-foreground text-base">Nueva tarea para la IA</h2>
                            <button onClick={() => { setShowNew(false); setSelectedEmployeeId(null); setDomain("coordinator"); }} className="text-muted-foreground hover:text-foreground transition">
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        <form onSubmit={createTask} className="p-6 space-y-4">
                            <div>
                                <label className="text-sm text-foreground block mb-2 font-medium">¿A quién se lo asignas?</label>
                                <div className="max-h-64 overflow-y-auto pr-0.5 space-y-2">
                                    {/* Coordinator option */}
                                    <button
                                        type="button"
                                        onClick={() => { setDomain(COORDINATOR_OPTION.value); setSelectedEmployeeId(null); }}
                                        className={`w-full text-left p-3 rounded-xl border text-sm transition ${domain === COORDINATOR_OPTION.value && !selectedEmployeeId
                                            ? "border-purple-500 bg-purple-500/10 text-foreground ring-1 ring-purple-500/30"
                                            : "border-border bg-card text-muted-foreground hover:border-purple-500/50 hover:text-foreground"
                                            }`}
                                    >
                                        <p className="font-medium">{COORDINATOR_OPTION.label}</p>
                                        <p className="text-[11px] mt-0.5 opacity-70">{COORDINATOR_OPTION.desc}</p>
                                    </button>
                                    {/* AI Employees */}
                                    <div className="grid grid-cols-2 gap-2">
                                    {employees.map(emp => {
                                        const icon = emp.icon || (DOMAIN_ICON[emp.domain] ?? "🤖");
                                        const isSelected = selectedEmployeeId === emp.id;
                                        return (
                                            <button
                                                key={emp.id}
                                                type="button"
                                                onClick={() => { setDomain(emp.domain); setSelectedEmployeeId(emp.id); }}
                                                className={`text-left p-3 rounded-xl border text-sm transition flex flex-col gap-1 ${isSelected
                                                    ? "border-primary bg-primary/10 text-foreground ring-1 ring-primary/30"
                                                    : "border-border bg-card text-muted-foreground hover:border-border hover:text-foreground"
                                                    } ${emp.status === "paused" ? "opacity-50 cursor-not-allowed" : ""}`}
                                                disabled={emp.status === "paused"}
                                            >
                                                <span className="text-xl leading-none">{icon}</span>
                                                <p className="font-medium text-xs mt-0.5 truncate">{emp.name}</p>
                                                <p className="text-[10px] opacity-60 truncate">{emp.role}</p>
                                            </button>
                                        );
                                    })}
                                    </div>
                                </div>
                            </div>

                            <div>
                                <label className="text-sm text-foreground block mb-1.5 font-medium">
                                    ¿Qué debe hacer?
                                </label>
                                <textarea
                                    rows={4}
                                    required
                                    value={intent}
                                    onChange={e => setIntent(e.target.value)}
                                    placeholder={
                                        domain === "coordinator" ? "Ej: Lee los correos nuevos, extrae los presupuestos aceptados, crúzalos con los clientes del CRM y genera un Excel con el resumen..." :
                                            domain === "billing" ? "Ej: Crea una factura para cliente ACME S.L. por 1500€ de consultoría" :
                                                domain === "documents" ? "Ej: Analiza el contrato que subí esta mañana y extrae las cláusulas importantes" :
                                                    domain === "hr" ? "Ej: Genera las nóminas de este mes para todos los empleados activos" :
                                                        domain === "compliance" ? "Ej: ¿Cuáles son mis obligaciones fiscales del próximo trimestre?" :
                                                            "Describe qué debe hacer el agente..."
                                    }
                                    className="w-full px-3 py-2.5 rounded-xl bg-card border border-border text-foreground text-sm placeholder:text-muted-foreground resize-none focus:outline-none focus:ring-2 focus:ring-primary transition"
                                />
                            </div>

                            {error && (
                                <div className="flex items-center gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
                                    <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
                                    <p className="text-sm text-red-400">{error}</p>
                                </div>
                            )}

                            <div className="flex gap-3 pt-1">
                                <button
                                    type="button"
                                    onClick={() => { setShowNew(false); setSelectedEmployeeId(null); setDomain("coordinator"); }}
                                    className="flex-1 py-2.5 rounded-xl border border-border text-muted-foreground hover:text-foreground text-sm transition"
                                >
                                    Cancelar
                                </button>
                                <button
                                    type="submit"
                                    disabled={creating || !intent.trim()}
                                    className="flex-1 py-2.5 rounded-xl bg-primary hover:bg-primary disabled:opacity-50 text-foreground text-sm font-medium transition flex items-center justify-center gap-2"
                                >
                                    {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Bot className="w-4 h-4" />}
                                    {creating ? "Enviando…" : "Asignar al agente"}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Lista de tareas activas */}
            {activeTasks.length > 0 && (
                <div className="mb-6">
                    <h2 className="text-xs text-muted-foreground uppercase tracking-wider mb-3 font-medium">En proceso ({activeTasks.length})</h2>
                    <div className="rounded-xl border border-border bg-card overflow-hidden">
                        <div className="grid grid-cols-12 gap-4 px-6 py-3 border-b border-border text-xs font-medium text-muted-foreground uppercase tracking-wide">
                            <div className="col-span-5">Instrucción</div>
                            <div className="col-span-2">Agente</div>
                            <div className="col-span-2">Estado</div>
                            <div className="col-span-2">Creada</div>
                            <div className="col-span-1 text-right">Acción</div>
                        </div>
                        {activeTasks.map(task => (
                            <TaskRow key={task.id} task={task} cancelTask={cancelTask} onReply={replyToTask} />
                        ))}
                    </div>
                </div>
            )}

            {/* Historial */}
            <div>
                <h2 className="text-xs text-muted-foreground uppercase tracking-wider mb-3 font-medium">Historial</h2>
                <div className="rounded-xl border border-border bg-card overflow-hidden">
                    <div className="grid grid-cols-12 gap-4 px-6 py-3 border-b border-border text-xs font-medium text-muted-foreground uppercase tracking-wide">
                        <div className="col-span-5">Instrucción</div>
                        <div className="col-span-2">Agente</div>
                        <div className="col-span-2">Estado</div>
                        <div className="col-span-2">Creada</div>
                        <div className="col-span-1 text-right">Acción</div>
                    </div>
                    {loading ? (
                        <div className="py-14 flex items-center justify-center gap-2 text-muted-foreground text-sm">
                            <Loader2 className="w-4 h-4 animate-spin" /> Cargando…
                        </div>
                    ) : doneTasks.length === 0 && activeTasks.length === 0 ? (
                        <div className="py-14 text-center">
                            <Bot className="w-8 h-8 text-muted-foreground mx-auto mb-3" />
                            <p className="text-muted-foreground text-sm">No hay tareas aún.</p>
                            <p className="text-muted-foreground text-xs mt-1">Crea la primera con el botón de arriba.</p>
                        </div>
                    ) : doneTasks.length === 0 ? (
                        <div className="py-8 text-center text-muted-foreground text-xs">Ninguna tarea completada aún.</div>
                    ) : (
                        doneTasks.map(task => (
                            <TaskRow key={task.id} task={task} cancelTask={cancelTask} onReply={replyToTask} />
                        ))
                    )}
                </div>
            </div>
        </div>
        </ErrorBoundary>
    );
}
