"use client";

import { useState } from "react";
import { AlertTriangle, MessageSquare, Loader2, Send } from "lucide-react";
import { executeTaskAndWait } from "../_hooks/useCompliance";
import { surfaceIfConnectivity } from "@/lib/api/errors";

export function ConsultaTab() {
    const [question, setQuestion] = useState("");
    const [loading, setLoading] = useState(false);
    const [statusText, setStatusText] = useState("");
    const [results, setResults] = useState<any>(null);
    const [error, setError] = useState<string | null>(null);

    async function submit(e: React.FormEvent) {
        e.preventDefault();
        if (!question.trim()) return;
        setLoading(true);
        setError(null);
        setResults(null);
        try {
            const data = await executeTaskAndWait(
                "compliance",
                question,
                (msg) => setStatusText(msg)
            );
            setResults(data);
        } catch (err: any) {
            if (surfaceIfConnectivity(err)) return;
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="max-w-2xl">
            <div className="rounded-xl border border-border bg-card p-6 mb-8">
                <h2 className="font-medium text-foreground mb-1">Consulta sobre obligaciones fiscales</h2>
                <p className="text-xs text-muted-foreground mb-4">
                    El agente responderá basándose en normativa española vigente. Para decisiones concretas, consulta siempre a tu asesor fiscal.
                </p>

                <form onSubmit={submit} className="space-y-4">
                    <textarea
                        rows={3}
                        required
                        value={question}
                        onChange={e => setQuestion(e.target.value)}
                        placeholder="Ej: ¿Tengo que presentar el modelo 303 si soy autónomo en módulos?"
                        className="w-full px-4 py-3 rounded-lg bg-card border border-border
                        text-foreground text-sm placeholder:text-muted-foreground resize-none
                        focus:outline-none focus:ring-2 focus:ring-primary transition"
                    />
                    <button
                        type="submit"
                        disabled={loading || !question.trim()}
                        className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-primary
                        hover:bg-primary disabled:opacity-50 text-foreground text-sm font-medium transition"
                    >
                        {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                        {loading ? "Calculando respuesta…" : "Enviar consulta"}
                    </button>
                </form>

                {loading && (
                    <div className="mt-6 flex flex-col items-center justify-center p-4 gap-3 bg-card/50 rounded-lg border border-border">
                        <Loader2 className="w-6 h-6 animate-spin text-primary" />
                        <p className="text-sm font-medium text-muted-foreground">{statusText || "Analizando el contexto normativo..."}</p>
                    </div>
                )}

                {error && (
                    <div className="mt-6 p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-center gap-2">
                        <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                        <div>
                            <p className="font-medium">Error al procesar la consulta:</p>
                            <p className="text-red-400/80 mt-1">{error}</p>
                        </div>
                    </div>
                )}
            </div>

            {results && results.respuesta_consulta && (
                <div className="rounded-xl border border-primary/20 bg-primary/5 p-6 shadow-lg shadow-primary/20">
                    <div className="flex items-center gap-3 mb-4">
                        <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
                            <MessageSquare className="w-4 h-4 text-primary" />
                        </div>
                        <div>
                            <h3 className="text-sm font-medium text-primary">Asesor IA dice:</h3>
                        </div>
                    </div>
                    <div className="text-sm text-foreground whitespace-pre-wrap leading-relaxed space-y-4">
                        {results.respuesta_consulta}
                    </div>

                    <div className="mt-6 pt-4 border-t border-primary/20">
                        <p className="text-xs text-primary/60 font-medium">Nota: Esta información es generada por IA y es de carácter orientativo.</p>
                    </div>
                </div>
            )}
        </div>
    );
}
