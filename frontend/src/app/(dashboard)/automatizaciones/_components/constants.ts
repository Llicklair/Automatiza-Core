import {
    Zap, Clock, RefreshCw, CreditCard, Users, FileText,
} from "lucide-react";
import type { useTranslations } from "next-intl";

type Translator = ReturnType<typeof useTranslations>;

export function buildTriggerConfig(t: Translator): Record<string, { label: string; icon: React.ElementType; cls: string; title: string }> {
    return {
        event_based: {
            label: t("trigger.eventBasedLabel"),
            icon: Zap,
            cls: "text-amber-400 bg-amber-500/10 border-amber-500/20",
            title: t("trigger.eventBasedTitle"),
        },
        schedule_based: {
            label: t("trigger.scheduleBasedLabel"),
            icon: Clock,
            cls: "text-blue-400 bg-blue-500/10 border-blue-500/20",
            title: t("trigger.scheduleBasedTitle"),
        },
        manual: {
            label: t("trigger.manualLabel"),
            icon: RefreshCw,
            cls: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
            title: t("trigger.manualTitle"),
        },
    };
}

export function buildExecStatus(t: Translator): Record<string, { label: string; cls: string }> {
    return {
        running: { label: t("execStatus.running"), cls: "text-blue-400 bg-blue-500/10 border-blue-500/20" },
        completed: { label: t("execStatus.completed"), cls: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20" },
        success: { label: t("execStatus.completed"), cls: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20" },
        failed: { label: t("execStatus.failed"), cls: "text-red-400 bg-red-500/10 border-red-500/20" },
        paused: { label: t("execStatus.paused"), cls: "text-orange-400 bg-orange-500/10 border-orange-500/20" },
        pending: { label: t("execStatus.pending"), cls: "text-zinc-400 bg-zinc-800 border-zinc-700" },
    };
}

export interface Template {
    icon: React.ElementType;
    color: string;
    bg: string;
    border: string;
    name: string;
    description: string;
    trigger_type: string;
    trigger_config: { cron: string };
    action_type: string;
    action_config: { instruction: string };
}

export function buildTemplates(t: Translator): Template[] {
    return [
        {
            icon: CreditCard,
            color: "text-amber-400",
            bg: "bg-amber-500/10",
            border: "border-amber-500/20",
            name: t("templates.invoiceAlert.name"),
            description: t("templates.invoiceAlert.description"),
            trigger_type: "schedule_based",
            trigger_config: { cron: "0 9 * * 1" },
            action_type: "ai_task",
            action_config: { instruction: t("templates.invoiceAlert.instruction") },
        },
        {
            icon: Users,
            color: "text-blue-400",
            bg: "bg-blue-500/10",
            border: "border-blue-500/20",
            name: t("templates.monthlyPayroll.name"),
            description: t("templates.monthlyPayroll.description"),
            trigger_type: "schedule_based",
            trigger_config: { cron: "0 8 1 * *" },
            action_type: "ai_task",
            action_config: { instruction: t("templates.monthlyPayroll.instruction") },
        },
        {
            icon: FileText,
            color: "text-emerald-400",
            bg: "bg-emerald-500/10",
            border: "border-emerald-500/20",
            name: t("templates.weeklySales.name"),
            description: t("templates.weeklySales.description"),
            trigger_type: "schedule_based",
            trigger_config: { cron: "0 8 * * 1" },
            action_type: "ai_task",
            action_config: { instruction: t("templates.weeklySales.instruction") },
        },
    ];
}

export function buildDays(t: Translator): string[] {
    return [t("days.sun"), t("days.mon"), t("days.tue"), t("days.wed"), t("days.thu"), t("days.fri"), t("days.sat")];
}
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

export function cronToHuman(cron: string, t: Translator): string {
    const { freq, minute, hour, day, weekday } = parseCron(cron);
    const hhmm = `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
    const days = buildDays(t);
    if (freq === "minutes") return t("schedule.humanMinutes", { minute });
    if (freq === "hourly")  return t("schedule.humanHourly", { minute });
    if (freq === "daily")   return t("schedule.humanDaily", { time: hhmm });
    if (freq === "weekly")  return t("schedule.humanWeekly", { day: days[weekday], time: hhmm });
    return t("schedule.humanMonthly", { day, time: hhmm });
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
