"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import {
    CalendarDays,
    Newspaper,
    AlertCircle,
    Briefcase,
    Scale,
    Loader2,
    ExternalLink,
    Search,
    Users,
    Building,
    Bot,
    Send,
    User,
    BookOpen,
    ChevronDown,
    ChevronUp,
    Lightbulb,
    Gavel,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { logError } from "@/lib/logger";

const CALENDAR_TYPES: Record<string, string[]> = {
    fiscal: ["iva", "irpf_fraccionado", "informativo_anual", "iva_anual"],
    laboral: ["retenciones", "retenciones_anual"],
    mercantil: [],
};

export default function AsesoriasPage() {
    const [news, setNews] = useState<any[]>([]);
    const [events, setEvents] = useState<any[]>([]);
    const [guides, setGuides] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState("fiscal");
    const [expandedGuide, setExpandedGuide] = useState<number | null>(null);
    const [newsSearch, setNewsSearch] = useState("");

    // Chat context
    const [chatMessages, setChatMessages] = useState<{ role: "user" | "ai", content: string }[]>([]);
    const [chatInput, setChatInput] = useState("");
    const [chatLoading, setChatLoading] = useState(false);

    useEffect(() => {
        async function fetchAdvisory() {
            setLoading(true);
            setExpandedGuide(null);
            try {
                const [n, e, g] = await Promise.all([
                    api.advisory.boe(filter, 8),
                    api.advisory.calendar(90),
                    api.advisory.guides(filter),
                ]);
                setNews(n || []);
                // Filtrar calendario por tipo según pestaña
                const tipos = CALENDAR_TYPES[filter] || [];
                setEvents(tipos.length > 0 ? (e || []).filter((ev: any) => tipos.includes(ev.tipo)) : []);
                setGuides(g || []);
            } catch (err) {
                logError("contabilidad/asesorias/page", err);
            } finally {
                setLoading(false);
            }
        }
        fetchAdvisory();
    }, [filter]);

    async function handleChat(e: React.FormEvent) {
        e.preventDefault();
        const prompt = chatInput.trim();
        if (!prompt) return;

        setChatInput("");
        setChatMessages(prev => [...prev, { role: "user", content: prompt }]);
        setChatLoading(true);

        try {
            const task = await api.tasks.create("compliance", prompt);
            let current = task;

            while (current.status !== "done" && current.status !== "failed" && current.status !== "cancelled") {
                await new Promise(r => setTimeout(r, 2000));
                current = await api.tasks.get(task.id);
            }

            if (current.status === "done" && current.agent_results?.length) {
                const results: any[] = current.agent_results;
                // El compliance agent guarda la respuesta en action_taken del último paso
                const answer = results.slice().reverse().find(
                    (r: any) => r.action_taken && r.action_taken !== "Invocando herramientas de compliance" && r.action_taken !== "Operación compliance completada."
                )?.action_taken;
                setChatMessages(prev => [...prev, { role: "ai", content: answer || "No pude obtener una respuesta. Inténtalo de nuevo." }]);
            } else {
                setChatMessages(prev => [...prev, { role: "ai", content: current.error_message || "La tarea falló." }]);
            }
        } catch (err: any) {
            setChatMessages(prev => [...prev, { role: "ai", content: `Error de conexión: ${err.message}` }]);
        } finally {
            setChatLoading(false);
        }
    }

    return (
        <div className="p-8 max-w-7xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight text-foreground flex items-center gap-3">
                        <Scale className="w-8 h-8 text-primary" />
                        Asesoría Jurídica y Fiscal
                    </h1>
                    <p className="text-muted-foreground mt-2">
                        Mantente al día de tus obligaciones con la AEAT y las últimas normativas del BOE para tu negocio.
                    </p>
                </div>

                <div className="flex bg-card p-1 rounded-xl border border-border">
                    {[
                        { id: "fiscal", label: "Fiscal / AEAT", icon: Briefcase },
                        { id: "laboral", label: "Laboral", icon: Users },
                        { id: "mercantil", label: "Mercantil", icon: Building },
                    ].map((tab) => {
                        const Icon = tab.icon;
                        const isActive = filter === tab.id;
                        return (
                            <button
                                key={tab.id}
                                onClick={() => setFilter(tab.id)}
                                className={cn(
                                    "flex items-center gap-2 px-4 py-2 text-sm font-medium transition-all rounded-lg",
                                    isActive
                                        ? "bg-primary/20 text-primary shadow-sm"
                                        : "text-muted-foreground hover:text-foreground hover:bg-accent/50"
                                )}
                            >
                                <Icon className="w-4 h-4" />
                                {tab.label}
                            </button>
                        );
                    })}
                </div>
            </div>

            {loading ? (
                <div className="flex items-center justify-center py-20">
                    <Loader2 className="w-8 h-8 text-primary animate-spin" />
                </div>
            ) : (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">

                    {/* Left Column: Chat IA + Calendario Fiscal */}
                    <div className="col-span-1 space-y-4">
                        {/* AI Advisory Chat */}
                        <div className="bg-card border border-border rounded-2xl overflow-hidden shadow-lg shadow-black/20 flex flex-col h-[400px]">
                            <div className="px-5 py-4 border-b border-border flex items-center justify-between bg-card">
                                <div className="flex items-center gap-2">
                                    <Bot className="w-5 h-5 text-primary" />
                                    <h2 className="text-sm font-semibold text-foreground">Consulta al Asesor IA</h2>
                                </div>
                            </div>

                            <div className="flex-1 overflow-y-auto p-5 space-y-4 custom-scrollbar">
                                {chatMessages.length === 0 ? (
                                    <div className="text-center py-10 flex flex-col items-center justify-center h-full">
                                        <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center mb-3">
                                            <Scale className="w-6 h-6 text-primary" />
                                        </div>
                                        <p className="text-sm text-muted-foreground">¿Tienes dudas fiscales?</p>
                                        <p className="text-xs text-muted-foreground mt-1 max-w-[200px] leading-relaxed">Pregunta sobre impuestos, deducciones o vencimientos de tu cuenta.</p>
                                    </div>
                                ) : (
                                    chatMessages.map((msg, idx) => (
                                        <div key={idx} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                            {msg.role === 'ai' && <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center flex-shrink-0"><Bot className="w-4 h-4 text-primary" /></div>}
                                            <div className={`px-4 py-3 rounded-2xl max-w-[85%] text-sm ${msg.role === 'user' ? 'bg-primary text-foreground rounded-br-none' : 'bg-muted text-foreground rounded-bl-none border border-border'}`}>
                                                <div className="whitespace-pre-wrap">{msg.content}</div>
                                            </div>
                                            {msg.role === 'user' && <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center flex-shrink-0"><User className="w-4 h-4 text-muted-foreground" /></div>}
                                        </div>
                                    ))
                                )}
                                {chatLoading && (
                                    <div className="flex gap-3 justify-start">
                                        <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center flex-shrink-0"><Bot className="w-4 h-4 text-primary" /></div>
                                        <div className="px-4 py-3 rounded-2xl bg-muted text-muted-foreground rounded-bl-none text-sm flex items-center gap-2 border border-border">
                                            <Loader2 className="w-4 h-4 animate-spin flex-shrink-0" /> Analizando contexto legal...
                                        </div>
                                    </div>
                                )}
                            </div>

                            <div className="p-3 border-t border-border bg-card">
                                <form onSubmit={handleChat} className="flex gap-2">
                                    <input
                                        type="text"
                                        value={chatInput}
                                        onChange={(e) => setChatInput(e.target.value)}
                                        disabled={chatLoading}
                                        placeholder="Ej. ¿Cuándo presento el IVA?"
                                        className="flex-1 bg-background border border-border text-sm text-foreground rounded-xl px-4 py-3 focus:outline-none focus:border-primary transition disabled:opacity-50"
                                    />
                                    <button
                                        type="submit"
                                        disabled={chatLoading || !chatInput.trim()}
                                        className="bg-primary hover:bg-primary text-foreground px-4 py-3 rounded-xl transition flex items-center justify-center disabled:opacity-50"
                                    >
                                        <Send className="w-4 h-4" />
                                    </button>
                                </form>
                            </div>
                        </div>

                        <div className="flex items-center gap-2">
                            <CalendarDays className="w-5 h-5 text-muted-foreground" />
                            <h2 className="text-xl font-semibold text-foreground">Próximos Vencimientos</h2>
                        </div>

                        <div className="bg-card border border-border rounded-2xl overflow-hidden shadow-lg shadow-black/20">
                            {events.length === 0 ? (
                                <div className="p-8 text-center text-muted-foreground text-sm">
                                    {filter === "mercantil"
                                        ? "Las obligaciones mercantiles tienen plazos anuales. Consulta la guía normativa."
                                        : "No hay vencimientos próximos en los próximos meses."}
                                </div>
                            ) : (
                                <div className="divide-y divide-border">
                                    {events.map((evt, i) => {
                                        const isUrgent = evt.dias_restantes <= evt.urgente_dias;
                                        return (
                                            <div key={i} className="p-5 hover:bg-accent/50 transition-colors">
                                                <div className="flex justify-between items-start mb-2">
                                                    <div className="flex items-center gap-2">
                                                        <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-border text-foreground">
                                                            Mod. {evt.modelo}
                                                        </span>
                                                        {isUrgent && (
                                                            <span className="flex items-center gap-1 text-xs text-red-400 bg-red-500/10 px-2 py-0.5 rounded-full ring-1 ring-red-500/20">
                                                                <AlertCircle className="w-3 h-3" />
                                                                Urgente
                                                            </span>
                                                        )}
                                                    </div>
                                                    <span className={cn(
                                                        "text-xs font-medium px-2 py-0.5 rounded-full bg-accent/50",
                                                        isUrgent ? "text-red-400 border border-red-500/20" : "text-emerald-400 border border-emerald-500/20"
                                                    )}>
                                                        Faltan {evt.dias_restantes} días
                                                    </span>
                                                </div>
                                                <h3 className="text-foreground font-medium">{evt.nombre}</h3>
                                                <p className="text-muted-foreground text-sm mt-1">{evt.descripcion}</p>
                                                <div className="mt-3 text-xs text-muted-foreground flex items-center gap-2">
                                                    <CalendarDays className="w-3.5 h-3.5 opacity-70" />
                                                    Fecha límite: <span className="text-foreground font-medium">{new Date(evt.fecha_limite).toLocaleDateString()}</span>
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            )}
                        </div>

                    </div>

                    {/* Right Column: Guías + BOE Feed */}
                    <div className="col-span-1 lg:col-span-2 space-y-8">

                        {/* Guías Normativas */}
                        <div className="space-y-4">
                            <div className="flex items-center gap-2">
                                <BookOpen className="w-5 h-5 text-muted-foreground" />
                                <h2 className="text-xl font-semibold text-foreground">
                                    Guía Normativa — {filter === "fiscal" ? "Fiscal / AEAT" : filter === "laboral" ? "Laboral" : "Mercantil"}
                                </h2>
                            </div>

                            <div className="grid gap-3">
                                {guides.map((guide: any, i: number) => {
                                    const isExpanded = expandedGuide === i;
                                    return (
                                        <div
                                            key={i}
                                            className="bg-card border border-border rounded-2xl overflow-hidden shadow-lg shadow-black/10 transition-all"
                                        >
                                            <button
                                                onClick={() => setExpandedGuide(isExpanded ? null : i)}
                                                className="w-full p-5 flex items-start gap-4 text-left hover:bg-accent/50 transition-colors"
                                            >
                                                <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                                                    <Gavel className="w-5 h-5 text-primary" />
                                                </div>
                                                <div className="flex-1 min-w-0">
                                                    <h3 className="text-foreground font-medium leading-snug">{guide.titulo}</h3>
                                                    <p className="text-muted-foreground text-sm mt-1 line-clamp-2">{guide.resumen}</p>
                                                </div>
                                                <div className="flex-shrink-0 mt-1">
                                                    {isExpanded
                                                        ? <ChevronUp className="w-5 h-5 text-muted-foreground" />
                                                        : <ChevronDown className="w-5 h-5 text-muted-foreground" />
                                                    }
                                                </div>
                                            </button>

                                            {isExpanded && (
                                                <div className="px-5 pb-5 pt-0 space-y-4 border-t border-border animate-in fade-in slide-in-from-top-2 duration-200">
                                                    <div className="pt-4">
                                                        <p className="text-foreground text-sm leading-relaxed">{guide.resumen}</p>
                                                    </div>

                                                    <div className="flex items-start gap-3 bg-card rounded-xl p-4 border border-border">
                                                        <Lightbulb className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
                                                        <div>
                                                            <p className="text-xs font-semibold text-amber-400 uppercase tracking-wider mb-1">Consejo para tu PYME</p>
                                                            <p className="text-foreground text-sm leading-relaxed">{guide.consejo_pyme}</p>
                                                        </div>
                                                    </div>

                                                    <div className="flex flex-col sm:flex-row sm:items-center gap-3 text-xs">
                                                        <span className="text-muted-foreground bg-card px-3 py-1.5 rounded-lg border border-border font-mono">
                                                            {guide.referencia_legal}
                                                        </span>
                                                        {guide.url_boe && (
                                                            <a
                                                                href={guide.url_boe}
                                                                target="_blank"
                                                                rel="noreferrer"
                                                                className="flex items-center gap-1.5 text-primary hover:text-primary transition-colors"
                                                            >
                                                                <ExternalLink className="w-3.5 h-3.5" />
                                                                Ver en el BOE
                                                            </a>
                                                        )}
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    );
                                })}
                            </div>
                        </div>

                        {/* BOE Feed */}
                        <div className="space-y-4">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <Newspaper className="w-5 h-5 text-muted-foreground" />
                                    <h2 className="text-xl font-semibold text-foreground">Novedades Normativas (BOE)</h2>
                                </div>
                                <div className="relative hidden sm:block">
                                    <Search className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
                                    <input
                                        type="text"
                                        placeholder="Buscar decretos..."
                                        value={newsSearch}
                                        onChange={e => setNewsSearch(e.target.value)}
                                        className="bg-card border border-border rounded-lg py-1.5 pl-9 pr-3 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary w-64 transition-all"
                                    />
                                </div>
                            </div>

                            <div className="grid gap-4">
                                {(() => {
                                    const q = newsSearch.toLowerCase();
                                    const filtered = q ? news.filter(item =>
                                        (item.titulo || "").toLowerCase().includes(q) ||
                                        (item.descripcion || "").toLowerCase().includes(q) ||
                                        (item.identificador || "").toLowerCase().includes(q)
                                    ) : news;
                                    if (filtered.length === 0) return (
                                        <div className="bg-card border border-border rounded-2xl p-8 text-center text-muted-foreground">
                                            {news.length === 0
                                                ? "No se encontraron novedades recientes del BOE para esta categoría. Consulta la guía normativa de arriba para conocer tus obligaciones vigentes."
                                                : `Sin resultados para "${newsSearch}"`}
                                        </div>
                                    );
                                    return filtered.map((item: any, i) => (
                                        <a
                                            key={i}
                                            href={item.url}
                                            target="_blank"
                                            rel="noreferrer"
                                            className="group bg-card border border-border hover:border-primary/20 rounded-2xl p-5 hover:bg-muted transition-all flex flex-col sm:flex-row gap-5 shadow-lg shadow-black/10"
                                        >
                                            <div className="flex-1">
                                                <div className="flex items-center gap-3 mb-2">
                                                    <span className="text-xs text-muted-foreground font-medium bg-card px-2 py-1 rounded-md border border-border">
                                                        {new Date(item.fecha).toLocaleDateString()}
                                                    </span>
                                                    {item.relevante_pyme && (
                                                        <span className="text-[10px] uppercase font-bold tracking-wider text-amber-400 bg-amber-400/10 px-2 py-1 rounded-md ring-1 ring-amber-400/20">
                                                            Relevante para tu negocio
                                                        </span>
                                                    )}
                                                    {item.identificador && (
                                                        <span className="text-[10px] font-mono text-muted-foreground">
                                                            {item.identificador}
                                                        </span>
                                                    )}
                                                </div>
                                                <h3 className="text-foreground font-medium leading-snug group-hover:text-primary transition-colors">
                                                    {item.titulo}
                                                </h3>
                                                <p className="text-muted-foreground text-sm mt-2 line-clamp-2 md:line-clamp-3 leading-relaxed">
                                                    {item.descripcion}
                                                </p>
                                            </div>
                                            <div className="flex sm:flex-col justify-end items-center sm:items-center gap-2 shrink-0">
                                                <div className="w-10 h-10 rounded-full bg-accent/50 flex items-center justify-center group-hover:bg-primary transition-colors group-hover:shadow-lg group-hover:shadow-primary/20">
                                                    <ExternalLink className="w-4 h-4 text-muted-foreground group-hover:text-foreground" />
                                                </div>
                                            </div>
                                        </a>
                                    ));
                                })()}
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
