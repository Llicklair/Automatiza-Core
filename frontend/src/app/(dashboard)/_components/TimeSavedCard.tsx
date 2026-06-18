"use client";

import { useEffect, useState } from "react";
import { Clock } from "lucide-react";
import { useTranslations } from "next-intl";
import { metricsApi, type TimeSavedSummary } from "@/lib/api/metrics";
import { ApiError } from "@/lib/api/errors";

type TFn = ReturnType<typeof useTranslations>;

const ACTION_LABEL_KEY: Record<string, string> = {
    create_invoice: "timeSaved.actionInvoicesCreated",
    invoice_created: "timeSaved.actionInvoicesCreated",
    create_journal_entry: "timeSaved.actionJournalEntries",
    journal_entry_created: "timeSaved.actionJournalEntries",
    reconcile_transaction: "timeSaved.actionReconciliations",
    banking_auto_reconciled: "timeSaved.actionAutoReconciliations",
    n43_imported: "timeSaved.actionStatementsImported",
    payroll_created: "timeSaved.actionPayrollsGenerated",
    payrolls_bulk_created: "timeSaved.actionPayrollBatches",
    approve_payroll: "timeSaved.actionPayrollsApproved",
    document_processed: "timeSaved.actionDocumentsProcessed",
    send_email: "timeSaved.actionEmailsSent",
    email_sent: "timeSaved.actionEmailsSent",
    aeat_presentation_confirmed: "timeSaved.actionPresentationsPrepared",
    approval_decision: "timeSaved.actionDecisionsManaged",
    ai_task: "timeSaved.actionAiTasksCompleted",
};

function formatTime(t: TFn, totalMinutes: number): string {
    if (totalMinutes < 60) return t("timeSaved.unitMinutes", { value: totalMinutes });
    const h = Math.floor(totalMinutes / 60);
    const m = totalMinutes % 60;
    return m ? t("timeSaved.unitHoursMinutes", { hours: h, minutes: m }) : t("timeSaved.unitHours", { value: h });
}

/**
 * Widget "Tiempo ahorrado por la IA" del centro de mando. Estimación
 * conservadora calculada en backend a partir del AuditLog (minutos de
 * trabajo manual equivalente por acción exitosa).
 */
export function TimeSavedCard() {
    const t = useTranslations("dashboard");
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
                if (active) setError(e instanceof ApiError ? e.detail : t("timeSaved.loadError"));
            })
            .finally(() => {
                if (active) setLoading(false);
            });
        return () => {
            active = false;
        };
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const top = summary?.breakdown.slice(0, 3) ?? [];

    return (
        <div className="bg-card border border-border rounded-2xl overflow-hidden">
            <div className="px-5 py-4 border-b border-border flex items-center justify-between">
                <h2 className="text-sm font-semibold text-foreground flex items-center gap-2">
                    <Clock className="w-4 h-4 text-primary" /> {t("timeSaved.title")}
                </h2>
                <span className="text-[10px] text-muted-foreground uppercase tracking-wide">{t("timeSaved.last30Days")}</span>
            </div>
            <div className="p-5">
                {loading ? (
                    <div className="h-16 animate-pulse rounded-lg bg-muted" />
                ) : error ? (
                    <p className="text-xs text-muted-foreground">{error}</p>
                ) : !summary || summary.total_actions === 0 ? (
                    <p className="text-xs text-muted-foreground">
                        {t("timeSaved.empty")}
                    </p>
                ) : (
                    <>
                        <div className="flex items-baseline gap-2">
                            <span className="text-3xl font-bold text-foreground">{formatTime(t, summary.total_minutes)}</span>
                            <span className="text-xs text-muted-foreground">
                                {t("timeSaved.inActions", { count: summary.total_actions })}
                            </span>
                        </div>
                        {top.length > 0 && (
                            <ul className="mt-4 space-y-1.5">
                                {top.map((item) => (
                                    <li key={item.action_type} className="flex items-center justify-between text-xs">
                                        <span className="text-muted-foreground">
                                            {ACTION_LABEL_KEY[item.action_type] ? t(ACTION_LABEL_KEY[item.action_type]) : item.action_type} × {item.count}
                                        </span>
                                        <span className="font-medium text-foreground">{formatTime(t, item.minutes)}</span>
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
