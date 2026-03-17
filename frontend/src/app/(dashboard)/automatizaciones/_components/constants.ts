import {
    Zap, Clock, RefreshCw, CreditCard, Users, FileText,
} from "lucide-react";

export const TRIGGER_CONFIG: Record<string, { label: string; icon: React.ElementType; cls: string; title: string }> = {
    event_based: {
        label: "Eventual",
        icon: Zap,
        cls: "text-amber-400 bg-amber-500/10 border-amber-500/20",
        title: "Se dispara cuando ocurre un evento en el ERP (factura creada, empleado modificado, etc.)",
    },
    schedule_based: {
        label: "De tiempo",
        icon: Clock,
        cls: "text-blue-400 bg-blue-500/10 border-blue-500/20",
        title: "Se ejecuta en una programación de tiempo definida (cron).",
    },
    manual: {
        label: "Constante",
        icon: RefreshCw,
        cls: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
        title: "Disponible en todo momento. Se lanza a demanda desde la UI o la API.",
    },
};

export const EXEC_STATUS: Record<string, { label: string; cls: string }> = {
    running: { label: "Ejecutando", cls: "text-blue-400 bg-blue-500/10 border-blue-500/20" },
    completed: { label: "Completada", cls: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20" },
    success: { label: "Completada", cls: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20" },
    failed: { label: "Error", cls: "text-red-400 bg-red-500/10 border-red-500/20" },
    paused: { label: "Pausada", cls: "text-orange-400 bg-orange-500/10 border-orange-500/20" },
    pending: { label: "Pendiente", cls: "text-zinc-400 bg-zinc-800 border-zinc-700" },
};

export const TEMPLATES = [
    {
        icon: CreditCard,
        color: "text-amber-400",
        bg: "bg-amber-500/10",
        border: "border-amber-500/20",
        name: "Alerta facturas vencidas",
        description: "Detecta facturas sin pagar y avisa por email",
        trigger_type: "schedule_based",
        trigger_config: { cron: "0 9 * * 1" },
        action_type: "ai_task",
        action_config: { instruction: "Revisa todas las facturas con más de 30 días sin pagar y envía un recordatorio por email a cada cliente con el importe pendiente y fecha de vencimiento." },
    },
    {
        icon: Users,
        color: "text-blue-400",
        bg: "bg-blue-500/10",
        border: "border-blue-500/20",
        name: "Nóminas mensuales automáticas",
        description: "Genera y envía las nóminas el día 1 de cada mes",
        trigger_type: "schedule_based",
        trigger_config: { cron: "0 8 1 * *" },
        action_type: "ai_task",
        action_config: { instruction: "El día 1 de cada mes, genera las nóminas de todos los empleados activos y envíales el documento por email." },
    },
    {
        icon: FileText,
        color: "text-emerald-400",
        bg: "bg-emerald-500/10",
        border: "border-emerald-500/20",
        name: "Informe semanal de ventas",
        description: "Resumen ejecutivo cada lunes por la mañana",
        trigger_type: "schedule_based",
        trigger_config: { cron: "0 8 * * 1" },
        action_type: "ai_task",
        action_config: { instruction: "Cada lunes, genera un resumen de las ventas de la semana anterior: facturas emitidas, cobradas, pendientes y comparativa con la semana anterior." },
    },
];

export const DAYS = ["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"];
export const MONTHS_DAYS = Array.from({ length: 28 }, (_, i) => i + 1);
export const HOURS = Array.from({ length: 24 }, (_, i) => i);
export const MINUTES_OPTIONS = [0, 5, 10, 15, 20, 30, 45];

export type FreqKey = "minutes" | "hourly" | "daily" | "weekly" | "monthly";

export function parseCron(cron: string): { freq: FreqKey; minute: number; hour: number; day: number; weekday: number } {
    const parts = cron.trim().split(/\s+/);
    if (parts.length !== 5) return { freq: "daily", minute: 0, hour: 9, day: 1, weekday: 1 };
    const [min, hr, dom, , dow] = parts;
    if (min.startsWith("*/")) return { freq: "minutes", minute: parseInt(min.slice(2)) || 5, hour: 9, day: 1, weekday: 1 };
    if (hr === "*") return { freq: "hourly", minute: parseInt(min) || 0, hour: 9, day: 1, weekday: 1 };
    if (dom === "*" && dow === "*") return { freq: "daily", minute: parseInt(min) || 0, hour: parseInt(hr) || 9, day: 1, weekday: 1 };
    if (dom === "*" && dow !== "*") return { freq: "weekly", minute: parseInt(min) || 0, hour: parseInt(hr) || 9, day: 1, weekday: parseInt(dow) || 1 };
    return { freq: "monthly", minute: parseInt(min) || 0, hour: parseInt(hr) || 9, day: parseInt(dom) || 1, weekday: 1 };
}

export function buildCron(freq: FreqKey, minute: number, hour: number, day: number, weekday: number): string {
    if (freq === "minutes") return `*/${minute} * * * *`;
    if (freq === "hourly")  return `${minute} * * * *`;
    if (freq === "daily")   return `${minute} ${hour} * * *`;
    if (freq === "weekly")  return `${minute} ${hour} * * ${weekday}`;
    return `${minute} ${hour} ${day} * *`;
}

export function cronToHuman(cron: string): string {
    const { freq, minute, hour, day, weekday } = parseCron(cron);
    const hhmm = `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
    if (freq === "minutes") return `Cada ${minute} minutos`;
    if (freq === "hourly")  return `Cada hora, al minuto ${minute}`;
    if (freq === "daily")   return `Cada día a las ${hhmm}`;
    if (freq === "weekly")  return `Cada ${DAYS[weekday]} a las ${hhmm}`;
    return `El día ${day} de cada mes a las ${hhmm}`;
}

export function hasFanOut(edges: any[] | null | undefined): boolean {
    if (!edges || edges.length === 0) return false;
    const counts: Record<string, number> = {};
    for (const e of edges) {
        const src = e.source;
        if (src) counts[src] = (counts[src] || 0) + 1;
    }
    return Object.values(counts).some(v => v >= 2);
}
