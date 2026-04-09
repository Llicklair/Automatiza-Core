"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { AlertTriangle, CalendarClock, Newspaper, MessageSquare, Loader2, Send } from "lucide-react";

type Tab = "calendario" | "boe" | "consulta";

interface Vencimiento {
    modelo: string;
    nombre: string;
    descripcion: string;
    fecha_limite: string;
    dias_restantes: number;
    tipo: string;
    urgente_dias: number;
}

export default function CompliancePage() {
    const [tab, setTab] = useState<Tab>("calendario");

    return (
        <div className="p-8 max-w-5xl mx-auto">
            <div className="mb-8">
                <h1 className="text-2xl font-bold text-foreground">Cumplimiento Legal y Fiscal</h1>
                <p className="text-sm text-muted-foreground mt-1">
                    Calendario fiscal AEAT, novedades del BOE y consultas sobre obligaciones
                </p>
            </div>

            {/* Tabs */}
            <div className="flex gap-1 mb-8 p-1 rounded-lg bg-card border border-border w-fit">
                {([
                    { id: "calendario", label: "Calendario fiscal", icon: CalendarClock },
                    { id: "boe", label: "Novedades BOE", icon: Newspaper },
                    { id: "consulta", label: "Consultar", icon: MessageSquare },
                ] as { id: Tab; label: string; icon: React.ElementType }[]).map(({ id, label, icon: Icon }) => (
                    <button
                        key={id}
                        onClick={() => setTab(id)}
                        className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition ${tab === id
                            ? "bg-primary text-foreground"
                            : "text-muted-foreground hover:text-foreground"
                            }`}
                    >
                        <Icon className="w-4 h-4" />
                        {label}
                    </button>
                ))}
            </div>

            {tab === "calendario" && <CalendarioTab />}
            {tab === "boe" && <BOETab />}
            {tab === "consulta" && <ConsultaTab />}
        </div>
    );
}


// ─── Utilidad para esperar tareas ─────────────────────────────────────────────

async function executeTaskAndWait(domain: string, intent: string, onProgress?: (msg: string) => void) {
    const task = await api.tasks.create(domain, intent);
    let currentTask = task;

    while (currentTask.status === "pending" || currentTask.status === "executing") {
        await new Promise(r => setTimeout(r, 2000));
        currentTask = await api.tasks.get(task.id);
        if (onProgress && currentTask.status === "executing") {
            onProgress("Procesando información...");
        }
    }

    if (currentTask.status === "failed") {
        throw new Error(currentTask.error_message || "Error al ejecutar la tarea");
    }

    // Extract the output from the last agent result
    const results: any[] = currentTask.agent_results || [];
    if (results.length > 0) {
        return results[results.length - 1].output || {};
    }

    return {};
}


// ─── Tab Calendario ───────────────────────────────────────────────────────────

function CalendarioTab() {
    const [vencimientos, setVencimientos] = useState<Vencimiento[]>([]);
    const [alertas, setAlertas] = useState<string[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        executeTaskAndWait("compliance", "vencimientos fiscales próximos 60 días")
            .then((results: any) => {
                setVencimientos(results?.vencimientos || []);
                setAlertas(results?.alertas || []);
                setLoading(false);
            })
            .catch((err) => {
                setError(err.message);
                setLoading(false);
            });
    }, []);

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center py-20 text-muted-foreground">
                <Loader2 className="w-8 h-8 animate-spin mb-4" />
                <p>Consultando calendario fiscal vigente...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
                Error al cargar el calendario: {error}
            </div>
        );
    }

    const urgentes = vencimientos.filter(v => v.dias_restantes <= v.urgente_dias);
    const proximos = vencimientos.filter(v => v.dias_restantes > v.urgente_dias);

    return (
        <div className="space-y-6">
            {/* Alertas redactadas por el Agente */}
            {alertas.length > 0 && (
                <div className="rounded-xl border border-primary/20 bg-primary/5 p-5 mb-6">
                    <h2 className="text-sm font-medium text-primary mb-3 flex items-center gap-2">
                        <MessageSquare className="w-4 h-4" />
                        Avisos del Asesor Fiscal
                    </h2>
                    <ul className="space-y-2 text-sm text-foreground list-disc pl-5">
                        {alertas.map((alerta, i) => (
                            <li key={i}>{alerta}</li>
                        ))}
                    </ul>
                </div>
            )}

            {/* Alertas urgentes */}
            {urgentes.length > 0 && (
                <div>
                    <h2 className="text-sm font-medium text-amber-400 mb-3 flex items-center gap-2">
                        <AlertTriangle className="w-4 h-4" />
                        Urgentes (menos de 15 días)
                    </h2>
                    <div className="space-y-3">
                        {urgentes.map((v, i) => (
                            <VencimientoCard key={i} v={v} urgent />
                        ))}
                    </div>
                </div>
            )}

            {/* Próximos vencimientos */}
            {proximos.length > 0 && (
                <div>
                    <h2 className="text-sm font-medium text-muted-foreground mb-3 flex items-center gap-2">
                        <CalendarClock className="w-4 h-4" />
                        Próximos vencimientos
                    </h2>
                    <div className="space-y-3">
                        {proximos.map((v, i) => (
                            <VencimientoCard key={i} v={v} />
                        ))}
                    </div>
                </div>
            )}

            {vencimientos.length === 0 && (
                <div className="text-center py-12 text-muted-foreground text-sm">
                    No hay vencimientos programados para los próximos días.
                </div>
            )}

            <p className="text-xs text-muted-foreground text-center pt-2">
                Fechas basadas en normativa vigente. Consulta siempre con tu asesor fiscal.
            </p>
        </div>
    );
}

function VencimientoCard({ v, urgent }: { v: Vencimiento; urgent?: boolean }) {
    return (
        <div className={`rounded-xl border p-5 ${urgent
            ? "border-amber-500/30 bg-amber-500/5"
            : "border-border bg-card"
            }`}>
            <div className="flex items-start justify-between gap-4">
                <div>
                    <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-bold text-foreground bg-primary/20 text-primary px-2 py-0.5 rounded">
                            Mod. {v.modelo}
                        </span>
                        <span className="font-medium text-foreground text-sm">{v.nombre}</span>
                    </div>
                    <p className="text-xs text-muted-foreground">{v.descripcion}</p>
                </div>
                <div className="text-right flex-shrink-0">
                    <p className="text-sm font-semibold text-foreground">{new Date(v.fecha_limite).toLocaleDateString('es-ES')}</p>
                    <p className={`text-xs ${urgent ? "text-amber-400" : "text-muted-foreground"}`}>
                        {v.dias_restantes} días
                    </p>
                </div>
            </div>
        </div>
    );
}


// ─── Tab BOE ──────────────────────────────────────────────────────────────────

function BOETab() {
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
                            {/* Resumen General */}
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

                            {/* Lista de Enlaces */}
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


// ─── Tab Consulta ─────────────────────────────────────────────────────────────

function ConsultaTab() {
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
