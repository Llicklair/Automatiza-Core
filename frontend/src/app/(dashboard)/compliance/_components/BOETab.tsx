"use client";

import { useState } from "react";
import { AlertTriangle, Newspaper, MessageSquare, Loader2 } from "lucide-react";
import { executeTaskAndWait } from "../_hooks/useCompliance";

export function BOETab() {
    const [loading, setLoading] = useState(false);
    const [statusText, setStatusText] = useState("");
    const [triggered, setTriggered] = useState(false);
    const [results, setResults] = useState<any>(null);
    const [error, setError] = useState<string | null>(null);

    async function fetchBOE() {
        setLoading(true); setTriggered(true); setError(null);
        try {
            const data = await executeTaskAndWait(
                "compliance",
                "novedades BOE regulación fiscal pyme",
                (msg) => setStatusText(msg)
            );
            setResults(data);
        } catch (err: any) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="space-y-6">
            {!triggered && !results && !error ? (
                <div className="flex flex-col items-center justify-center py-20 text-center">
                    <Newspaper className="w-12 h-12 text-muted-foreground mb-4" />
                    <p className="text-foreground font-medium mb-2">Novedades del BOE</p>
                    <p className="text-sm text-muted-foreground mb-6 max-w-sm">
                        El agente consultará el BOE y te resumirá las novedades relevantes para tu empresa
                    </p>
                    <button
                        onClick={fetchBOE}
                        className="px-6 py-2.5 rounded-lg bg-primary hover:bg-primary text-foreground text-sm font-medium transition"
                    >
                        Consultar novedades
                    </button>
                </div>
            ) : (
                <div className="rounded-xl border border-border bg-card p-6">
                    {loading ? (
                        <div className="flex flex-col items-center justify-center py-10 gap-4 text-muted-foreground">
                            <Loader2 className="w-8 h-8 animate-spin text-primary" />
                            <p className="text-sm font-medium">{statusText || "El agente está conectando con el BOE..."}</p>
                            <p className="text-xs text-muted-foreground max-w-xs text-center">
                                Esto puede tardar unos segundos mientras la IA lee y resume el Boletín Oficial del Estado.
                            </p>
                        </div>
                    ) : error ? (
                        <div className="space-y-4">
                            <p className="text-red-400 text-sm font-medium flex items-center gap-2">
                                <AlertTriangle className="w-4 h-4" /> Error al consultar el BOE
                            </p>
                            <p className="text-muted-foreground text-sm">{error}</p>
                            <button
                                onClick={() => { setTriggered(false); setError(null); }}
                                className="text-xs text-primary hover:text-primary transition"
                            >
                                Volver a intentar
                            </button>
                        </div>
                    ) : results ? (
                        <div className="space-y-6">
                            <div>
                                <h3 className="text-foreground font-medium mb-2 flex items-center gap-2">
                                    <MessageSquare className="w-4 h-4 text-primary" />
                                    Resumen del Asesor (IA)
                                </h3>
                                <div className="p-4 bg-card rounded-lg border border-border">
                                    <p className="text-sm text-foreground whitespace-pre-wrap leading-relaxed">
                                        {results.resumen_boe || "No hay resumen disponible."}
                                    </p>
                                </div>
                            </div>

                            {results.boe_novedades && results.boe_novedades.length > 0 && (
                                <div>
                                    <h3 className="text-sm font-medium text-muted-foreground mb-3">
                                        Fuentes Originales ({results.boe_novedades.length})
                                    </h3>
                                    <ul className="space-y-3">
                                        {results.boe_novedades.map((norma: any, i: number) => (
                                            <li key={i} className="flex flex-col gap-1 p-3 rounded-md bg-card/50 border border-border">
                                                <a
                                                    href={norma.url}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className="text-sm font-medium text-primary hover:underline"
                                                >
                                                    {norma.titulo}
                                                </a>
                                                <p className="text-xs text-muted-foreground line-clamp-2">
                                                    {norma.descripcion}
                                                </p>
                                                <div className="flex gap-2 mt-1">
                                                    <span className="text-[10px] text-muted-foreground font-mono">{norma.identificador}</span>
                                                    <span className="text-[10px] text-muted-foreground">{norma.fecha}</span>
                                                </div>
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}

                            <button
                                onClick={fetchBOE}
                                className="text-xs text-muted-foreground hover:text-foreground transition mt-4"
                            >
                                Actualizar de nuevo
                            </button>
                        </div>
                    ) : null}
                </div>
            )}
        </div>
    );
}
