"use client";

import { useEffect, useState } from "react";
import { Clock } from "lucide-react";
import { metricsApi, type TimeSavedSummary } from "@/lib/api/metrics";
import { ApiError } from "@/lib/api/errors";

const ACTION_LABELS: Record<string, string> = {
    create_invoice: "Facturas creadas",
    invoice_created: "Facturas creadas",
    create_journal_entry: "Asientos contables",
    journal_entry_created: "Asientos contables",
    reconcile_transaction: "Conciliaciones",
    banking_auto_reconciled: "Conciliaciones automáticas",
    n43_imported: "Extractos importados",
    payroll_created: "Nóminas generadas",
    payrolls_bulk_created: "Lotes de nóminas",
    approve_payroll: "Nóminas aprobadas",
    document_processed: "Documentos procesados",
    send_email: "Emails enviados",
    email_sent: "Emails enviados",
    aeat_presentation_confirmed: "Presentaciones preparadas",
    approval_decision: "Decisiones gestionadas",
    ai_task: "Tareas IA completadas",
};

function formatTime(totalMinutes: number): string {
    if (totalMinutes < 60) return `${totalMinutes} min`;
    const h = Math.floor(totalMinutes / 60);
    const m = totalMinutes % 60;
    return m ? `${h} h ${m} min` : `${h} h`;
}

/**
 * Widget "Tiempo ahorrado por la IA" del centro de mando. Estimación
 * conservadora calculada en backend a partir del AuditLog (minutos de
 * trabajo manual equivalente por acción exitosa).
 */
export function TimeSavedCard() {
    const [summary, setSummary] = useState<TimeSavedSummary | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        let active = true;
        metricsApi
            .timeSaved(30)
            .then((res) => {
                if (active) setSummary(res);
            })
            .catch((e) => {
                if (active) setError(e instanceof ApiError ? e.detail : "No se pudo cargar la métrica");
            })
            .finally(() => {
                if (active) setLoading(false);
            });
        return () => {
            active = false;
        };
    }, []);

    const top = summary?.breakdown.slice(0, 3) ?? [];

    return (
        <div className="bg-card border border-border rounded-2xl overflow-hidden">
            <div className="px-5 py-4 border-b border-border flex items-center justify-between">
                <h2 className="text-sm font-semibold text-foreground flex items-center gap-2">
                    <Clock className="w-4 h-4 text-primary" /> Tiempo ahorrado por la IA
                </h2>
                <span className="text-[10px] text-muted-foreground uppercase tracking-wide">Últimos 30 días</span>
            </div>
            <div className="p-5">
                {loading ? (
                    <div className="h-16 animate-pulse rounded-lg bg-muted" />
                ) : error ? (
                    <p className="text-xs text-muted-foreground">{error}</p>
                ) : !summary || summary.total_actions === 0 ? (
                    <p className="text-xs text-muted-foreground">
                        Aún no hay actividad de la IA este mes. Cuando los agentes trabajen, verás aquí el tiempo que te ahorran.
                    </p>
                ) : (
                    <>
                        <div className="flex items-baseline gap-2">
                            <span className="text-3xl font-bold text-foreground">{formatTime(summary.total_minutes)}</span>
                            <span className="text-xs text-muted-foreground">
                                en {summary.total_actions} {summary.total_actions === 1 ? "acción" : "acciones"}
                            </span>
                        </div>
                        {top.length > 0 && (
                            <ul className="mt-4 space-y-1.5">
                                {top.map((item) => (
                                    <li key={item.action_type} className="flex items-center justify-between text-xs">
                                        <span className="text-muted-foreground">
                                            {ACTION_LABELS[item.action_type] ?? item.action_type} × {item.count}
                                        </span>
                                        <span className="font-medium text-foreground">{formatTime(item.minutes)}</span>
                                    </li>
                                ))}
                            </ul>
                        )}
                    </>
                )}
            </div>
        </div>
    );
}
