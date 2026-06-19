"use client";

import { Bot, Loader2, MessageSquare, Square } from "lucide-react";
import { useTranslations } from "next-intl";
import { AIDisclosureBanner } from "@/components/ai/AIDisclosureBanner";

interface ChatSectionProps {
    chatMessages: { role: "user" | "assistant"; content: string }[];
    setChatMessages: (msgs: { role: "user" | "assistant"; content: string }[]) => void;
    chatQuery: string;
    setChatQuery: (v: string) => void;
    chatLoading: boolean;
    onSend: () => void;
    /** UI.AGT — resumen del último evento de progreso recibido por SSE. */
    progressSummary?: string | null;
    /** UI.AGT — handler para botón "Detener" (solo visible si streaming). */
    onStop?: () => void;
    /** UI.AGT — true mientras llegan eventos del task. */
    isStreaming?: boolean;
}

export function ChatSection({
    chatMessages, setChatMessages, chatQuery, setChatQuery, chatLoading, onSend,
    progressSummary, onStop, isStreaming,
}: ChatSectionProps) {
    const t = useTranslations("miEquipo");
    return (
        <div className="mb-8 bg-card border border-primary/20 rounded-2xl overflow-hidden shadow-lg shadow-primary/20">
            <div className="px-5 pt-3">
                <AIDisclosureBanner domain="mi-equipo" />
            </div>
            <div className="flex items-center justify-between px-5 py-3 border-b border-primary/20">
                <div className="flex items-center gap-2 text-primary text-sm font-medium">
                    <Bot className="w-4 h-4" /> {t("chat.assistantTitle")}
                </div>
                {chatMessages.length > 0 && (
                    <button onClick={() => setChatMessages([])} className="text-xs text-muted-foreground hover:text-muted-foreground transition">
                        {t("chat.clearConversation")}
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
                        <div className="flex gap-2.5 items-start" aria-live="polite">
                            <div className="p-1.5 rounded-lg bg-primary/20 flex-shrink-0 mt-0.5">
                                <Bot className="w-3.5 h-3.5 text-primary" />
                            </div>
                            <div className="bg-background border border-border rounded-2xl rounded-tl-sm px-4 py-2.5 flex-1 max-w-[85%]">
                                <div className="flex items-center gap-2">
                                    <Loader2 className="w-4 h-4 animate-spin text-primary flex-shrink-0" />
                                    {progressSummary ? (
                                        <span className="text-sm text-muted-foreground truncate">{progressSummary}</span>
                                    ) : (
                                        // Skeleton de 2 líneas mientras no llega progress.
                                        <div className="flex-1 space-y-1.5">
                                            <div className="h-2 w-3/4 rounded bg-muted animate-pulse" />
                                            <div className="h-2 w-1/2 rounded bg-muted animate-pulse" />
                                        </div>
                                    )}
                                    {isStreaming && onStop && (
                                        <button
                                            type="button"
                                            onClick={onStop}
                                            aria-label={t("chat.stopAria")}
                                            className="ml-2 flex items-center gap-1 px-2 py-1 rounded-md border border-border text-xs text-muted-foreground hover:text-foreground hover:border-primary transition-colors flex-shrink-0"
                                        >
                                            <Square className="w-3 h-3" /> {t("chat.stop")}
                                        </button>
                                    )}
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            )}
            <div className="px-5 py-4">
                <div className="flex bg-background border border-border rounded-xl overflow-hidden focus-within:border-primary transition-colors">
                    <input type="text" value={chatQuery}
                        onChange={(e) => setChatQuery(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && onSend()}
                        placeholder={t("chat.inputPlaceholder")}
                        className="flex-1 bg-transparent border-none text-foreground text-sm px-4 py-3 focus:outline-none focus:ring-0 placeholder:text-muted-foreground" />
                    <button onClick={onSend} disabled={chatLoading || !chatQuery.trim()}
                        className="px-5 bg-primary hover:bg-primary text-foreground font-medium text-sm transition-colors disabled:opacity-50 flex items-center gap-2">
                        <MessageSquare className="w-4 h-4" />
                        {t("chat.send")}
                    </button>
                </div>
            </div>
        </div>
    );
}
