/**
 * UI.COST — modal post-abort que muestra tokens y coste estimado.
 *
 * Se dispara desde el botón "Detener" del chat: al cancelar la task,
 * se invoca `fetchTaskCost(taskId)` y se muestra este modal con el
 * desglose por agente.
 *
 * El coste es estimado a partir de `agent_execution_trace.cost_eur`
 * calculado en cada llamada al LLM. Si el provider no expone precio
 * (Claude Code, Ollama local), el coste será 0.
 */
"use client";

import { useEffect, useState } from "react";
import { Coins, Loader2, X } from "lucide-react";
import { fetchTaskCost, type TaskCost } from "@/lib/api/taskStream";

interface Props {
    taskId: string;
    /** Trigger reason — "cancelled" o "completed". Cambia el copy. */
    reason: "cancelled" | "completed";
    onClose: () => void;
}

export function CostModal({ taskId, reason, onClose }: Props) {
    const [data, setData] = useState<TaskCost | null>(null);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        fetchTaskCost(taskId)
            .then(setData)
            .catch((e: Error) => setError(e.message));
    }, [taskId]);

    return (
        <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="cost-modal-title"
            className="fixed inset-0 z-50 flex items-center justify-center bg-background/70 backdrop-blur-sm p-4"
            onClick={onClose}
        >
            <div
                className="bg-card border border-border rounded-2xl shadow-2xl max-w-md w-full overflow-hidden"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header */}
                <div className="flex items-center justify-between px-5 py-4 border-b border-border">
                    <div className="flex items-center gap-2.5">
                        <Coins className="w-4 h-4 text-primary" aria-hidden="true" />
                        <h2 id="cost-modal-title" className="text-sm font-semibold text-foreground">
                            {reason === "cancelled" ? "Generación detenida" : "Tarea completada"}
                        </h2>
                    </div>
                    <button
                        type="button"
                        onClick={onClose}
                        aria-label="Cerrar"
                        className="p-1 rounded text-muted-foreground hover:text-foreground hover:bg-background"
                    >
                        <X className="w-4 h-4" />
                    </button>
                </div>

                {/* Body */}
                <div className="p-5 space-y-4">
                    {error && (
                        <p role="alert" className="text-sm text-red-500">
                            No se pudo obtener el coste: {error}
                        </p>
                    )}
                    {!data && !error && (
                        <div className="flex items-center gap-2 text-muted-foreground text-sm">
                            <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
                            Calculando consumo…
                        </div>
                    )}
                    {data && (
                        <>
                            <p className="text-sm text-foreground leading-relaxed">
                                {reason === "cancelled" ? "Has detenido al agente. " : "El agente terminó. "}
                                Has consumido{" "}
                                <strong className="text-foreground">
                                    {data.tokens_total.toLocaleString("es-ES")} tokens
                                </strong>
                                {data.cost_eur > 0 && (
                                    <>
                                        {" "}
                                        (≈{" "}
                                        <strong className="text-foreground">
                                            {data.cost_eur.toLocaleString("es-ES", {
                                                style: "currency",
                                                currency: "EUR",
                                                minimumFractionDigits: 2,
                                                maximumFractionDigits: 4,
                                            })}
                                        </strong>
                                        )
                                    </>
                                )}
                                .
                            </p>

                            {data.agents.length > 0 && (
                                <section aria-labelledby="cost-agents-heading">
                                    <h3
                                        id="cost-agents-heading"
                                        className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1.5"
                                    >
                                        Desglose por agente
                                    </h3>
                                    <ul className="space-y-1">
                                        {data.agents.map((a) => (
                                            <li
                                                key={a.agent}
                                                className="flex items-center justify-between text-xs text-foreground bg-background border border-border rounded-md px-3 py-1.5"
                                            >
                                                <span className="font-medium">{a.agent}</span>
                                                <span className="tabular-nums text-muted-foreground">
                                                    {a.tokens.toLocaleString("es-ES")} tokens
                                                    {a.cost_eur > 0 &&
                                                        ` · ${a.cost_eur.toLocaleString("es-ES", {
                                                            style: "currency",
                                                            currency: "EUR",
                                                            minimumFractionDigits: 2,
                                                            maximumFractionDigits: 4,
                                                        })}`}
                                                </span>
                                            </li>
                                        ))}
                                    </ul>
                                </section>
                            )}

                            {data.cost_eur === 0 && data.tokens_total > 0 && (
                                <p className="text-[11px] text-muted-foreground italic leading-relaxed">
                                    El proveedor LLM activo no expone precio por token (Claude Code o
                                    proveedor local). El consumo en tokens sigue contabilizado.
                                </p>
                            )}
                        </>
                    )}
                </div>

                {/* Footer */}
                <div className="px-5 py-3 border-t border-border flex justify-end">
                    <button
                        type="button"
                        onClick={onClose}
                        className="px-4 py-2 rounded-md bg-primary text-foreground text-sm font-medium hover:bg-primary/90"
                    >
                        Entendido
                    </button>
                </div>
            </div>
        </div>
    );
}
