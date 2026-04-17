"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export interface FiscalEvent {
    modelo: string;
    nombre: string;
    descripcion: string;
    fecha_limite: string;
    dias_restantes: number;
    tipo: string;
    urgente_dias: number;
}

export function useImpuestos() {
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

    return { events, loading, error, urgentes, proximos };
}
