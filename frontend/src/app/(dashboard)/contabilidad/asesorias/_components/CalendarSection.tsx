"use client";

import { CalendarDays, AlertCircle } from "lucide-react";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";

interface CalendarSectionProps {
    events: any[];
    filter: string;
}

export function CalendarSection({ events, filter }: CalendarSectionProps) {
    const t = useTranslations("contabilidad");
    return (
        <>
            <div className="flex items-center gap-2">
                <CalendarDays className="w-5 h-5 text-muted-foreground" />
                <h2 className="text-xl font-semibold text-foreground">{t("calendar.title")}</h2>
            </div>

            <div className="bg-card border border-border rounded-2xl overflow-hidden shadow-lg shadow-black/20">
                {events.length === 0 ? (
                    <div className="p-8 text-center text-muted-foreground text-sm">
                        {filter === "mercantil"
                            ? t("calendar.emptyMercantil")
                            : t("calendar.emptyUpcoming")}
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
                                                {t("calendar.modelLabel", { modelo: evt.modelo })}
                                            </span>
                                            {isUrgent && (
                                                <span className="flex items-center gap-1 text-xs text-red-400 bg-red-500/10 px-2 py-0.5 rounded-full ring-1 ring-red-500/20">
                                                    <AlertCircle className="w-3 h-3" />
                                                    {t("calendar.urgent")}
                                                </span>
                                            )}
                                        </div>
                                        <span className={cn(
                                            "text-xs font-medium px-2 py-0.5 rounded-full bg-accent/50",
                                            isUrgent ? "text-red-400 border border-red-500/20" : "text-emerald-400 border border-emerald-500/20"
                                        )}>
                                            {t("calendar.daysLeft", { dias: evt.dias_restantes })}
                                        </span>
                                    </div>
                                    <h3 className="text-foreground font-medium">{evt.nombre}</h3>
                                    <p className="text-muted-foreground text-sm mt-1">{evt.descripcion}</p>
                                    <div className="mt-3 text-xs text-muted-foreground flex items-center gap-2">
                                        <CalendarDays className="w-3.5 h-3.5 opacity-70" />
                                        {t("calendar.dueDate")} <span className="text-foreground font-medium">{new Date(evt.fecha_limite).toLocaleDateString()}</span>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>
        </>
    );
}
