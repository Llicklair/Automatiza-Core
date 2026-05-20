"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
    Sparkles, ArrowRight, Mail, Receipt, Calendar as CalendarIcon,
    TrendingUp, Clock, CheckCircle2, AlertCircle, Loader2,
} from "lucide-react";
import { api, type Task, type Invoice } from "@/lib/api";

interface BriefMetric {
    icon: typeof Mail;
    label: string;
    value: string;
    href?: string;
    accent?: "primary" | "amber" | "emerald" | "rose";
}

interface BriefAction {
    text: string;
    href: string;
    cta: string;
}

interface BriefData {
    tasksDone: number;
    invoicesIssuedToday: number;
    invoicesIssuedToday_amount: number;
    overdueCount: number;
    overdueAmount: number;
    nextDeadline: { modelo: string; nombre: string; dias: number } | null;
    minutesSaved: number;
    actions: BriefAction[];
}

function accentClasses(accent?: BriefMetric["accent"]) {
    switch (accent) {
        case "amber":
            return "bg-amber-500/10 text-amber-500 border-amber-500/20";
        case "emerald":
            return "bg-emerald-500/10 text-emerald-500 border-emerald-500/20";
        case "rose":
            return "bg-rose-500/10 text-rose-500 border-rose-500/20";
        default:
            return "bg-primary/10 text-primary border-primary/20";
    }
}

function computeBrief(invoices: Invoice[], tasks: Task[], vencimientos: any[]): BriefData {
    const today = new Date();
    const todayStr = today.toISOString().slice(0, 10);

    const issuedToday = invoices.filter((inv: any) => {
        const d: string | undefined = inv.issue_date ?? inv.created_at ?? inv.date;
        return typeof d === "string" && d.startsWith(todayStr);
    });
    const issuedToday_amount = issuedToday.reduce((s: number, inv: any) => s + Number(inv.total ?? inv.amount ?? 0), 0);

    const overdue = invoices.filter((inv: any) => {
        const due = inv.due_date ?? inv.fecha_vencimiento;
        const status = String(inv.status ?? "").toLowerCase();
        if (status === "paid" || status === "cobrada" || status === "pagada") return false;
        if (!due) return false;
        try { return new Date(due) < today; } catch { return false; }
    });
    const overdueAmount = overdue.reduce((s: number, inv: any) => s + Number(inv.total ?? inv.amount ?? 0), 0);

    const tasksDone = tasks.filter((t: any) => {
        const status = String(t.status ?? "").toLowerCase();
        return status === "done" || status === "completed";
    }).length;

    const next = vencimientos[0] ?? null;

    // Estimación bruta: 12 min ahorrados por tarea automatizada + 5 min por factura emitida automáticamente
    const minutesSaved = tasksDone * 12 + issuedToday.length * 5;

    const actions: BriefAction[] = [];
    if (overdue.length > 0) {
        actions.push({
            text: `Tienes ${overdue.length} factura${overdue.length === 1 ? "" : "s"} vencida${overdue.length === 1 ? "" : "s"} sin cobrar (${Math.round(overdueAmount).toLocaleString("es-ES")} €).`,
            href: "/ventas/facturas?status=overdue",
            cta: "Enviar recordatorios",
        });
    }
    if (next && next.dias_restantes <= 15) {
        actions.push({
            text: `El modelo ${next.modelo} (${next.nombre}) vence en ${next.dias_restantes} día${next.dias_restantes === 1 ? "" : "s"}.`,
            href: "/compliance",
            cta: "Preparar",
        });
    }
    if (issuedToday.length === 0 && new Date().getHours() >= 11) {
        actions.push({
            text: "Aún no has emitido ninguna factura hoy. ¿Hay algún albarán pendiente de facturar?",
            href: "/albaranes",
            cta: "Revisar albaranes",
        });
    }
    if (actions.length === 0) {
        actions.push({
            text: "Todo al día. Puedes pedirme cualquier cosa: «emite la factura del cliente X», «cuándo vence el próximo modelo», «resume el mes».",
            href: "/mi-equipo",
            cta: "Hablar con tu equipo",
        });
    }

    return {
        tasksDone,
        invoicesIssuedToday: issuedToday.length,
        invoicesIssuedToday_amount: issuedToday_amount,
        overdueCount: overdue.length,
        overdueAmount,
        nextDeadline: next ? { modelo: next.modelo, nombre: next.nombre, dias: next.dias_restantes } : null,
        minutesSaved,
        actions,
    };
}

function formatMinutes(m: number): string {
    if (m < 60) return `${m} min`;
    const h = Math.floor(m / 60);
    const rest = m % 60;
    return rest === 0 ? `${h} h` : `${h} h ${rest} min`;
}

export function MorningBrief() {
    const [data, setData] = useState<BriefData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(false);

    useEffect(() => {
        Promise.all([
            api.erp.invoices.list({ limit: 100 }).catch(() => []),
            api.tasks.list({ limit: 50 }).catch(() => []),
            api.advisory.calendar(90).catch(() => []),
        ])
            .then(([invoices, tasks, vencimientos]) => {
                setData(computeBrief(invoices as Invoice[], tasks as Task[], vencimientos as any[]));
            })
            .catch(() => setError(true))
            .finally(() => setLoading(false));
    }, []);

    if (loading) {
        return (
            <div className="rounded-2xl border border-primary/20 bg-gradient-to-br from-primary/5 via-card to-card p-6 shadow-sm">
                <div className="flex items-center gap-3 text-muted-foreground text-sm">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Preparando tu resumen del día...
                </div>
            </div>
        );
    }

    if (error || !data) {
        return null;
    }

    const metrics: BriefMetric[] = [
        {
            icon: TrendingUp,
            label: "Facturado hoy",
            value: data.invoicesIssuedToday > 0
                ? `${Math.round(data.invoicesIssuedToday_amount).toLocaleString("es-ES")} €`
                : "—",
            href: "/ventas/facturas",
            accent: "emerald",
        },
        {
            icon: Receipt,
            label: "Por cobrar",
            value: data.overdueCount > 0
                ? `${Math.round(data.overdueAmount).toLocaleString("es-ES")} €`
                : "Al día",
            href: "/ventas/facturas?status=overdue",
            accent: data.overdueCount > 0 ? "amber" : "emerald",
        },
        {
            icon: CalendarIcon,
            label: "Próximo vencimiento",
            value: data.nextDeadline
                ? `Mod. ${data.nextDeadline.modelo} · ${data.nextDeadline.dias}d`
                : "—",
            href: "/compliance",
            accent: data.nextDeadline && data.nextDeadline.dias <= 15 ? "rose" : "primary",
        },
        {
            icon: CheckCircle2,
            label: "Tareas IA cerradas",
            value: `${data.tasksDone}`,
            href: "/tareas",
            accent: "primary",
        },
    ];

    return (
        <div className="rounded-2xl border border-primary/20 bg-gradient-to-br from-primary/5 via-card to-card p-6 shadow-sm">
            {/* Cabecera narrativa */}
            <div className="flex items-start gap-4">
                <div className="flex-shrink-0 w-11 h-11 rounded-xl bg-primary/15 text-primary flex items-center justify-center">
                    <Sparkles className="w-5 h-5" />
                </div>
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 text-[11px] uppercase tracking-wider text-muted-foreground font-semibold">
                        <Clock className="w-3 h-3" />
                        Resumen del día · Tu equipo IA
                    </div>
                    <h2 className="mt-1 text-lg font-semibold text-foreground">
                        {data.minutesSaved > 0
                            ? <>Te he ahorrado <span className="text-primary">{formatMinutes(data.minutesSaved)}</span> hoy.</>
                            : "Listo para empezar el día contigo."}
                    </h2>
                    <p className="mt-0.5 text-sm text-muted-foreground">
                        {data.tasksDone > 0
                            ? `He cerrado ${data.tasksDone} tarea${data.tasksDone === 1 ? "" : "s"} y emitido ${data.invoicesIssuedToday} factura${data.invoicesIssuedToday === 1 ? "" : "s"}. Esto es lo más importante:`
                            : "Aquí tienes el panorama. Dime en qué te ayudo."}
                    </p>
                </div>
            </div>

            {/* Métricas */}
            <div className="mt-5 grid grid-cols-2 lg:grid-cols-4 gap-3">
                {metrics.map((m, i) => {
                    const Icon = m.icon;
                    const inner = (
                        <div className={`rounded-xl border p-3 transition-colors h-full ${accentClasses(m.accent)} hover:brightness-110`}>
                            <div className="flex items-center gap-2 text-[11px] font-medium uppercase tracking-wide opacity-80">
                                <Icon className="w-3.5 h-3.5" />
                                {m.label}
                            </div>
                            <div className="mt-1.5 text-lg font-semibold text-foreground">
                                {m.value}
                            </div>
                        </div>
                    );
                    return m.href
                        ? <Link key={i} href={m.href}>{inner}</Link>
                        : <div key={i}>{inner}</div>;
                })}
            </div>

            {/* Acciones recomendadas */}
            {data.actions.length > 0 && (
                <div className="mt-5 space-y-2">
                    {data.actions.map((a, i) => (
                        <Link
                            key={i}
                            href={a.href}
                            className="flex items-center gap-3 rounded-lg border border-border bg-background/50 hover:bg-background hover:border-primary/30 transition-colors p-3 group"
                        >
                            <AlertCircle className="w-4 h-4 text-primary flex-shrink-0" />
                            <span className="flex-1 text-sm text-foreground">{a.text}</span>
                            <span className="flex items-center gap-1 text-xs font-medium text-primary group-hover:gap-1.5 transition-all">
                                {a.cta}
                                <ArrowRight className="w-3.5 h-3.5" />
                            </span>
                        </Link>
                    ))}
                </div>
            )}
        </div>
    );
}
