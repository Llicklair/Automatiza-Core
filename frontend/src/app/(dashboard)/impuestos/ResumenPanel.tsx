"use client";

import { useState } from "react";
import {
    CalendarClock, AlertTriangle, CheckCircle2,
    Loader2, ChevronRight, Clock, ReceiptText, MessageSquare, Sparkles,
} from "lucide-react";
import { PageHeader } from "@/components/shared/PageHeader";
import { KpiCard } from "@/components/shared/KpiCard";
import { EmptyState } from "@/components/shared/EmptyState";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { useImpuestos } from "./_hooks/useImpuestos";
import { EventCard } from "./_components/EventCard";
import { ConsultaRapida } from "./_components/ConsultaRapida";
import { LibroRegistroExport } from "./_components/LibroRegistroExport";
import { Expediente303Drawer } from "./_components/Expediente303Drawer";
import { PresentacionesPanel } from "./_components/PresentacionesPanel";
import { PreventiveCheckCard } from "./_components/PreventiveCheckCard";

function currentQuarterYear(): { quarter: number; year: number } {
    const d = new Date();
    return { quarter: Math.floor(d.getMonth() / 3) + 1, year: d.getFullYear() };
}

export function ResumenPanel() {
    const { events, loading, error, urgentes, proximos } = useImpuestos();
    const [exp303Open, setExp303Open] = useState(false);
    const [exp303Q, setExp303Q] = useState(currentQuarterYear());

    return (
        <div className="space-y-6">
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
                                El agente responde sobre normativa española vigente basándose en el Modelo de IA configurado
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <ConsultaRapida />
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="calendario" className="space-y-6">
                    {/* Panel general de presentación electrónica (todos los modelos) */}
                    <PresentacionesPanel />

                    {/* Expediente Modelo 303 — atajo prominente */}
                    <Card className="border-primary/20 bg-gradient-to-br from-primary/5 via-card to-card">
                        <CardContent className="p-5 flex items-start justify-between gap-4 flex-wrap">
                            <div className="flex items-start gap-3 flex-1 min-w-[280px]">
                                <div className="flex-shrink-0 w-11 h-11 rounded-xl bg-primary/15 text-primary flex items-center justify-center">
                                    <Sparkles className="w-5 h-5" />
                                </div>
                                <div>
                                    <p className="text-sm font-semibold text-foreground">
                                        Expediente Modelo 303 — listo para presentar
                                    </p>
                                    <p className="text-xs text-muted-foreground mt-0.5 max-w-prose">
                                        Casillas oficiales rellenadas desde tus facturas, XML auxiliar, PDF y checklist paso a paso para presentar tú mismo en la SEDE AEAT.
                                    </p>
                                </div>
                            </div>
                            <div className="flex items-center gap-2">
                                <select
                                    value={`${exp303Q.quarter}-${exp303Q.year}`}
                                    onChange={(e) => {
                                        const [q, y] = e.target.value.split("-").map(Number);
                                        setExp303Q({ quarter: q, year: y });
                                    }}
                                    className="h-9 px-2 rounded-md border border-border bg-card text-sm"
                                >
                                    {[1, 2, 3, 4].map((q) => (
                                        <option key={`${q}-${exp303Q.year}`} value={`${q}-${exp303Q.year}`}>
                                            {q}T {exp303Q.year}
                                        </option>
                                    ))}
                                </select>
                                <Button onClick={() => setExp303Open(true)} className="h-9">
                                    Generar expediente
                                </Button>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Asistente fiscal preventivo del trimestre seleccionado */}
                    <PreventiveCheckCard quarter={exp303Q.quarter} year={exp303Q.year} />

                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                        <KpiCard
                            title="Vencimientos urgentes"
                            value={loading ? "—" : urgentes.length}
                            icon={AlertTriangle}
                            className={urgentes.length > 0 ? "border-red-500/20" : ""}
                        />
                        <KpiCard
                            title="Próximos 90 días"
                            value={loading ? "—" : proximos.length}
                            icon={Clock}
                        />
                        <KpiCard
                            title="Modelos en calendario"
                            value={loading ? "—" : events.length}
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

                            {proximos.length > 0 && (
                                <div>
                                    <div className="flex items-center gap-2 mb-4">
                                        <CalendarClock className="w-4 h-4 text-muted-foreground" />
                                        <h2 className="text-sm font-semibold text-muted-foreground">Próximos Vencimientos</h2>
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
                                    title="Sin vencimientos próximos"
                                    description="No hay obligaciones fiscales en los próximos 90 días."
                                />
                            )}

                            <p className="text-xs text-muted-foreground text-center pt-4 border-t border-border">
                                Calendario basado en normativa AEAT vigente · Datos orientativos
                            </p>
                        </div>
                    )}
                </TabsContent>
            </Tabs>

            <Expediente303Drawer
                quarter={exp303Q.quarter}
                year={exp303Q.year}
                open={exp303Open}
                onClose={() => setExp303Open(false)}
            />
        </div>
    );
}
