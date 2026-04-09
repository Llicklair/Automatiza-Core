"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useToastStore } from "@/stores/toast";
import {
    CalendarClock, AlertTriangle, CheckCircle2, FileText,
    Loader2, ChevronRight, Clock, ReceiptText, MessageSquare, Send, Download,
} from "lucide-react";
import { PageHeader } from "@/components/shared/PageHeader";
import { KpiCard } from "@/components/shared/KpiCard";
import { EmptyState } from "@/components/shared/EmptyState";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";

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
    "303": "bg-primary/20 text-primary border-primary/20",
    "130": "bg-emerald-600/30 text-emerald-300 border-emerald-500/30",
    "111": "bg-amber-600/30 text-amber-300 border-amber-500/30",
    "115": "bg-purple-600/30 text-purple-300 border-purple-500/30",
    "200": "bg-blue-600/30 text-blue-300 border-blue-500/30",
    "347": "bg-pink-600/30 text-pink-300 border-pink-500/30",
    "349": "bg-cyan-600/30 text-cyan-300 border-cyan-500/30",
};

function ModeloBadge({ modelo }: { modelo: string }) {
    const color = MODELO_COLORS[modelo] || "bg-accent text-muted-foreground border-border";
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
    const color = isUrgent ? "bg-red-500" : isClose ? "bg-amber-500" : "bg-primary";

    return (
        <div className="w-full h-1 bg-border rounded-full overflow-hidden mt-2">
            <div className={`h-full rounded-full transition-all duration-700 ${color}`} style={{ width: `${100 - pct}%` }} />
        </div>
    );
}

function EventCard({ ev }: { ev: FiscalEvent }) {
    const isUrgent = ev.dias_restantes <= ev.urgente_dias;
    const isClose = ev.dias_restantes <= 30 && !isUrgent;
    const dateStr = new Date(ev.fecha_limite).toLocaleDateString("es-ES", { day: "numeric", month: "long" });

    return (
        <Card className={
            isUrgent
                ? "border-red-500/30 bg-gradient-to-br from-red-950/20 to-card"
                : isClose
                    ? "border-amber-500/30 bg-gradient-to-br from-amber-950/20 to-card"
                    : ""
        }>
            <CardContent className="p-5">
                <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-2 flex-wrap">
                            <ModeloBadge modelo={ev.modelo} />
                            <span className="font-semibold text-foreground text-sm truncate">{ev.nombre}</span>
                        </div>
                        <p className="text-xs text-muted-foreground leading-relaxed">{ev.descripcion}</p>
                        <UrgencyBar dias={ev.dias_restantes} urgente={ev.urgente_dias} />
                    </div>
                    <div className="text-right flex-shrink-0 ml-4">
                        <p className="text-sm font-bold text-foreground">{dateStr}</p>
                        <p className={`text-xs font-medium mt-1 ${isUrgent ? "text-red-400" : isClose ? "text-amber-400" : "text-muted-foreground"}`}>
                            {isUrgent
                                ? `\u26A0 ${ev.dias_restantes}d`
                                : `${ev.dias_restantes} d\u00edas`
                            }
                        </p>
                        {isUrgent && (
                            <span className="inline-block text-[10px] uppercase font-bold text-red-400 bg-red-500/10 border border-red-500/20 px-2 py-0.5 rounded-full mt-1">
                                Urgente
                            </span>
                        )}
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}

// --- Consulta fiscal rapida ---

function ConsultaRapida() {
    const [question, setQuestion] = useState("");
    const [loading, setLoading] = useState(false);
    const [answer, setAnswer] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);

    const SUGGESTIONS = [
        "\u00bfCu\u00e1ndo debo presentar el modelo 303?",
        "\u00bfQu\u00e9 es el modelo 130 y para qu\u00e9 sirve?",
        "\u00bfTengo que presentar el modelo 347 si facturo m\u00e1s de 3.005\u20ac?",
        "\u00bfCu\u00e1l es el plazo para el IRPF como aut\u00f3nomo?",
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
                >
                    {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                </Button>
            </div>

            {loading && (
                <div className="flex items-center gap-3 text-xs text-muted-foreground py-4">
                    <Loader2 className="w-4 h-4 animate-spin text-primary shrink-0" />
                    El agente fiscal est\u00e1 analizando tu consulta...
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
                            Informaci\u00f3n orientativa generada por IA. Consulta siempre con tu asesor fiscal.
                        </p>
                    </CardContent>
                </Card>
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
        <Card>
            <CardContent className="p-5">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                    <div>
                        <h2 className="text-sm font-semibold text-foreground flex items-center gap-2">
                            <FileText className="w-4 h-4 text-emerald-400" />
                            Libro registro de facturas (AEAT)
                        </h2>
                        <p className="text-xs text-muted-foreground mt-1 max-w-xl">
                            Exporta CSV con facturas emitidas o recibidas del ejercicio para contabilidad o revisi\u00f3n.
                        </p>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                        <label className="text-xs text-muted-foreground flex items-center gap-2">
                            A\u00f1o
                            <Input
                                type="number"
                                min={2020}
                                max={yearNow + 1}
                                value={year}
                                onChange={(e) => setYear(Number(e.target.value) || yearNow)}
                                className="w-20 h-8"
                            />
                        </label>
                        <Button
                            variant="outline"
                            size="sm"
                            disabled={busy !== null}
                            onClick={() => void download("emitidas")}
                            className="text-emerald-400 border-emerald-500/30 hover:bg-emerald-600/20"
                        >
                            {busy === "emitidas" ? <Loader2 className="mr-1.5 w-3.5 h-3.5 animate-spin" /> : <Download className="mr-1.5 w-3.5 h-3.5" />}
                            Emitidas
                        </Button>
                        <Button
                            variant="outline"
                            size="sm"
                            disabled={busy !== null}
                            onClick={() => void download("recibidas")}
                            className="text-primary border-primary/20 hover:bg-primary/20"
                        >
                            {busy === "recibidas" ? <Loader2 className="mr-1.5 w-3.5 h-3.5 animate-spin" /> : <Download className="mr-1.5 w-3.5 h-3.5" />}
                            Recibidas
                        </Button>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}

export default function ImpuestosPage() {
    const [events, setEvents] = useState<FiscalEvent[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        api.advisory.calendar(90)
            .then((data: any[]) => {
                setEvents(data as FiscalEvent[]);
            })
            .catch(err => setError(err.message))
            .finally(() => setLoading(false));
    }, []);

    const urgentes = events.filter(ev => ev.dias_restantes <= (ev.urgente_dias ?? 15));
    const proximos = events.filter(ev => ev.dias_restantes > (ev.urgente_dias ?? 15));

    return (
        <div className="p-6 space-y-6">
            <PageHeader
                title="Impuestos & Fiscal"
                description="Calendario AEAT, vencimientos fiscales y consultas a tu asesor IA"
                icon={CalendarClock}
            />

            <Tabs defaultValue="calendario">
                <TabsList>
                    <TabsTrigger value="calendario" className="gap-2">
                        <CalendarClock className="w-4 h-4" />
                        Calendario AEAT
                    </TabsTrigger>
                    <TabsTrigger value="consulta" className="gap-2">
                        <MessageSquare className="w-4 h-4" />
                        Consultar Asesor IA
                    </TabsTrigger>
                </TabsList>

                <TabsContent value="consulta">
                    <Card>
                        <CardHeader>
                            <CardTitle className="text-sm">Consulta Fiscal</CardTitle>
                            <CardDescription>
                                El agente responde sobre normativa espa\u00f1ola vigente bas\u00e1ndose en el Modelo de IA configurado
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <ConsultaRapida />
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="calendario" className="space-y-6">
                    {/* KPIs */}
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                        <KpiCard
                            title="Vencimientos urgentes"
                            value={loading ? "\u2014" : urgentes.length}
                            icon={AlertTriangle}
                            className={urgentes.length > 0 ? "border-red-500/20" : ""}
                        />
                        <KpiCard
                            title="Pr\u00f3ximos 90 d\u00edas"
                            value={loading ? "\u2014" : proximos.length}
                            icon={Clock}
                        />
                        <KpiCard
                            title="Modelos en calendario"
                            value={loading ? "\u2014" : events.length}
                            icon={ReceiptText}
                        />
                    </div>

                    {loading ? (
                        <div className="flex items-center justify-center py-20 text-muted-foreground gap-3">
                            <Loader2 className="w-6 h-6 animate-spin text-primary" />
                            <span className="text-sm">Cargando calendario fiscal AEAT...</span>
                        </div>
                    ) : error ? (
                        <Card className="border-red-500/20 bg-red-500/5">
                            <CardContent className="p-6 text-red-400 text-sm flex gap-3">
                                <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
                                <div>
                                    <p className="font-medium">Error al cargar el calendario fiscal</p>
                                    <p className="text-red-400/70 text-xs mt-1">{error}</p>
                                </div>
                            </CardContent>
                        </Card>
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

                            {/* Proximos */}
                            {proximos.length > 0 && (
                                <div>
                                    <div className="flex items-center gap-2 mb-4">
                                        <CalendarClock className="w-4 h-4 text-muted-foreground" />
                                        <h2 className="text-sm font-semibold text-muted-foreground">Pr\u00f3ximos Vencimientos</h2>
                                        <ChevronRight className="w-4 h-4 text-muted-foreground ml-auto" />
                                    </div>
                                    <div className="space-y-3">
                                        {proximos.map((ev, i) => <EventCard key={i} ev={ev} />)}
                                    </div>
                                </div>
                            )}

                            {events.length === 0 && (
                                <EmptyState
                                    icon={CheckCircle2}
                                    title="Sin vencimientos pr\u00f3ximos"
                                    description="No hay obligaciones fiscales en los pr\u00f3ximos 90 d\u00edas."
                                />
                            )}

                            <p className="text-xs text-muted-foreground text-center pt-4 border-t border-border">
                                Calendario basado en normativa AEAT vigente &middot; Datos orientativos
                            </p>
                        </div>
                    )}
                </TabsContent>
            </Tabs>
        </div>
    );
}
