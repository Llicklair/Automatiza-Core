"use client";

import { useEffect, useState } from "react";
import { api, type Task } from "@/lib/api";
import { useNotificationStore } from "@/stores/notifications";
import { Plus, X, ChevronDown, Bot, Clock, CheckCircle2, AlertCircle, Loader2, RefreshCw, Copy, Check, MessageSquare, Trash2 } from "lucide-react";
import InfoBanner from "@/components/InfoBanner";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";
import { useNavigationGuard } from "@/stores/navigationGuard";

const STATUS_COLOR: Record<string, string> = {
    pending: "text-zinc-400 bg-zinc-500/10 border-zinc-500/20",
    planning: "text-blue-400 bg-blue-500/10 border-blue-500/20",
    executing: "text-indigo-400 bg-indigo-500/10 border-indigo-500/20",
    awaiting_approval: "text-amber-400 bg-amber-500/10 border-amber-500/20",
    done: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
    failed: "text-red-400 bg-red-500/10 border-red-500/20",
    cancelled: "text-zinc-500 bg-zinc-700/20 border-zinc-700/20",
};
const STATUS_LABEL: Record<string, string> = {
    pending: "Pendiente",
    planning: "Planificando",
    executing: "Ejecutando",
    awaiting_approval: "Espera aprobación",
    done: "Completada",
    failed: "Fallida",
    cancelled: "Cancelada",
};
const STATUS_ICON: Record<string, React.ReactNode> = {
    pending: <Clock className="w-3 h-3" />,
    planning: <Bot className="w-3 h-3" />,
    executing: <Loader2 className="w-3 h-3 animate-spin" />,
    awaiting_approval: <AlertCircle className="w-3 h-3" />,
    done: <CheckCircle2 className="w-3 h-3" />,
    failed: <X className="w-3 h-3" />,
    cancelled: <X className="w-3 h-3" />,
};

const CHAT_OPTION = {
    value: "chat",
    label: "💬 Chat",
    desc: "Preguntas, dudas o consultas de estado",
};

const COORDINATOR_OPTION = {
    value: "coordinator",
    label: "🧠 Coordinador General",
    desc: "Tarea compleja puntual: coordina varios agentes en secuencia para darte un único resultado",
};

const DOMAIN_OPTIONS = [
    { value: "billing", label: "💰 Facturación", desc: "Facturas, cobros, presupuestos" },
    { value: "documents", label: "📄 Documentos", desc: "OCR, análisis, clasificación de documentos" },
    { value: "hr", label: "👥 RRHH", desc: "Nóminas, empleados, gestión de personal" },
    { value: "compliance", label: "⚖️ Asesor Fiscal", desc: "Obligaciones tributarias, BOE, alertas" },
    { value: "banking", label: "🏦 Banca", desc: "Resumen bancario, movimientos, conciliación" },
    { value: "crm", label: "🤝 CRM", desc: "Oportunidades, clientes, seguimiento comercial" },
    { value: "excel", label: "📊 Excel / Datos", desc: "Cruza tablas y elabora hojas de cálculo" },
    { value: "email", label: "📧 Correos", desc: "Bandeja de entrada, responde y organiza" },
];

const ALL_DOMAIN_OPTIONS = [CHAT_OPTION, COORDINATOR_OPTION, ...DOMAIN_OPTIONS];

function ChatBubble({ text }: { text: string }) {
    return (
        <div className="px-6 pb-5 pt-3 border-t border-[#27272a]/50">
            <div className="flex gap-3 items-start">
                <div className="p-1.5 rounded-lg bg-indigo-500/20 mt-0.5 flex-shrink-0">
                    <Bot className="w-4 h-4 text-indigo-400" />
                </div>
                <div className="bg-[#18181b] border border-[#27272a] rounded-2xl rounded-tl-sm px-4 py-3 max-w-[90%]">
                    <p className="text-sm text-zinc-200 leading-relaxed whitespace-pre-wrap">{text}</p>
                </div>
            </div>
        </div>
    );
}

function getChatResponse(task: Task): string | null {
    if (!Array.isArray(task.agent_results)) return null;
    const results = task.agent_results as any[];
    // Buscar resumen conversacional o respuesta de chat
    for (let i = results.length - 1; i >= 0; i--) {
        const r = results[i];
        if ((r.agent === "chat" || r.agent === "summary") && r.output?.action === "chat_response" && r.output?.response) {
            return r.output.response;
        }
    }
    return null;
}

function TaskRow({ task, cancelTask }: { task: Task; cancelTask: (id: string) => void }) {
    const chatResponse = getChatResponse(task);
    const [open, setOpen] = useState(!!chatResponse);
    const [copied, setCopied] = useState(false);
    const hasDetail = chatResponse || task.plan || task.agent_results;
    const domain = ALL_DOMAIN_OPTIONS.find(d => d.value === task.domain);

    const copyPrompt = (e: React.MouseEvent) => {
        e.stopPropagation();
        navigator.clipboard.writeText(task.user_intent).then(() => {
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        });
    };

    return (
        <div className="border-b border-[#27272a] last:border-0 hover:bg-white/[0.02] transition">
            <div
                className={`grid grid-cols-12 gap-4 px-6 py-4 items-center ${hasDetail ? "cursor-pointer" : ""}`}
                onClick={() => hasDetail && setOpen(!open)}
            >
                <div className="col-span-5 min-w-0">
                    <p className="text-sm text-white truncate">{task.user_intent}</p>
                    <p className="text-xs text-zinc-500 mt-0.5 font-mono">{task.id.slice(0, 8)}…</p>
                </div>
                <div className="col-span-2">
                    <span className="text-xs text-zinc-400 bg-zinc-800 px-2 py-0.5 rounded-md">
                        {domain?.label ?? task.domain}
                    </span>
                </div>
                <div className="col-span-2">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium border flex items-center gap-1.5 w-fit ${STATUS_COLOR[task.status] ?? "text-zinc-400"}`}>
                        {STATUS_ICON[task.status]}
                        {STATUS_LABEL[task.status] ?? task.status}
                    </span>
                </div>
                <div className="col-span-2 text-xs text-zinc-500">
                    {new Date(task.created_at).toLocaleDateString("es-ES", {
                        day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit"
                    })}
                </div>
                <div className="col-span-1 flex justify-end gap-2 items-center">
                    {!["done", "failed", "cancelled"].includes(task.status) && (
                        <button
                            onClick={(e) => {
                                e.preventDefault();
                                e.stopPropagation();
                                cancelTask(task.id);
                            }}
                            className="text-zinc-600 hover:text-red-400 transition p-1 rounded"
                            title="Cancelar"
                        >
                            <X className="w-4 h-4" />
                        </button>
                    )}
                    {Boolean(hasDetail) && (
                        <ChevronDown className={`w-4 h-4 text-zinc-500 transition-transform duration-300 ${open ? "rotate-180" : ""}`} />
                    )}
                </div>
            </div>

            {/* Detalles expandibles */}
            {Boolean(hasDetail) && (
                <div className={`grid transition-[grid-template-rows,opacity] duration-300 ease-in-out ${open ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0"}`}>
                    <div className="overflow-hidden">

                        {/* ── Vista chat: burbuja conversacional ── */}
                        {chatResponse ? (
                            <ChatBubble text={chatResponse} />
                        ) : (
                        <div className="px-6 pb-6 pt-2 border-t border-[#27272a]/50 space-y-4">

                            {/* ── Prompt completo del usuario ── */}
                            <div className="rounded-xl border border-indigo-500/20 bg-indigo-500/5 overflow-hidden">
                                <div className="px-4 py-2.5 border-b border-indigo-500/15 bg-indigo-500/10 flex items-center justify-between">
                                    <h4 className="text-xs font-semibold text-indigo-300 uppercase tracking-wider flex items-center gap-2">
                                        <MessageSquare className="w-3 h-3" /> Prompt del usuario
                                    </h4>
                                    <button
                                        onClick={copyPrompt}
                                        className="flex items-center gap-1.5 text-[11px] text-indigo-400 hover:text-white transition px-2 py-1 rounded-md hover:bg-indigo-500/20"
                                        title="Copiar prompt"
                                    >
                                        {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                                        {copied ? "¡Copiado!" : "Copiar"}
                                    </button>
                                </div>
                                <p className="px-4 py-3 text-sm text-indigo-100/90 leading-relaxed whitespace-pre-wrap">
                                    {task.user_intent}
                                </p>
                            </div>

                            {Boolean(task.error_message) && (
                                <div className="p-4 rounded-xl bg-red-500/10 text-sm border border-red-500/20 flex items-start gap-3">
                                    <div className="p-1 bg-red-500/20 rounded-lg">
                                        <X className="w-4 h-4 text-red-400 flex-shrink-0" />
                                    </div>
                                    <div>
                                        <p className="font-semibold text-red-400 mb-0.5">Error durante la ejecución</p>
                                        <p className="text-red-300/80 leading-relaxed">{task.error_message}</p>
                                    </div>
                                </div>
                            )}

                            <div className="grid grid-cols-2 gap-6">
                                {Boolean(task.plan) && (
                                    <div className="bg-[#18181b] rounded-xl border border-[#27272a] overflow-hidden flex flex-col">
                                        <div className="px-4 py-3 border-b border-[#27272a] bg-[#1f1f22]">
                                            <h4 className="text-xs font-semibold text-zinc-300 uppercase tracking-wider flex items-center gap-2">
                                                <span className="w-2 h-2 rounded-full bg-blue-500"></span> Plan de Ejecución
                                            </h4>
                                        </div>
                                        <div className="p-4 overflow-x-auto text-xs font-mono text-zinc-400 flex-1">
                                            {Array.isArray(task.plan) ? (
                                                <div className="space-y-3">
                                                    {(task.plan as any[]).map((step: any, i) => (
                                                        <div key={i} className="flex gap-3">
                                                            <div className="flex flex-col items-center">
                                                                <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] ${step.status === 'done' ? 'bg-emerald-500/20 text-emerald-400' : step.status === 'failed' ? 'bg-red-500/20 text-red-400' : 'bg-zinc-700/50 text-zinc-400'}`}>
                                                                    {i + 1}
                                                                </div>
                                                                {i < (task.plan as any[]).length - 1 && <div className="w-px h-full bg-[#27272a] my-1"></div>}
                                                            </div>
                                                            <div className="pb-3">
                                                                <p className="text-white font-medium mb-1 capitalize">{step.action?.replace(/_/g, ' ')}</p>
                                                                <p className="text-zinc-500 text-[11px]">Agente: <span className="text-indigo-400 font-medium">{step.agent}</span></p>
                                                            </div>
                                                        </div>
                                                    ))}
                                                </div>
                                            ) : (
                                                <pre>{JSON.stringify(task.plan, null, 2)}</pre>
                                            )}
                                        </div>
                                    </div>
                                )}

                                {Boolean(task.agent_results) && (
                                    <div className="bg-[#18181b] rounded-xl border border-[#27272a] overflow-hidden flex flex-col">
                                        <div className="px-4 py-3 border-b border-[#27272a] bg-[#1f1f22]">
                                            <h4 className="text-xs font-semibold text-zinc-300 uppercase tracking-wider flex items-center gap-2">
                                                <span className="w-2 h-2 rounded-full bg-indigo-500"></span> Resultado del Agente
                                            </h4>
                                        </div>
                                        <div className="p-4 overflow-x-auto flex-1">
                                            {Array.isArray(task.agent_results) && (task.agent_results as any[]).length > 0 ? (
                                                <div className="space-y-3">
                                                    {(task.agent_results as any[]).map((res: any, i) => (
                                                        <div key={i} className={`p-3 rounded-lg border ${res.success ? 'border-emerald-500/20 bg-emerald-500/5' : 'border-red-500/20 bg-red-500/5'}`}>
                                                            <div className="flex items-center gap-2 mb-1.5">
                                                                <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider ${res.success ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'}`}>
                                                                    {res.agent}
                                                                </span>
                                                            </div>
                                                            <p className="text-sm text-zinc-200 leading-relaxed">
                                                                {res.summary || (res.error ? `❌ ${res.error}` : (typeof res.output === 'string' ? res.output : '✅ Completado.'))}
                                                            </p>
                                                        </div>
                                                    ))}
                                                </div>
                                            ) : (
                                                <p className="text-xs text-zinc-500 italic">No hay resultados aún.</p>
                                            )}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}

export default function TareasPage() {
    const toast = useToastStore();
    const [tasks, setTasks] = useState<Task[]>([]);
    const [loading, setLoading] = useState(true);
    const [showNew, setShowNew] = useState(false);
    const [domain, setDomain] = useState("billing");
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

    // Polling adaptativo: 2s si hay tareas activas, 10s si no
    const hasActive = tasks.some(t => !["done", "failed", "cancelled"].includes(t.status));

    useEffect(() => {
        load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [refreshKey]);

    useEffect(() => {
        const active = showNew || creating || chatLoading || hasActive;
        setGuard(active, "Hay una tarea IA en ejecución. Si cambias de sección perderás el progreso visible.");
        return () => { if (active) setGuard(false); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [showNew, creating, chatLoading, hasActive]);

    useEffect(() => {
        const interval = setInterval(loadSilent, hasActive ? 2000 : 10000);
        return () => clearInterval(interval);
    }, [hasActive]);

    const _isQuestion = (text: string): boolean => {
        const t = text.toLowerCase().trim();
        return [
            /^\u00bf/, /\?$/, /^(qu[eé]|c[oó]mo|cu[aá]ndo|cu[aá]ntas?|cu[aá]ntos?|d[oó]nde|por qu[eé]|hay|tiene|est[aá]|se ejecut|funcion|termin|fall|result|estado|dime|muestra|lista|resumen)/,
            /^(hola|buenas|gracias|ayuda|explica|diferencia)/,
        ].some(p => p.test(t));
    };

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
            const newTask = await api.tasks.create(domain, intent);
            setShowNew(false);
            setIntent("");
            // Actualización optimista: añadir la tarea al instante sin esperar polling
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
        <div className="p-8 max-w-5xl mx-auto">
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h1 className="text-2xl font-bold text-white">Tareas para la IA</h1>
                    <p className="text-sm text-zinc-400 mt-1">
                        Asigna una instrucción a un agente — él se encargará del resto.
                    </p>
                </div>
                <div className="flex items-center gap-3">
                    <button
                        onClick={load}
                        className="p-2 rounded-lg border border-[#3f3f46] text-zinc-500 hover:text-white hover:border-zinc-400 transition"
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
                        Limpiar historial{(activeTasks.length + doneTasks.length) > 0 ? ` (${activeTasks.length + doneTasks.length})` : ""}
                    </button>
                    <button
                        onClick={() => setShowNew(true)}
                        className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium transition shadow-lg shadow-indigo-900/20"
                    >
                        <Plus className="w-4 h-4" /> Nueva tarea
                    </button>
                </div>
            </div>

            <InfoBanner id="tareas-intro" title="¿Qué es una tarea?">
                <p>
                    Una tarea es una instrucción puntual que le das a un agente IA: &quot;hazme esto ahora&quot;.
                    Elige el agente adecuado, describe lo que necesitas, y él se encarga.
                    Ejemplo: <span className="text-indigo-300">&quot;Genera la factura de enero para ACME S.L.&quot;</span>
                </p>
                <p className="mt-1">
                    <a href="/automatizaciones" className="text-indigo-400 hover:text-indigo-300 underline underline-offset-2 transition">
                        ¿Buscas reglas automáticas? Ir a Automatizaciones →
                    </a>
                </p>
            </InfoBanner>

            {/* Chat con la IA */}
            <div className="mb-8 bg-[#111113] border border-indigo-500/30 rounded-2xl overflow-hidden shadow-lg shadow-indigo-500/5">
                {/* Cabecera */}
                <div className="flex items-center justify-between px-5 py-3 border-b border-indigo-500/15">
                    <div className="flex items-center gap-2 text-indigo-300 text-sm font-medium">
                        <Bot className="w-4 h-4" /> Asistente IA
                    </div>
                    {chatMessages.length > 0 && (
                        <button onClick={() => setChatMessages([])} className="text-xs text-zinc-600 hover:text-zinc-400 transition">
                            Limpiar conversación
                        </button>
                    )}
                </div>
                {/* Historial de mensajes */}
                {chatMessages.length > 0 && (
                    <div className="px-5 py-4 space-y-4 max-h-80 overflow-y-auto">
                        {chatMessages.map((msg, i) => (
                            msg.role === "user" ? (
                                <div key={i} className="flex justify-end">
                                    <div className="bg-indigo-600/20 border border-indigo-500/20 rounded-2xl rounded-tr-sm px-4 py-2.5 max-w-[80%]">
                                        <p className="text-sm text-indigo-100 leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                                    </div>
                                </div>
                            ) : (
                                <div key={i} className="flex gap-2.5 items-start">
                                    <div className="p-1.5 rounded-lg bg-indigo-500/20 flex-shrink-0 mt-0.5">
                                        <Bot className="w-3.5 h-3.5 text-indigo-400" />
                                    </div>
                                    <div className="bg-[#09090b] border border-zinc-800 rounded-2xl rounded-tl-sm px-4 py-2.5 max-w-[85%]">
                                        <p className="text-sm text-zinc-100 leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                                    </div>
                                </div>
                            )
                        ))}
                        {chatLoading && (
                            <div className="flex gap-2.5 items-center">
                                <div className="p-1.5 rounded-lg bg-indigo-500/20 flex-shrink-0">
                                    <Bot className="w-3.5 h-3.5 text-indigo-400" />
                                </div>
                                <div className="bg-[#09090b] border border-zinc-800 rounded-2xl rounded-tl-sm px-4 py-2.5">
                                    <Loader2 className="w-4 h-4 animate-spin text-indigo-400" />
                                </div>
                            </div>
                        )}
                    </div>
                )}
                {/* Input */}
                <div className="px-5 py-4">
                    <div className="flex bg-[#09090b] border border-zinc-800 rounded-xl overflow-hidden focus-within:border-indigo-500 transition-colors">
                        <input type="text" value={chatQuery}
                            onChange={(e) => setChatQuery(e.target.value)}
                            onKeyDown={(e) => e.key === "Enter" && handleChat()}
                            placeholder="Pregunta lo que quieras... ej: ¿Cuántas facturas pendientes tengo?"
                            className="flex-1 bg-transparent border-none text-white text-sm px-4 py-3 focus:outline-none focus:ring-0 placeholder:text-zinc-600" />
                        <button onClick={handleChat} disabled={chatLoading || !chatQuery.trim()}
                            className="px-5 bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm transition-colors disabled:opacity-50 flex items-center gap-2">
                            <MessageSquare className="w-4 h-4" />
                            Enviar
                        </button>
                    </div>
                </div>
            </div>

            {/* Modal nueva tarea */}
            {showNew && (
                <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4" onClick={() => setShowNew(false)}>
                    <div className="w-full max-w-lg rounded-2xl border border-[#27272a] bg-[#111113] overflow-hidden"
                        onClick={e => e.stopPropagation()}>
                        <div className="flex items-center justify-between px-6 py-4 border-b border-[#27272a]">
                            <h2 className="font-semibold text-white text-base">Nueva tarea para la IA</h2>
                            <button onClick={() => setShowNew(false)} className="text-zinc-400 hover:text-white transition">
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        <form onSubmit={createTask} className="p-6 space-y-4">
                            {/* Selector de agente */}
                            <div>
                                <label className="text-sm text-zinc-300 block mb-2 font-medium">¿A qué agente se lo asignas?</label>
                                <div className="grid grid-cols-2 gap-2">
                                    {/* Coordinador General — ocupa las 2 columnas arriba */}
                                    <button
                                        type="button"
                                        onClick={() => setDomain(COORDINATOR_OPTION.value)}
                                        className={`col-span-2 text-left p-3 rounded-xl border text-sm transition ${domain === COORDINATOR_OPTION.value
                                            ? "border-purple-500 bg-purple-500/10 text-white ring-1 ring-purple-500/30"
                                            : "border-[#3f3f46] bg-[#18181b] text-zinc-400 hover:border-purple-500/50 hover:text-zinc-300"
                                            }`}
                                    >
                                        <p className="font-medium">{COORDINATOR_OPTION.label}</p>
                                        <p className="text-[11px] mt-0.5 opacity-70">{COORDINATOR_OPTION.desc}</p>
                                    </button>
                                    {/* Agentes especializados */}
                                    {DOMAIN_OPTIONS.map(opt => (
                                        <button
                                            key={opt.value}
                                            type="button"
                                            onClick={() => setDomain(opt.value)}
                                            className={`text-left p-3 rounded-xl border text-sm transition ${domain === opt.value
                                                ? "border-indigo-500 bg-indigo-500/10 text-white"
                                                : "border-[#3f3f46] bg-[#18181b] text-zinc-400 hover:border-zinc-500 hover:text-zinc-300"
                                                }`}
                                        >
                                            <p className="font-medium">{opt.label}</p>
                                            <p className="text-[11px] mt-0.5 opacity-70">{opt.desc}</p>
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {/* Instrucción */}
                            <div>
                                <label className="text-sm text-zinc-300 block mb-1.5 font-medium">
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
                                    className="w-full px-3 py-2.5 rounded-xl bg-[#18181b] border border-[#3f3f46] text-white text-sm placeholder-zinc-500 resize-none focus:outline-none focus:ring-2 focus:ring-indigo-500 transition"
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
                                    onClick={() => setShowNew(false)}
                                    className="flex-1 py-2.5 rounded-xl border border-[#3f3f46] text-zinc-400 hover:text-white text-sm transition"
                                >
                                    Cancelar
                                </button>
                                <button
                                    type="submit"
                                    disabled={creating || !intent.trim()}
                                    className="flex-1 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-medium transition flex items-center justify-center gap-2"
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
                    <h2 className="text-xs text-zinc-500 uppercase tracking-wider mb-3 font-medium">En proceso ({activeTasks.length})</h2>
                    <div className="rounded-xl border border-[#27272a] bg-[#111113] overflow-hidden">
                        <div className="grid grid-cols-12 gap-4 px-6 py-3 border-b border-[#27272a] text-xs font-medium text-zinc-500 uppercase tracking-wide">
                            <div className="col-span-5">Instrucción</div>
                            <div className="col-span-2">Agente</div>
                            <div className="col-span-2">Estado</div>
                            <div className="col-span-2">Creada</div>
                            <div className="col-span-1 text-right">Acción</div>
                        </div>
                        {activeTasks.map(task => (
                            <TaskRow key={task.id} task={task} cancelTask={cancelTask} />
                        ))}
                    </div>
                </div>
            )}

            {/* Historial */}
            <div>
                <h2 className="text-xs text-zinc-500 uppercase tracking-wider mb-3 font-medium">Historial</h2>
                <div className="rounded-xl border border-[#27272a] bg-[#111113] overflow-hidden">
                    <div className="grid grid-cols-12 gap-4 px-6 py-3 border-b border-[#27272a] text-xs font-medium text-zinc-500 uppercase tracking-wide">
                        <div className="col-span-5">Instrucción</div>
                        <div className="col-span-2">Agente</div>
                        <div className="col-span-2">Estado</div>
                        <div className="col-span-2">Creada</div>
                        <div className="col-span-1 text-right">Acción</div>
                    </div>
                    {loading ? (
                        <div className="py-14 flex items-center justify-center gap-2 text-zinc-500 text-sm">
                            <Loader2 className="w-4 h-4 animate-spin" /> Cargando…
                        </div>
                    ) : doneTasks.length === 0 && activeTasks.length === 0 ? (
                        <div className="py-14 text-center">
                            <Bot className="w-8 h-8 text-zinc-700 mx-auto mb-3" />
                            <p className="text-zinc-500 text-sm">No hay tareas aún.</p>
                            <p className="text-zinc-600 text-xs mt-1">Crea la primera con el botón de arriba.</p>
                        </div>
                    ) : doneTasks.length === 0 ? (
                        <div className="py-8 text-center text-zinc-600 text-xs">Ninguna tarea completada aún.</div>
                    ) : (
                        doneTasks.map(task => (
                            <TaskRow key={task.id} task={task} cancelTask={cancelTask} />
                        ))
                    )}
                </div>
            </div>
        </div>
    );
}
