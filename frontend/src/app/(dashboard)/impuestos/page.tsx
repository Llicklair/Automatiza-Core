"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useToastStore } from "@/stores/toast";
import {
    CalendarClock, AlertTriangle, CheckCircle2, FileText,
    Loader2, ChevronRight, Clock, ReceiptText, MessageSquare, Send, Download,
} from "lucide-react";

interface FiscalEvent {
    modelo: string;
    nombre: string;
    descripcion: string;
    fecha_limite: string;
    dias_restantes: number;
    tipo: string;
    urgente_dias: number;
}

// Colores por modelo fiscal
const MODELO_COLORS: Record<string, string> = {
    "303": "bg-indigo-600/30 text-indigo-300 border-indigo-500/30",
    "130": "bg-emerald-600/30 text-emerald-300 border-emerald-500/30",
    "111": "bg-amber-600/30 text-amber-300 border-amber-500/30",
    "115": "bg-purple-600/30 text-purple-300 border-purple-500/30",
    "200": "bg-blue-600/30 text-blue-300 border-blue-500/30",
    "347": "bg-pink-600/30 text-pink-300 border-pink-500/30",
    "349": "bg-cyan-600/30 text-cyan-300 border-cyan-500/30",
};

function ModeloBadge({ modelo }: { modelo: string }) {
    const color = MODELO_COLORS[modelo] || "bg-zinc-700/30 text-zinc-400 border-zinc-500/30";
    return (
        <span className={`inline-flex items-center text-xs font-bold px-2.5 py-1 rounded-lg border ${color}`}>
            Mod. {modelo}
        </span>
    );
}

function UrgencyBar({ dias, urgente }: { dias: number; urgente: number }) {
    const pct = Math.max(0, Math.min(100, Math.round((dias / 90) * 100)));
    const isUrgent = dias <= urgente;
    const isClose = dias <= 30;
    const color = isUrgent ? "bg-red-500" : isClose ? "bg-amber-500" : "bg-indigo-500";

    return (
        <div className="w-full h-1 bg-[#27272a] rounded-full overflow-hidden mt-2">
            <div className={`h-full rounded-full transition-all duration-700 ${color}`} style={{ width: `${100 - pct}%` }} />
        </div>
    );
}

function EventCard({ ev }: { ev: FiscalEvent }) {
    const isUrgent = ev.dias_restantes <= ev.urgente_dias;
    const isClose = ev.dias_restantes <= 30 && !isUrgent;
    const dateStr = new Date(ev.fecha_limite).toLocaleDateString("es-ES", { day: "numeric", month: "long" });

    return (
        <div className={`rounded-xl border p-5 transition-all hover:scale-[1.01] cursor-default ${isUrgent
            ? "border-red-500/30 bg-gradient-to-br from-red-950/20 to-[#111113]"
            : isClose
                ? "border-amber-500/30 bg-gradient-to-br from-amber-950/20 to-[#111113]"
                : "border-[#27272a] bg-[#111113]"
            }`}>
            <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2 flex-wrap">
                        <ModeloBadge modelo={ev.modelo} />
                        <span className="font-semibold text-white text-sm truncate">{ev.nombre}</span>
                    </div>
                    <p className="text-xs text-zinc-400 leading-relaxed">{ev.descripcion}</p>
                    <UrgencyBar dias={ev.dias_restantes} urgente={ev.urgente_dias} />
                </div>
                <div className="text-right flex-shrink-0 ml-4">
                    <p className="text-sm font-bold text-white">{dateStr}</p>
                    <p className={`text-xs font-medium mt-1 ${isUrgent ? "text-red-400" : isClose ? "text-amber-400" : "text-zinc-500"}`}>
                        {isUrgent
                            ? `⚠ ${ev.dias_restantes}d`
                            : `${ev.dias_restantes} días`
                        }
                    </p>
                    {isUrgent && (
                        <span className="inline-block text-[10px] uppercase font-bold text-red-400 bg-red-500/10 border border-red-500/20 px-2 py-0.5 rounded-full mt-1">
                            Urgente
                        </span>
                    )}
                </div>
            </div>
        </div>
    );
}

// ─── Consulta fiscal rápida ────────────────────────────────────────────────────

function ConsultaRapida() {
    const [question, setQuestion] = useState("");
    const [loading, setLoading] = useState(false);
    const [answer, setAnswer] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);

    const SUGGESTIONS = [
        "¿Cuándo debo presentar el modelo 303?",
        "¿Qué es el modelo 130 y para qué sirve?",
        "¿Tengo que presentar el modelo 347 si facturo más de 3.005€?",
        "¿Cuál es el plazo para el IRPF como autónomo?",
    ];

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
                    <button
                        key={s}
                        onClick={() => submit(s)}
                        className="text-xs px-3 py-1.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 hover:bg-indigo-500/20 transition-colors"
                    >
                        {s}
                    </button>
                ))}
            </div>

            <div className="flex gap-3">
                <input
                    type="text"
                    value={question}
                    onChange={e => setQuestion(e.target.value)}
                    onKeyDown={e => e.key === "Enter" && submit(question)}
                    placeholder="Escribe tu consulta fiscal..."
                    className="flex-1 bg-[#18181b] border border-[#3f3f46] rounded-xl px-4 py-2.5 text-white text-sm placeholder-zinc-500 focus:outline-none focus:border-indigo-500 transition"
                />
                <button
                    onClick={() => submit(question)}
                    disabled={loading || !question.trim()}
                    className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-medium transition"
                >
                    {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                </button>
            </div>

            {loading && (
                <div className="flex items-center gap-3 text-xs text-zinc-400 py-4">
                    <Loader2 className="w-4 h-4 animate-spin text-indigo-500 shrink-0" />
                    El agente fiscal está analizando tu consulta...
                </div>
            )}

            {error && (
                <div className="p-4 rounded-xl bg-red-500/5 border border-red-500/20 text-red-400 text-sm flex gap-2">
                    <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                    <span>{error}</span>
                </div>
            )}

            {answer && (
                <div className="p-5 rounded-xl bg-indigo-500/5 border border-indigo-500/20 relative overflow-hidden">
                    <div className="absolute top-0 right-0 p-3 opacity-5 pointer-events-none">
                        <MessageSquare className="w-24 h-24 text-indigo-400" />
                    </div>
                    <div className="flex items-center gap-2 mb-3 text-xs font-semibold text-indigo-400">
                        <div className="w-6 h-6 rounded-full bg-indigo-500/20 flex items-center justify-center">
                            <MessageSquare className="w-3 h-3" />
                        </div>
                        Asesor Fiscal IA
                    </div>
                    <p className="text-sm text-zinc-300 whitespace-pre-wrap leading-relaxed">{answer}</p>
                    <p className="text-xs text-zinc-600 mt-4 pt-3 border-t border-indigo-500/10">
                        ⚠ Información orientativa generada por IA. Consulta siempre con tu asesor fiscal.
                    </p>
                </div>
            )}
        </div>
    );
}


function LibroRegistroExport() {
    const show = useToastStore((s) => s.show);
    const yearNow = new Date().getFullYear();
    const [year, setYear] = useState(yearNow);
    const [busy, setBusy] = useState<"emitidas" | "recibidas" | null>(null);

    const download = async (type: "emitidas" | "recibidas") => {
        setBusy(type);
        try {
            await api.reports.libroRegistro(year, type);
            show(`Libro ${type} ${year} descargado`, "success");
        } catch (e: unknown) {
            const msg = e instanceof Error ? e.message : "No se pudo descargar el CSV";
            show(msg, "error");
        } finally {
            setBusy(null);
        }
    };

    return (
        <div className="rounded-2xl border border-[#27272a] bg-[#111113] p-5 mb-8">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
                    <h2 className="text-sm font-semibold text-white flex items-center gap-2">
                        <FileText className="w-4 h-4 text-emerald-400" />
                        Libro registro de facturas (AEAT)
                    </h2>
                    <p className="text-xs text-zinc-500 mt-1 max-w-xl">
                        Exporta CSV con facturas emitidas o recibidas del ejercicio para contabilidad o revisión.
                    </p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                    <label className="text-xs text-zinc-500 flex items-center gap-2">
                        Año
                        <input
                            type="number"
                            min={2020}
                            max={yearNow + 1}
                            value={year}
                            onChange={(e) => setYear(Number(e.target.value) || yearNow)}
                            className="w-20 bg-[#18181b] border border-zinc-700 rounded-lg px-2 py-1.5 text-sm text-white"
                        />
                    </label>
                    <button
                        type="button"
                        disabled={busy !== null}
                        onClick={() => void download("emitidas")}
                        className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium bg-emerald-600/20 text-emerald-300 border border-emerald-500/30 hover:bg-emerald-600/30 disabled:opacity-50"
                    >
                        {busy === "emitidas" ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
                        Emitidas
                    </button>
                    <button
                        type="button"
                        disabled={busy !== null}
                        onClick={() => void download("recibidas")}
                        className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium bg-indigo-600/20 text-indigo-300 border border-indigo-500/30 hover:bg-indigo-600/30 disabled:opacity-50"
                    >
                        {busy === "recibidas" ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
                        Recibidas
                    </button>
                </div>
            </div>
        </div>
    );
}

export default function ImpuestosPage() {
    const [events, setEvents] = useState<FiscalEvent[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [tab, setTab] = useState<"calendario" | "consulta">("calendario");

    useEffect(() => {
        api.advisory.calendar(90)
            .then((data: any[]) => {
                // El endpoint devuelve objetos con estructura del calendario
                setEvents(data as FiscalEvent[]);
            })
            .catch(err => setError(err.message))
            .finally(() => setLoading(false));
    }, []);

    const urgentes = events.filter(ev => ev.dias_restantes <= (ev.urgente_dias ?? 15));
    const proximos = events.filter(ev => ev.dias_restantes > (ev.urgente_dias ?? 15));

    return (
        <div className="p-8 max-w-4xl mx-auto">
            {/* Header */}
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-white tracking-tight">Impuestos & Fiscal</h1>
                <p className="text-sm text-zinc-400 mt-1">
                    Calendario AEAT, vencimientos fiscales y consultas a tu asesor IA
                </p>
            </div>

            {/* Tabs */}
            <div className="flex gap-1 mb-8 p-1 rounded-xl bg-[#18181b] border border-[#27272a] w-fit">
                {([
                    { id: "calendario", label: "Calendario AEAT", icon: CalendarClock },
                    { id: "consulta", label: "Consultar Asesor IA", icon: MessageSquare },
                ] as { id: typeof tab, label: string; icon: React.ElementType }[]).map(({ id, label, icon: Icon }) => (
                    <button
                        key={id}
                        onClick={() => setTab(id)}
                        className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition ${tab === id
                            ? "bg-indigo-600 text-white shadow-lg shadow-indigo-500/20"
                            : "text-zinc-400 hover:text-white"
                            }`}
                    >
                        <Icon className="w-4 h-4" />
                        {label}
                    </button>
                ))}
            </div>

            {tab === "consulta" ? (
                <div className="bg-[#111113] border border-[#27272a] rounded-2xl p-6 shadow-lg shadow-black/20">
                    <h2 className="text-sm font-semibold text-white mb-1">Consulta Fiscal</h2>
                    <p className="text-xs text-zinc-500 mb-5">
                        El agente responde sobre normativa española vigente basándose en el Modelo de IA configurado
                    </p>
                    <ConsultaRapida />
                </div>
            ) : (
                <>
                    {/* KPIs rápidos */}
                    <div className="grid grid-cols-3 gap-4 mb-8">
                        <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-4 flex items-center gap-3">
                            <AlertTriangle className="w-8 h-8 text-red-400 shrink-0" />
                            <div>
                                <p className="text-2xl font-bold text-red-400">{loading ? "—" : urgentes.length}</p>
                                <p className="text-xs text-zinc-500">Vencimientos urgentes</p>
                            </div>
                        </div>
                        <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4 flex items-center gap-3">
                            <Clock className="w-8 h-8 text-amber-400 shrink-0" />
                            <div>
                                <p className="text-2xl font-bold text-amber-400">{loading ? "—" : proximos.length}</p>
                                <p className="text-xs text-zinc-500">Próximos 90 días</p>
                            </div>
                        </div>
                        <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4 flex items-center gap-3">
                            <ReceiptText className="w-8 h-8 text-emerald-400 shrink-0" />
                            <div>
                                <p className="text-2xl font-bold text-emerald-400">{loading ? "—" : events.length}</p>
                                <p className="text-xs text-zinc-500">Modelos en calendario</p>
                            </div>
                        </div>
                    </div>

                    {loading ? (
                        <div className="flex items-center justify-center py-20 text-zinc-400 gap-3">
                            <Loader2 className="w-6 h-6 animate-spin text-indigo-500" />
                            <span className="text-sm">Cargando calendario fiscal AEAT...</span>
                        </div>
                    ) : error ? (
                        <div className="p-6 rounded-2xl bg-red-500/5 border border-red-500/20 text-red-400 text-sm flex gap-3">
                            <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
                            <div>
                                <p className="font-medium">Error al cargar el calendario fiscal</p>
                                <p className="text-red-400/70 text-xs mt-1">{error}</p>
                            </div>
                        </div>
                    ) : (
                        <div className="space-y-8">
                            <LibroRegistroExport />
                            {/* Urgentes */}
                            {urgentes.length > 0 && (
                                <div>
                                    <div className="flex items-center gap-2 mb-4">
                                        <AlertTriangle className="w-4 h-4 text-red-400" />
                                        <h2 className="text-sm font-semibold text-red-400">Vencimientos Urgentes</h2>
                                        <span className="ml-auto text-xs text-red-400 bg-red-500/10 border border-red-500/20 px-2 py-0.5 rounded-full font-bold">
                                            {urgentes.length} pendiente{urgentes.length !== 1 ? "s" : ""}
                                        </span>
                                    </div>
                                    <div className="space-y-3">
                                        {urgentes.map((ev, i) => <EventCard key={i} ev={ev} />)}
                                    </div>
                                </div>
                            )}

                            {/* Próximos */}
                            {proximos.length > 0 && (
                                <div>
                                    <div className="flex items-center gap-2 mb-4">
                                        <CalendarClock className="w-4 h-4 text-zinc-400" />
                                        <h2 className="text-sm font-semibold text-zinc-400">Próximos Vencimientos</h2>
                                        <ChevronRight className="w-4 h-4 text-zinc-600 ml-auto" />
                                    </div>
                                    <div className="space-y-3">
                                        {proximos.map((ev, i) => <EventCard key={i} ev={ev} />)}
                                    </div>
                                </div>
                            )}

                            {events.length === 0 && (
                                <div className="flex flex-col items-center justify-center py-20 text-center">
                                    <CheckCircle2 className="w-12 h-12 text-zinc-700 mb-4" />
                                    <p className="text-white font-medium">Sin vencimientos próximos</p>
                                    <p className="text-sm text-zinc-500 mt-1">No hay obligaciones fiscales en los próximos 90 días.</p>
                                </div>
                            )}

                            <p className="text-xs text-zinc-700 text-center pt-4 border-t border-[#27272a]">
                                Calendario basado en normativa AEAT vigente · Datos orientativos
                            </p>
                        </div>
                    )}
                </>
            )}
        </div>
    );
}
