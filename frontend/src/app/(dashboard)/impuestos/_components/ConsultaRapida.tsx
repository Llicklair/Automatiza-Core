"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { AlertTriangle, MessageSquare, Loader2, Send } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const SUGGESTIONS = [
    "¿Cuándo debo presentar el modelo 303?",
    "¿Qué es el modelo 130 y para qué sirve?",
    "¿Tengo que presentar el modelo 347 si facturo más de 3.005€?",
    "¿Cuál es el plazo para el IRPF como autónomo?",
];

export function ConsultaRapida() {
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
            let current = task;
            let tries = 0;

            while ((current.status === "pending" || current.status === "executing") && tries < 30) {
                await new Promise(r => setTimeout(r, 2000));
                current = await api.tasks.get(task.id);
                tries++;
            }

            if (current.status === "done") {
                const results: any[] = current.agent_results || [];
                const out = results[results.length - 1]?.output || {};
                setAnswer(out.respuesta_consulta || out.resumen_boe || JSON.stringify(out, null, 2));
            } else {
                setError(current.error_message || "No se pudo obtener respuesta.");
            }
        } catch (err: any) {
            setError(err.message);
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
                    placeholder="Escribe tu consulta fiscal..."
                    className="flex-1"
                />
                <Button
                    onClick={() => submit(question)}
                    disabled={loading || !question.trim()}
                    size="icon"
                 aria-label="Enviar consulta">
                    {loading ? <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" /> : <Send className="w-4 h-4" aria-hidden="true" />}
                </Button>
            </div>

            {loading && (
                <div className="flex items-center gap-3 text-xs text-muted-foreground py-4">
                    <Loader2 className="w-4 h-4 animate-spin text-primary shrink-0" />
                    El agente fiscal está analizando tu consulta...
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
                            Asesor Fiscal IA
                        </div>
                        <p className="text-sm text-foreground whitespace-pre-wrap leading-relaxed">{answer}</p>
                        <p className="text-xs text-muted-foreground mt-4 pt-3 border-t border-primary/20">
                            Información orientativa generada por IA. Consulta siempre con tu asesor fiscal.
                        </p>
                    </CardContent>
                </Card>
            )}
        </div>
    );
}
