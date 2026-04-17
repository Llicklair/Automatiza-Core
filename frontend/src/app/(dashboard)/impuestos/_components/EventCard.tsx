"use client";

import { Card, CardContent } from "@/components/ui/card";
import { type FiscalEvent } from "../_hooks/useImpuestos";

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

export function EventCard({ ev }: { ev: FiscalEvent }) {
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
            </CardContent>
        </Card>
    );
}
