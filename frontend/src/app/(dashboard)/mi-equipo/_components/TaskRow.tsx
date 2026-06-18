"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import type { Task } from "@/lib/api";
import { X, ChevronDown, Loader2, Copy, Check, MessageSquare } from "lucide-react";
import { getAllDomainOptions, STATUS_COLOR, getStatusLabel, STATUS_ICON, getChatResponse } from "./task-constants";
import { ChatBubble } from "./ChatBubble";

export function TaskRow({ task, cancelTask, onReply }: {
    task: Task;
    cancelTask: (id: string) => void;
    onReply: (parentTaskId: string, domain: string, reply: string) => Promise<void>;
}) {
    const t = useTranslations("miEquipo");
    const tc = useTranslations("common");
    const chatResponse = getChatResponse(task);
    const [open, setOpen] = useState(!!chatResponse);
    const [copied, setCopied] = useState(false);
    const [replyText, setReplyText] = useState("");
    const [replying, setReplying] = useState(false);
    const hasDetail = chatResponse || task.plan || task.agent_results;
    const STATUS_LABEL = getStatusLabel(t);
    const domain = getAllDomainOptions(t).find(d => d.value === task.domain);
    // Mostrar input de respuesta cuando el agente lanzó una pregunta
    const canReply = task.domain !== "chat" && task.status === "done" && !!chatResponse;

    async function handleReply() {
        if (!replyText.trim() || replying) return;
        setReplying(true);
        try {
            await onReply(task.id, task.domain, replyText.trim());
            setReplyText("");
        } finally {
            setReplying(false);
        }
    }

    const copyPrompt = (e: React.MouseEvent) => {
        e.stopPropagation();
        navigator.clipboard.writeText(task.user_intent).then(() => {
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        });
    };

    return (
        <div className="border-b border-border last:border-0 hover:bg-accent/50 transition">
            <div
                className={`grid grid-cols-12 gap-4 px-6 py-4 items-center ${hasDetail ? "cursor-pointer" : ""}`}
                onClick={() => hasDetail && setOpen(!open)}
            >
                <div className="col-span-5 min-w-0">
                    <p className="text-sm text-foreground truncate">{task.user_intent}</p>
                    <p className="text-xs text-muted-foreground mt-0.5 font-mono">{task.id.slice(0, 8)}…</p>
                </div>
                <div className="col-span-2">
                    <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded-md">
                        {domain?.label ?? task.domain}
                    </span>
                </div>
                <div className="col-span-2">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium border flex items-center gap-1.5 w-fit ${STATUS_COLOR[task.status] ?? "text-muted-foreground"}`}>
                        {STATUS_ICON[task.status]}
                        {STATUS_LABEL[task.status] ?? task.status}
                    </span>
                </div>
                <div className="col-span-2 text-xs text-muted-foreground">
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
                            className="text-muted-foreground hover:text-red-400 transition p-1 rounded"
                            title={tc("cancel")}
                        >
                            <X className="w-4 h-4" />
                        </button>
                    )}
                    {Boolean(hasDetail) && (
                        <ChevronDown className={`w-4 h-4 text-muted-foreground transition-transform duration-300 ${open ? "rotate-180" : ""}`} />
                    )}
                </div>
            </div>

            {/* Detalles expandibles */}
            {Boolean(hasDetail) && (
                <div className={`grid transition-[grid-template-rows,opacity] duration-300 ease-in-out ${open ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0"}`}>
                    <div className="overflow-hidden">

                        {/* -- Vista chat: burbuja conversacional -- */}
                        {chatResponse ? (
                            <>
                                <ChatBubble text={chatResponse} />
                                {canReply && (
                                    <div className="px-6 pb-5">
                                        <div className="flex gap-2">
                                            <input
                                                type="text"
                                                value={replyText}
                                                onChange={e => setReplyText(e.target.value)}
                                                onKeyDown={e => e.key === "Enter" && handleReply()}
                                                placeholder={t("taskRow.replyPlaceholder")}
                                                disabled={replying}
                                                className="flex-1 bg-background border border-primary/30 rounded-xl px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary transition"
                                            />
                                            <button
                                                onClick={handleReply}
                                                disabled={replying || !replyText.trim()}
                                                className="px-4 py-2.5 bg-primary rounded-xl text-foreground text-sm font-medium disabled:opacity-50 flex items-center gap-2 transition"
                                            >
                                                {replying ? <Loader2 className="w-4 h-4 animate-spin" /> : <MessageSquare className="w-4 h-4" />}
                                                {replying ? t("taskRow.sending") : t("taskRow.reply")}
                                            </button>
                                        </div>
                                    </div>
                                )}
                            </>
                        ) : (
                        <div className="px-6 pb-6 pt-2 border-t border-border/50 space-y-4">

                            {/* -- Prompt completo del usuario -- */}
                            <div className="rounded-xl border border-primary/20 bg-primary/5 overflow-hidden">
                                <div className="px-4 py-2.5 border-b border-primary/20 bg-primary/10 flex items-center justify-between">
                                    <h4 className="text-xs font-semibold text-primary uppercase tracking-wider flex items-center gap-2">
                                        <MessageSquare className="w-3 h-3" /> {t("taskRow.userPrompt")}
                                    </h4>
                                    <button
                                        onClick={copyPrompt}
                                        className="flex items-center gap-1.5 text-[11px] text-primary hover:text-foreground transition px-2 py-1 rounded-md hover:bg-primary/20"
                                        title={t("taskRow.copyPrompt")}
                                    >
                                        {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                                        {copied ? t("taskRow.copied") : t("taskRow.copy")}
                                    </button>
                                </div>
                                <p className="px-4 py-3 text-sm text-primary-foreground/90 leading-relaxed whitespace-pre-wrap">
                                    {task.user_intent}
                                </p>
                            </div>

                            {Boolean(task.error_message) && (
                                <div className="p-4 rounded-xl bg-red-500/10 text-sm border border-red-500/20 flex items-start gap-3">
                                    <div className="p-1 bg-red-500/20 rounded-lg">
                                        <X className="w-4 h-4 text-red-400 flex-shrink-0" />
                                    </div>
                                    <div>
                                        <p className="font-semibold text-red-400 mb-0.5">{t("taskRow.executionError")}</p>
                                        <p className="text-red-300/80 leading-relaxed">{task.error_message}</p>
                                    </div>
                                </div>
                            )}

                            <div className="grid grid-cols-2 gap-6">
                                {Boolean(task.plan) && (
                                    <div className="bg-card rounded-xl border border-border overflow-hidden flex flex-col">
                                        <div className="px-4 py-3 border-b border-border bg-muted">
                                            <h4 className="text-xs font-semibold text-foreground uppercase tracking-wider flex items-center gap-2">
                                                <span className="w-2 h-2 rounded-full bg-blue-500"></span> {t("taskRow.executionPlan")}
                                            </h4>
                                        </div>
                                        <div className="p-4 overflow-x-auto text-xs font-mono text-muted-foreground flex-1">
                                            {Array.isArray(task.plan) ? (
                                                <div className="space-y-3">
                                                    {(task.plan as any[]).map((step: any, i) => (
                                                        <div key={i} className="flex gap-3">
                                                            <div className="flex flex-col items-center">
                                                                <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] ${step.status === 'done' ? 'bg-emerald-500/20 text-emerald-400' : step.status === 'failed' ? 'bg-red-500/20 text-red-400' : 'bg-accent text-muted-foreground'}`}>
                                                                    {i + 1}
                                                                </div>
                                                                {i < (task.plan as any[]).length - 1 && <div className="w-px h-full bg-border my-1"></div>}
                                                            </div>
                                                            <div className="pb-3">
                                                                <p className="text-foreground font-medium mb-1 capitalize">{step.action?.replace(/_/g, ' ')}</p>
                                                                <p className="text-muted-foreground text-[11px]">{t("taskRow.agentLabel")} <span className="text-primary font-medium">{step.agent}</span></p>
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
                                    <div className="bg-card rounded-xl border border-border overflow-hidden flex flex-col">
                                        <div className="px-4 py-3 border-b border-border bg-muted">
                                            <h4 className="text-xs font-semibold text-foreground uppercase tracking-wider flex items-center gap-2">
                                                <span className="w-2 h-2 rounded-full bg-primary"></span> {t("taskRow.agentResult")}
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
                                                            <p className="text-sm text-foreground leading-relaxed">
                                                                {res.summary || (res.error ? `❌ ${res.error}` : (typeof res.output === 'string' ? res.output : t("taskRow.completed")))}
                                                            </p>
                                                        </div>
                                                    ))}
                                                </div>
                                            ) : (
                                                <p className="text-xs text-muted-foreground italic">{t("taskRow.noResults")}</p>
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
