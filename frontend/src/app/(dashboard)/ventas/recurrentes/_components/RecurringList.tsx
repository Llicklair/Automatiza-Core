"use client";

import { type RecurringInvoice } from "@/lib/api";
import { fmt, INTERVAL_MAP, INTERVAL_COLORS } from "../_hooks/useRecurrentes";
import {
    RefreshCw, Play, Pause, Pencil, Trash2,
    Loader2, Calendar, CheckCircle2
} from "lucide-react";

interface RecurringListProps {
    items: RecurringInvoice[];
    runningId: string | null;
    deletingId: string | null;
    onRun: (rec: RecurringInvoice) => void;
    onToggleActive: (rec: RecurringInvoice) => void;
    onEdit: (rec: RecurringInvoice) => void;
    onDelete: (id: string) => void;
    t: (key: string, params?: any) => string;
}

export default function RecurringList({
    items, runningId, deletingId,
    onRun, onToggleActive, onEdit, onDelete, t,
}: RecurringListProps) {
    return (
        <div className="bg-card border border-border rounded-2xl overflow-hidden">
            <div className="grid grid-cols-12 gap-4 px-6 py-3 border-b border-border text-xs font-medium text-muted-foreground uppercase tracking-wide bg-muted">
                <div className="col-span-3">{t("templateName")}</div>
                <div className="col-span-2">{t("client")}</div>
                <div className="col-span-2">{t("intervalType")}</div>
                <div className="col-span-2">{t("nextIssue")}</div>
                <div className="col-span-1 text-right">{t("recurringAmount")}</div>
                <div className="col-span-2 text-right">{t("recurringActions")}</div>
            </div>
            {items.map(rec => {
                const totalRec = rec.lines_json.reduce((acc, l) => acc + l.quantity * l.unit_price * (1 + l.tax_percentage / 100), 0);
                const isDue = rec.is_active && rec.next_run_date <= new Date().toISOString().split("T")[0];
                const intervalCls = INTERVAL_COLORS[rec.interval_type] || "text-muted-foreground bg-muted border-border";

                return (
                    <div key={rec.id} className="grid grid-cols-12 gap-4 px-6 py-4 border-b border-border/50 last:border-0 hover:bg-accent/50 transition-colors items-center">
                        <div className="col-span-3 flex items-center gap-3">
                            <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${rec.is_active ? "bg-primary/10 border border-primary/20" : "bg-muted border border-border"}`}>
                                <RefreshCw className={`w-4 h-4 ${rec.is_active ? "text-primary" : "text-muted-foreground"}`} />
                            </div>
                            <div>
                                <p className={`text-sm font-medium ${rec.is_active ? "text-foreground" : "text-muted-foreground"}`}>{rec.name}</p>
                                {!rec.is_active && <p className="text-xs text-muted-foreground">{t("recurringPaused")}</p>}
                            </div>
                        </div>
                        <div className="col-span-2">
                            <p className="text-sm text-foreground truncate">{rec.client?.name || "\u2014"}</p>
                        </div>
                        <div className="col-span-2">
                            <span className={`text-xs px-2 py-1 rounded-full border ${intervalCls}`}>
                                {INTERVAL_MAP[rec.interval_type] || rec.interval_type}
                            </span>
                        </div>
                        <div className="col-span-2">
                            <div className="flex items-center gap-1.5">
                                <Calendar className={`w-3 h-3 ${isDue ? "text-amber-400" : "text-muted-foreground"}`} />
                                <span className={`text-sm ${isDue ? "text-amber-400 font-medium" : "text-muted-foreground"}`}>
                                    {new Date(rec.next_run_date).toLocaleDateString("es-ES")}
                                </span>
                                {isDue && <span className="text-xs bg-amber-500/20 text-amber-400 px-1.5 py-0.5 rounded-md border border-amber-500/30">{t("recurringOverdue")}</span>}
                            </div>
                            {rec.last_run_date && (
                                <p className="text-xs text-muted-foreground mt-0.5 flex items-center gap-1">
                                    <CheckCircle2 className="w-3 h-3" /> {t("recurringLastRun")}: {new Date(rec.last_run_date).toLocaleDateString("es-ES")}
                                </p>
                            )}
                        </div>
                        <div className="col-span-1 text-right">
                            <p className="text-sm font-bold text-foreground font-mono">{fmt(totalRec)}</p>
                        </div>
                        <div className="col-span-2 flex items-center justify-end gap-1">
                            <button onClick={() => onRun(rec)} disabled={runningId === rec.id} title={t("recurringRunNow")}
                                className="p-1.5 rounded-lg hover:bg-emerald-500/10 text-muted-foreground hover:text-emerald-400 transition-colors" aria-label={t("recurringRunNow")}>
                                {runningId === rec.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" aria-hidden="true" /> : <Play className="w-3.5 h-3.5" aria-hidden="true" />}
                            </button>
                            <button onClick={() => onToggleActive(rec)} title={rec.is_active ? t("recurringPause") : t("recurringActivate")}
                                className="p-1.5 rounded-lg hover:bg-amber-500/10 text-muted-foreground hover:text-amber-400 transition-colors" aria-label={rec.is_active ? t("recurringPause") : t("recurringActivate")}>
                                {rec.is_active ? <Pause className="w-3.5 h-3.5" aria-hidden="true" /> : <Play className="w-3.5 h-3.5 text-emerald-400" aria-hidden="true" />}
                            </button>
                            <button onClick={() => onEdit(rec)} className="p-1.5 rounded-lg hover:bg-accent text-muted-foreground hover:text-foreground transition-colors" aria-label={t("editRecurringAria")}>
                                <Pencil className="w-3.5 h-3.5" aria-hidden="true" />
                            </button>
                            <button onClick={() => onDelete(rec.id)} disabled={deletingId === rec.id}
                                className="p-1.5 rounded-lg hover:bg-rose-500/10 text-muted-foreground hover:text-rose-400 transition-colors" aria-label={t("deleteRecurringAria")}>
                                {deletingId === rec.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" aria-hidden="true" /> : <Trash2 className="w-3.5 h-3.5" aria-hidden="true" />}
                            </button>
                        </div>
                    </div>
                );
            })}
        </div>
    );
}
