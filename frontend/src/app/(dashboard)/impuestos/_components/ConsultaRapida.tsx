"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api";
import { waitForTask, TaskTimeoutError } from "@/lib/api/tasks";
import { AlertTriangle, MessageSquare, Loader2, Send } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function ConsultaRapida() {
    const t = useTranslations("impuestos");
    const SUGGESTIONS = [
        t("consulta.suggestion1"),
        t("consulta.suggestion2"),
        t("consulta.suggestion3"),
        t("consulta.suggestion4"),
    ];
    const [question, setQuestion] = useState("");
    const [loading, setLoading] = useState(false);
    const [answer, setAnswer] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);

    async function submit(q: string) {
        const text = q || question;
        if (!text.trim()) return;
        setLoading(true);
        setError(null);
        setAnswer(null);
        setQuestion(text);
        try {
            const task = await api.tasks.create("compliance", text);
            const current = await waitForTask(task.id, { timeoutMs: 60_000, intervalMs: 2_000 });

            if (current.status === "done") {
                const results: any[] = current.agent_results || [];
                const out = results[results.length - 1]?.output || {};
                setAnswer(out.respuesta_consulta || out.resumen_boe || JSON.stringify(out, null, 2));
            } else {
                setError(current.error_message || t("consulta.noAnswer"));
            }
        } catch (err: any) {
            setError(err instanceof TaskTimeoutError ? t("consulta.noAnswer") : err.message);
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="space-y-4">
            <div className="flex flex-wrap gap-2">
                {SUGGESTIONS.map(s => (
                    <Button
                        key={s}
                        variant="outline"
                        size="sm"
                        onClick={() => submit(s)}
                        className="text-xs text-primary border-primary/20 bg-primary/10 hover:bg-primary/20"
                    >
                        {s}
                    </Button>
                ))}
            </div>

            <div className="flex gap-3">
                <Input
                    type="text"
                    value={question}
                    onChange={e => setQuestion(e.target.value)}
                    onKeyDown={e => e.key === "Enter" && submit(question)}
                    placeholder={t("consulta.placeholder")}
                    className="flex-1"
                />
                <Button
                    onClick={() => submit(question)}
                    disabled={loading || !question.trim()}
                    size="icon"
                 aria-label={t("consulta.sendAria")}>
                    {loading ? <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" /> : <Send className="w-4 h-4" aria-hidden="true" />}
                </Button>
            </div>

            {loading && (
                <div className="flex items-center gap-3 text-xs text-muted-foreground py-4">
                    <Loader2 className="w-4 h-4 animate-spin text-primary shrink-0" />
                    {t("consulta.analyzing")}
                </div>
            )}

            {error && (
                <Card className="border-red-500/20 bg-red-500/5">
                    <CardContent className="p-4 text-red-400 text-sm flex gap-2">
                        <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                        <span>{error}</span>
                    </CardContent>
                </Card>
            )}

            {answer && (
                <Card className="bg-primary/5 border-primary/20 relative overflow-hidden">
                    <CardContent className="p-5">
                        <div className="absolute top-0 right-0 p-3 opacity-5 pointer-events-none">
                            <MessageSquare className="w-24 h-24 text-primary" />
                        </div>
                        <div className="flex items-center gap-2 mb-3 text-xs font-semibold text-primary">
                            <div className="w-6 h-6 rounded-full bg-primary/20 flex items-center justify-center">
                                <MessageSquare className="w-3 h-3" />
                            </div>
                            {t("consulta.advisorName")}
                        </div>
                        <p className="text-sm text-foreground whitespace-pre-wrap leading-relaxed">{answer}</p>
                        <p className="text-xs text-muted-foreground mt-4 pt-3 border-t border-primary/20">
                            {t("consulta.disclaimer")}
                        </p>
                    </CardContent>
                </Card>
            )}
        </div>
    );
}
