"use client";

import {
    Zap, PlayCircle, Loader2, X,
    ChevronDown, ChevronUp, Activity,
    BrainCircuit, Pause, Cpu, GitFork,
    RotateCw, Pencil, StopCircle, MessageSquare, Send,
} from "lucide-react";
import { Workflow, WorkflowExecution } from "@/lib/api";
import { TRIGGER_CONFIG, EXEC_STATUS, hasFanOut } from "./constants";
import { useWorkflowExecution, formatElapsed } from "../_hooks/useWorkflowExecution";

interface WorkflowCardProps {
    wf: Workflow;
    isExpanded: boolean;
    wfExecs: WorkflowExecution[];
    runningId: string | null;
    loadingExec: string | null;
    refreshingExec: string | null;
    contextInputId: string | null;
    contextText: string;
    liveLogs: Record<string, string[]>;
    onToggleExpand: (id: string) => void;
    onRun: (id: string) => void;
    onDelete: (id: string) => void;
    onEdit: (wf: Workflow) => void;
    onToggleStatus: (wf: Workflow) => void;
    onRefreshExecutions: (e: React.MouseEvent, id: string) => void;
    onCancel: (workflowId: string, executionId: string) => void;
    onResume: (workflowId: string, executionId: string) => void;
    onContextInputToggle: (id: string) => void;
    onContextTextChange: (text: string) => void;
    onRunWithContext: (id: string) => void;
}

export default function WorkflowCard({
    wf, isExpanded, wfExecs, runningId, loadingExec, refreshingExec,
    contextInputId, contextText, liveLogs,
    onToggleExpand, onRun, onDelete, onEdit, onToggleStatus,
    onRefreshExecutions, onCancel, onResume,
    onContextInputToggle, onContextTextChange, onRunWithContext,
}: WorkflowCardProps) {
    const activeExec = wfExecs.find(e => e.status === "running" || e.status === "paused");
    // Runtime info por nodo (WS): timer en vivo, agente, instrucción.
    const rt = useWorkflowExecution(activeExec?.id || null);
    const lastExec = wfExecs[0];

    // Construir capas de nodos para el mapa visual
    const nodeLayers: any[][] = (() => {
        if (wf.ui_nodes && wf.ui_nodes.length > 0) {
            const sorted = [...wf.ui_nodes].sort((a: any, b: any) => (a.position?.y ?? 0) - (b.position?.y ?? 0));
            const layers: any[][] = [];
            let current: any[] = [];
            let lastY = -9999;
            for (const nd of sorted) {
                const y = nd.position?.y ?? 0;
                if (y - lastY > 60 && current.length > 0) { layers.push(current); current = []; }
                current.push(nd);
                lastY = y;
            }
            if (current.length > 0) layers.push(current);
            return layers;
        }
        const triggerDesc = wf.trigger_config?.events
            ? `Evento: ${(wf.trigger_config.events as string[]).join(", ")}`
            : wf.trigger_config?.cron
                ? `Cron: ${wf.trigger_config.cron}`
                : "Inicio de la automatización";
        return [
            [{ id: "trigger", type: "trigger", data: { label: TRIGGER_CONFIG[wf.trigger_type]?.label ?? wf.trigger_type, description: triggerDesc } }],
            [{ id: "agent", type: "skill", data: { label: "Agente IA", description: wf.action_config?.instruction || "Ejecutar automatización" } }],
        ];
    })();

    return (
        <div className="bg-card border border-border rounded-2xl overflow-hidden hover:border-primary/30 transition-all group relative flex flex-col">
            <div className="absolute -top-16 -right-16 w-32 h-32 bg-primary/10 rounded-full blur-3xl group-hover:bg-primary/15 transition-all pointer-events-none" />

            {/* Cabecera */}
            <div className="px-5 pt-4 pb-3 relative z-10">
                <div className="flex items-start justify-between gap-2 mb-2">
                    <div className="flex-1 min-w-0">
                        <h3 className="text-sm font-semibold text-foreground truncate leading-tight">{wf.name}</h3>
                        {wf.action_config?.instruction ? (
                            <p className="text-[11px] text-muted-foreground mt-0.5 line-clamp-1 italic">
                                &ldquo;{wf.action_config.instruction}&rdquo;
                            </p>
                        ) : wf.description && (
                            <p className="text-[11px] text-muted-foreground mt-0.5 line-clamp-1">{wf.description}</p>
                        )}
                    </div>
                    <div className="flex items-center gap-1.5 flex-shrink-0 mt-0.5">
                        {lastExec && (
                            <span className={`text-[10px] px-1.5 py-0.5 rounded border font-medium ${(EXEC_STATUS[lastExec.status] ?? EXEC_STATUS.pending).cls}`}>
                                {(EXEC_STATUS[lastExec.status] ?? EXEC_STATUS.pending).label}
                            </span>
                        )}
                        <button onClick={() => onContextInputToggle(wf.id)} disabled={!wf.is_active}
                            className={`p-1.5 bg-muted rounded-lg transition-colors disabled:opacity-40 ${contextInputId === wf.id ? "text-primary bg-primary/10" : "text-muted-foreground hover:text-primary hover:bg-primary/10"}`}
                            title="Ejecutar con contexto">
                            <MessageSquare className="w-4 h-4" />
                        </button>
                        <button onClick={() => onRun(wf.id)} disabled={runningId === wf.id || !wf.is_active}
                            className="p-1.5 text-muted-foreground hover:text-emerald-400 bg-muted hover:bg-emerald-400/10 rounded-lg transition-colors disabled:opacity-40" title="Ejecutar ahora">
                            {runningId === wf.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <PlayCircle className="w-4 h-4" />}
                        </button>
                        <button onClick={() => onEdit(wf)} className="p-1.5 text-muted-foreground hover:text-primary bg-muted hover:bg-primary/10 rounded-lg transition-colors" title="Editar">
                            <Pencil className="w-3.5 h-3.5" />
                        </button>
                        <button onClick={() => onDelete(wf.id)} className="p-1.5 text-muted-foreground hover:text-red-400 bg-muted hover:bg-red-400/10 rounded-lg transition-colors" title="Eliminar">
                            <X className="w-4 h-4" />
                        </button>
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    <button onClick={() => onToggleStatus(wf)}
                        className={`w-8 h-4 rounded-full transition-colors flex items-center px-0.5 flex-shrink-0 ${wf.is_active ? "bg-primary" : "bg-accent"}`}
                        title={wf.is_active ? "Desactivar" : "Activar"}>
                        <div className={`w-3 h-3 rounded-full bg-white transition-transform ${wf.is_active ? "translate-x-4" : "translate-x-0"}`} />
                    </button>
                    <span className={`text-[11px] ${wf.is_active ? "text-primary" : "text-muted-foreground"}`}>
                        {wf.is_active ? "Activa" : "Pausada"}
                    </span>
                    <span className="text-muted-foreground/60">·</span>
                    {(() => {
                        const tc = TRIGGER_CONFIG[wf.trigger_type];
                        if (!tc) return <span className="text-[11px] text-muted-foreground">{wf.trigger_type}</span>;
                        const TIcon = tc.icon;
                        return (
                            <span className={`flex items-center gap-0.5 text-[10px] px-1.5 py-0.5 rounded-full border font-semibold ${tc.cls}`} title={tc.title}>
                                <TIcon className="w-2.5 h-2.5" />
                                {tc.label}
                            </span>
                        );
                    })()}
                    <span className="text-muted-foreground/60">·</span>
                    {wf.execution_mode === "deterministic" ? (
                        <span className="flex items-center gap-0.5 text-[10px] px-1.5 py-0.5 rounded-full border font-semibold text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
                            title="Los pasos están precompilados. Se ejecutan sin LLM, con coste cero y velocidad máxima.">
                            <Cpu className="w-2.5 h-2.5" /> Determinista
                        </span>
                    ) : (
                        <span className="flex items-center gap-0.5 text-[10px] px-1.5 py-0.5 rounded-full border font-semibold text-blue-400 bg-blue-500/10 border-blue-500/20"
                            title="El orquestador LLM interpreta la instrucción en tiempo real en cada ejecución.">
                            <BrainCircuit className="w-2.5 h-2.5" /> Con IA
                        </span>
                    )}
                    {hasFanOut(wf.ui_edges) && (
                        <>
                            <span className="text-muted-foreground/60">·</span>
                            <span className="flex items-center gap-0.5 text-[10px] px-1.5 py-0.5 rounded-full border font-semibold text-violet-400 bg-violet-500/10 border-violet-500/20"
                                title="Este workflow ejecuta ramas en paralelo mediante asyncio.gather">
                                <GitFork className="w-2.5 h-2.5" /> Paralelo
                            </span>
                        </>
                    )}
                    {activeExec && (
                        <>
                            <span className="text-muted-foreground/60">·</span>
                            <span className="flex items-center gap-1 text-[11px] text-blue-400">
                                <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
                                {activeExec.status === "paused" ? "Pausada" : "Ejecutando"}
                            </span>
                        </>
                    )}
                </div>
            </div>

            {/* Input de contexto */}
            {contextInputId === wf.id && (
                <div className="px-5 pb-3 pt-2 border-t border-primary/20 bg-primary/[0.03]">
                    <p className="text-[10px] text-primary mb-1.5 flex items-center gap-1">
                        <MessageSquare className="w-3 h-3" /> Contexto adicional para esta ejecución
                    </p>
                    <div className="flex gap-2">
                        <input type="text" value={contextText} onChange={e => onContextTextChange(e.target.value)}
                            onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) onRunWithContext(wf.id); }}
                            placeholder="Ej: Solo facturas del cliente Acme S.L."
                            className="flex-1 bg-background border border-border rounded-lg px-3 py-1.5 text-foreground text-xs focus:outline-none focus:border-primary transition placeholder:text-muted-foreground/60"
                            autoFocus />
                        <button onClick={() => onRunWithContext(wf.id)} disabled={runningId === wf.id}
                            className="px-3 py-1.5 bg-primary hover:bg-primary text-foreground rounded-lg text-xs font-medium transition disabled:opacity-50 flex items-center gap-1">
                            {runningId === wf.id ? <Loader2 className="w-3 h-3 animate-spin" /> : <Send className="w-3 h-3" />}
                            Lanzar
                        </button>
                    </div>
                </div>
            )}

            {/* Mapa de nodos */}
            <div className="px-5 pb-5 pt-1 border-t border-border space-y-0">
                {nodeLayers.map((layer, layerIdx) => {
                    const prevLayer = nodeLayers[layerIdx - 1];
                    const prevCompleted = prevLayer?.every((n: any) =>
                        activeExec?.node_states?.[n.id]?.status === "completed"
                    );
                    return (
                        <div key={layerIdx}>
                            {layerIdx > 0 && (
                                <div className="flex justify-center items-center py-0" style={{ height: 28 }}>
                                    <div className="flex flex-col items-center">
                                        <div className={`w-px h-3 ${prevCompleted ? "bg-emerald-600/70" : "bg-accent"}`} />
                                        <div className={`w-2 h-2 rounded-full border-2 ${prevCompleted ? "border-emerald-600 bg-emerald-600/30" : "border-border bg-muted"}`} />
                                        <div className={`w-px h-3 ${prevCompleted ? "bg-emerald-600/70" : "bg-accent"}`} />
                                    </div>
                                </div>
                            )}
                            <div className={`flex gap-2 ${layerIdx === 0 ? "mt-3" : ""}`}>
                                {layer.map((node: any) => {
                                    const ns = activeExec?.node_states?.[node.id];
                                    const status = ns?.status;
                                    const isCurrentNode = activeExec?.current_node_id === node.id;
                                    const isRunning = status === "running" || isCurrentNode;
                                    const isDone = status === "completed";
                                    const isFailed = status === "failed";
                                    const isPausedNode = status === "paused";
                                    const isTrigger = node.type === "trigger";

                                    const cardBorder = isRunning ? "border-blue-500/50"
                                        : isDone ? "border-emerald-500/30"
                                        : isFailed ? "border-red-500/40"
                                        : isPausedNode ? "border-orange-500/40"
                                        : isTrigger ? "border-primary/20"
                                        : "border-border";

                                    const cardBg = isRunning ? "bg-blue-500/[0.04]"
                                        : isDone ? "bg-emerald-500/[0.03]"
                                        : "bg-background";

                                    const iconCls = isTrigger ? "bg-primary/10 text-primary"
                                        : isRunning ? "bg-blue-500/10 text-blue-400"
                                        : isDone ? "bg-emerald-500/10 text-emerald-400"
                                        : isFailed ? "bg-red-500/10 text-red-400"
                                        : isPausedNode ? "bg-orange-500/10 text-orange-400"
                                        : "bg-muted text-muted-foreground";

                                    const TriggerIcon = TRIGGER_CONFIG[wf.trigger_type]?.icon ?? Zap;
                                    const Icon = isTrigger ? TriggerIcon : BrainCircuit;
                                    const description = node.data?.description || node.data?.action || (isTrigger ? "Escuchando evento..." : "Procesando...");

                                    return (
                                        <div key={node.id} className={`flex-1 rounded-xl px-3 py-2.5 border ${cardBorder} ${cardBg} relative overflow-hidden transition-all`}>
                                            {isRunning && <div className="absolute inset-0 animate-pulse bg-blue-500/[0.06] pointer-events-none" />}
                                            <div className="flex items-start gap-2.5 relative">
                                                <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5 ${iconCls}`}>
                                                    <Icon className="w-3.5 h-3.5" />
                                                </div>
                                                <div className="flex-1 min-w-0">
                                                    <div className="flex items-center justify-between gap-1 mb-0.5">
                                                        <span className="text-xs font-semibold text-foreground leading-tight truncate">
                                                            {node.data?.label || node.type}
                                                        </span>
                                                        {status && (
                                                            <span className={`text-[9px] font-semibold flex-shrink-0 ${isRunning ? "text-blue-400" : isDone ? "text-emerald-400" : isFailed ? "text-red-400" : isPausedNode ? "text-orange-400" : "text-muted-foreground"}`}>
                                                                {isRunning ? "Ejecutando" : isDone ? "Completado" : isFailed ? "Error" : isPausedNode ? "Pausado" : status}
                                                            </span>
                                                        )}
                                                    </div>
                                                    <p className="text-[11px] text-muted-foreground leading-snug line-clamp-2">{description}</p>
                                                    {/* Runtime real-time WS info: agente, timer en vivo, instrucción */}
                                                    {rt[node.id] && (
                                                        <div className="mt-1.5 space-y-0.5">
                                                            {rt[node.id].status === "running" && (
                                                                <>
                                                                    <div className="flex items-center gap-1.5 text-[10px]">
                                                                        <Loader2 className="w-3 h-3 animate-spin text-blue-400" />
                                                                        <span className="font-semibold text-blue-300">{rt[node.id].agent || node.type}</span>
                                                                        <span className="text-blue-400/80">· {formatElapsed(rt[node.id].elapsedMs)}</span>
                                                                    </div>
                                                                    {rt[node.id].instruction && (
                                                                        <p className="text-[9px] text-blue-200/70 italic truncate">
                                                                            “{rt[node.id].instruction}”
                                                                        </p>
                                                                    )}
                                                                </>
                                                            )}
                                                            {rt[node.id].status === "completed" && (
                                                                <div className="flex items-center gap-1.5 text-[10px] text-emerald-300/80">
                                                                    <span>✓ {formatElapsed(rt[node.id].elapsedMs)}</span>
                                                                    {rt[node.id].resultSummary && (
                                                                        <span className="truncate">· {rt[node.id].resultSummary}</span>
                                                                    )}
                                                                </div>
                                                            )}
                                                            {rt[node.id].status === "failed" && (
                                                                <div className="flex items-center gap-1.5 text-[10px] text-red-300">
                                                                    <span>✗ {formatElapsed(rt[node.id].elapsedMs)}</span>
                                                                    {rt[node.id].error && (
                                                                        <span className="truncate">· {rt[node.id].error}</span>
                                                                    )}
                                                                </div>
                                                            )}
                                                        </div>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    );
                })}

                {/* Botones de acción en ejecución activa */}
                {activeExec && (
                    <div className="mt-3 flex justify-center gap-2">
                        {activeExec.status === "paused" && (
                            <button onClick={() => onResume(wf.id, activeExec.id)}
                                className="flex items-center gap-1.5 px-4 py-1.5 bg-orange-500/10 hover:bg-orange-500/20 text-orange-400 rounded-full text-xs font-semibold transition-colors border border-orange-500/20">
                                <Pause className="w-3 h-3" /> Reanudar ejecución
                            </button>
                        )}
                        {(() => {
                            const runningMins = (Date.now() - new Date(activeExec.started_at).getTime()) / 60000;
                            if (activeExec.status === "running" && runningMins >= 2) {
                                return (
                                    <button onClick={() => onCancel(wf.id, activeExec.id)}
                                        className="flex items-center gap-1.5 px-4 py-1.5 bg-red-500/10 hover:bg-red-500/20 text-red-400 rounded-full text-xs font-semibold transition-colors border border-red-500/20">
                                        <StopCircle className="w-3 h-3" /> Cancelar ejecución
                                    </button>
                                );
                            }
                            return null;
                        })()}
                    </div>
                )}
            </div>

            {/* Toggle historial */}
            <button onClick={() => onToggleExpand(wf.id)}
                className="w-full flex items-center justify-between px-5 py-2.5 border-t border-border hover:bg-accent/50 transition text-xs text-muted-foreground hover:text-foreground mt-auto">
                <span className="flex items-center gap-1.5">
                    <Activity className="w-3.5 h-3.5" /> Historial de ejecuciones
                    {wfExecs.length > 0 && (
                        <span className="bg-muted text-muted-foreground rounded-full px-1.5 py-0.5 text-[10px] font-medium">{wfExecs.length}</span>
                    )}
                </span>
                {loadingExec === wf.id
                    ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    : isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />
                }
            </button>

            {/* Historial expandible */}
            {isExpanded && (
                <div className="border-t border-border bg-background max-h-64 overflow-y-auto">
                    <div className="px-5 py-3 border-b border-border bg-card flex justify-between items-center sticky top-0 z-10">
                        <h4 className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">Últimas Ejecuciones</h4>
                        <button type="button" onClick={(e) => onRefreshExecutions(e, wf.id)} disabled={refreshingExec === wf.id}
                            className="text-[11px] text-muted-foreground hover:text-foreground flex items-center gap-1 transition disabled:opacity-50">
                            {refreshingExec === wf.id ? <Loader2 className="w-3 h-3 animate-spin" /> : <RotateCw className="w-3 h-3" />}
                            Actualizar
                        </button>
                    </div>
                    {wfExecs.length === 0 ? (
                        <div className="py-8 text-center text-xs text-muted-foreground/60 flex flex-col items-center justify-center">
                            <Activity className="w-6 h-6 mb-2 text-muted-foreground/40" /> Sin ejecuciones registradas.
                        </div>
                    ) : (
                        <div className="divide-y divide-zinc-800/50">
                            {wfExecs.slice(0, 10).map(ex => {
                                const st = EXEC_STATUS[ex.status] ?? { label: ex.status, cls: "text-muted-foreground bg-muted border-border" };
                                return (
                                    <div key={ex.id} className="px-5 py-3 hover:bg-white/[0.01] transition-colors border-b border-border last:border-0">
                                        <div className="flex items-center justify-between mb-1">
                                            <div className="flex items-center gap-2">
                                                <span className={`text-[10px] px-1.5 py-0.5 rounded border font-semibold ${st.cls}`}>{st.label}</span>
                                                {ex.status === "paused" && (
                                                    <button onClick={() => onResume(wf.id, ex.id)}
                                                        className="text-[9px] text-orange-400 bg-orange-500/10 hover:bg-orange-500/20 px-1.5 py-0.5 rounded font-semibold transition-colors">
                                                        Reanudar
                                                    </button>
                                                )}
                                                {ex.status === "running" && (() => {
                                                    const runningMins = (Date.now() - new Date(ex.started_at).getTime()) / 60000;
                                                    if (runningMins < 2) return null;
                                                    return (
                                                        <button onClick={() => onCancel(wf.id, ex.id)}
                                                            className="text-[9px] text-red-400 bg-red-500/10 hover:bg-red-500/20 px-1.5 py-0.5 rounded font-semibold transition-colors flex items-center gap-0.5"
                                                            title="Cancelar ejecución atascada">
                                                            <StopCircle className="w-2.5 h-2.5" /> Cancelar
                                                        </button>
                                                    );
                                                })()}
                                            </div>
                                            <span className="text-[10px] text-muted-foreground font-mono">
                                                {new Date(ex.started_at).toLocaleString("es-ES", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })}
                                            </span>
                                        </div>
                                        {ex.status === "running" && liveLogs[ex.id] && liveLogs[ex.id].length > 0 ? (
                                            <div className="mt-2 bg-background border border-border rounded-lg p-2 space-y-0.5 max-h-32 overflow-y-auto">
                                                {liveLogs[ex.id].map((line, i) => (
                                                    <p key={i} className="text-[10px] font-mono text-foreground leading-relaxed">{line}</p>
                                                ))}
                                                <p className="text-[10px] font-mono text-blue-400 animate-pulse flex items-center gap-1">
                                                    <span className="w-1 h-1 rounded-full bg-blue-400 inline-block" /> procesando…
                                                </p>
                                            </div>
                                        ) : ex.status === "running" ? (
                                            <p className="text-[10px] text-blue-400 animate-pulse mt-1 font-mono flex items-center gap-1">
                                                <Loader2 className="w-2.5 h-2.5 animate-spin" /> Iniciando agente…
                                            </p>
                                        ) : ex.result_log ? (
                                            <p className="text-[11px] text-muted-foreground font-mono leading-relaxed mt-1 line-clamp-3">{ex.result_log}</p>
                                        ) : null}
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
