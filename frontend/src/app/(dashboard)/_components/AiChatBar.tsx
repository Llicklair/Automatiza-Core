"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { Bot, Loader2, MessageSquare } from "lucide-react";
import Link from "next/link";
import { TaskProgressPipeline } from "./TaskProgressPipeline";

const SUGGESTIONS = [
    "¿Cuánto he facturado este mes?",
    "Genera las nóminas del mes",
    "¿Tengo facturas pendientes de cobro?",
    "Revisa mis obligaciones fiscales",
    "Crea una factura para cliente nuevo",
];

export function AiChatBar() {
    const [input, setInput] = useState("");
    const [sending, setSending] = useState(false);
    const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
    const [messages, setMessages] = useState<{ role: "user" | "assistant"; content: string }[]>([]);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = useCallback(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, []);

    useEffect(() => { scrollToBottom(); }, [messages, scrollToBottom]);

    async function send(text: string) {
        const msg = text.trim();
        if (!msg || sending) return;
        setSending(true);
        setInput("");
        setMessages(prev => [...prev, { role: "user", content: msg }]);
        try {
            const task = await api.tasks.create("chat", msg);
            setActiveTaskId(task.id);
            let answer = "";
            for (let i = 0; i < 30; i++) {
                await new Promise(r => setTimeout(r, 1000));
                const t = await api.tasks.get(task.id);
                if (t.status === "done" || t.status === "failed") {
                    const results = t.agent_results as any[];
                    if (Array.isArray(results)) {
                        for (let j = results.length - 1; j >= 0; j--) {
                            if (results[j]?.output?.response) { answer = results[j].output.response; break; }
                        }
                    }
                    if (!answer) {
                        if (t.error_message) {
                            // Una petición de aclaración no es un error: se muestra
                            // tal cual, sin el prefijo "Error:".
                            const isClarification = Boolean(
                                (t.additional_metadata as Record<string, unknown> | null)?.clarification,
                            );
                            answer = isClarification ? t.error_message : `Error: ${t.error_message}`;
                        } else {
                            answer = "No se obtuvo respuesta.";
                        }
                    }
                    break;
                }
            }
            if (!answer) answer = "La IA tardó demasiado. Inténtalo de nuevo.";
            setMessages(prev => [...prev, { role: "assistant", content: answer }]);
        } catch {
            setMessages(prev => [...prev, { role: "assistant", content: "Error al enviar la tarea. Inténtalo de nuevo." }]);
        } finally {
            setSending(false);
        }
    }

    return (
        <div className="bg-card border border-primary/20 rounded-2xl overflow-hidden shadow-lg shadow-primary/20">
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-3 border-b border-primary/20">
                <div className="flex items-center gap-2 text-primary text-sm font-medium">
                    <Bot className="w-4 h-4" /> Asistente IA
                </div>
                <div className="flex items-center gap-3">
                    {messages.length > 0 && (
                        <button onClick={() => setMessages([])} className="text-xs text-muted-foreground hover:text-foreground transition">
                            Limpiar
                        </button>
                    )}
                    <Link href="/mi-equipo?tab=tareas" className="text-xs text-muted-foreground hover:text-foreground transition">
                        Ver tareas →
                    </Link>
                </div>
            </div>

            {/* Messages */}
            {messages.length > 0 && (
                <div className="px-5 py-4 space-y-4 max-h-72 overflow-y-auto">
                    {messages.map((msg, i) => (
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
                    {sending && (
                        <div className="flex gap-2.5 items-center">
                            <div className="p-1.5 rounded-lg bg-primary/20 flex-shrink-0">
                                <Bot className="w-3.5 h-3.5 text-primary" />
                            </div>
                            <div className="bg-background border border-border rounded-2xl rounded-tl-sm px-4 py-2.5">
                                <Loader2 className="w-4 h-4 animate-spin text-primary" />
                            </div>
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>
            )}

            {/* Pipeline de progreso de task activa */}
            <TaskProgressPipeline taskId={activeTaskId} active={sending} />

            {/* Sugerencias rápidas — solo sin mensajes */}
            {messages.length === 0 && (
                <div className="px-5 pt-4 pb-2 flex flex-wrap gap-2">
                    {SUGGESTIONS.map(s => (
                        <button key={s} onClick={() => send(s)} disabled={sending}
                            className="text-xs px-3 py-1.5 rounded-full bg-accent/50 border border-border text-muted-foreground hover:text-foreground hover:bg-accent transition disabled:opacity-40">
                            {s}
                        </button>
                    ))}
                </div>
            )}

            {/* Input */}
            <div className="px-5 py-4">
                <div className="flex bg-background border border-border rounded-xl overflow-hidden focus-within:border-primary transition-colors">
                    <input type="text" value={input}
                        onChange={e => setInput(e.target.value)}
                        onKeyDown={e => e.key === "Enter" && send(input)}
                        placeholder="Pregunta o pide algo a tu asistente IA..."
                        disabled={sending}
                        className="flex-1 bg-transparent border-none text-foreground text-sm px-4 py-3 focus:outline-none focus:ring-0 placeholder:text-muted-foreground" />
                    <button onClick={() => send(input)} disabled={sending || !input.trim()}
                        className="px-5 bg-primary hover:bg-primary text-foreground font-medium text-sm transition-colors disabled:opacity-50 flex items-center gap-2">
                        {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <MessageSquare className="w-4 h-4" />}
                        {sending ? "…" : "Enviar"}
                    </button>
                </div>
            </div>
        </div>
    );
}
