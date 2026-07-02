"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { useAiChatStore } from "@/stores/aiChat";
import { Bot, Loader2, MessageSquare } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { TaskProgressPipeline } from "./TaskProgressPipeline";

export function AiChatBar() {
    const t = useTranslations("dashboard");
    const SUGGESTIONS = [
        t("aiChat.suggestion1"),
        t("aiChat.suggestion2"),
        t("aiChat.suggestion3"),
        t("aiChat.suggestion4"),
        t("aiChat.suggestion5"),
    ];
    const [input, setInput] = useState("");
    // Hilo ÚNICO compartido con el chat de mi-equipo (mismo dominio "chat").
    const { messages, sending, activeTaskId, setMessages, send: sendShared } = useAiChatStore();
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = useCallback(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, []);

    useEffect(() => { scrollToBottom(); }, [messages, scrollToBottom]);

    function send(text: string) {
        if (!text.trim() || sending) return;
        setInput("");
        void sendShared(text, {
            noResponse: t("aiChat.noResponse"),
            timeout: t("aiChat.timeout"),
            sendError: t("aiChat.sendError"),
        });
    }

    return (
        <div className="bg-card border border-primary/20 rounded-2xl overflow-hidden shadow-lg shadow-primary/20">
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-3 border-b border-primary/20">
                <div className="flex items-center gap-2 text-primary text-sm font-medium">
                    <Bot className="w-4 h-4" /> {t("aiChat.title")}
                </div>
                <div className="flex items-center gap-3">
                    {messages.length > 0 && (
                        <button onClick={() => setMessages([])} className="text-xs text-muted-foreground hover:text-foreground transition">
                            {t("aiChat.clear")}
                        </button>
                    )}
                    <Link href="/mi-equipo?tab=tareas" className="text-xs text-muted-foreground hover:text-foreground transition">
                        {t("aiChat.viewTasks")}
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
                        placeholder={t("aiChat.placeholder")}
                        disabled={sending}
                        className="flex-1 bg-transparent border-none text-foreground text-sm px-4 py-3 focus:outline-none focus:ring-0 placeholder:text-muted-foreground" />
                    <button onClick={() => send(input)} disabled={sending || !input.trim()}
                        className="px-5 bg-primary hover:bg-primary text-foreground font-medium text-sm transition-colors disabled:opacity-50 flex items-center gap-2">
                        {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <MessageSquare className="w-4 h-4" />}
                        {sending ? "…" : t("aiChat.send")}
                    </button>
                </div>
            </div>
        </div>
    );
}
