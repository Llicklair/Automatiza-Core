"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { BellRing, ChevronRight } from "lucide-react";
import { api, type AlertEntry } from "@/lib/api";
import { logError } from "@/lib/logger";

const TYPE_LABEL_KEY: Record<AlertEntry["alert_type"], string> = {
    overdue_invoice: "alertsWidget.overdueInvoice",
    due_soon_invoice: "alertsWidget.dueSoonInvoice",
    low_stock: "alertsWidget.lowStock",
    pending_payroll: "alertsWidget.pendingPayroll",
};

/** Resumen compacto de alertas de negocio en la portada (audit UX P3-14):
 *  "qué requiere mi atención" sin tener que visitar /alertas. Se oculta si
 *  no hay ninguna, para no añadir ruido. */
export function AlertsWidget() {
    const t = useTranslations("dashboard");
    const [alerts, setAlerts] = useState<AlertEntry[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        api.alerts
            .list()
            .then(setAlerts)
            .catch((e) => logError("dashboard/alerts-widget", e))
            .finally(() => setLoading(false));
    }, []);

    if (loading || alerts.length === 0) return null;

    return (
        <Link
            href="/alertas"
            className="block bg-card border border-amber-500/20 rounded-2xl p-4 hover:bg-muted/40 transition-colors"
        >
            <div className="flex items-center justify-between">
                <span className="flex items-center gap-2 text-sm font-semibold text-amber-400">
                    <BellRing className="w-4 h-4" /> {t("alertsWidget.title")}
                    <span className="px-2 py-0.5 rounded-full bg-amber-500/15 border border-amber-500/30 text-xs">
                        {alerts.length}
                    </span>
                </span>
                <ChevronRight className="w-4 h-4 text-muted-foreground" />
            </div>
            <ul className="mt-2 space-y-1">
                {alerts.slice(0, 3).map((a) => (
                    <li key={a.id} className="text-xs text-muted-foreground truncate">
                        • {t(TYPE_LABEL_KEY[a.alert_type] ?? "alertsWidget.generic")} · {a.entity_label}
                    </li>
                ))}
                {alerts.length > 3 && (
                    <li className="text-[11px] text-muted-foreground/70">
                        {t("alertsWidget.more", { n: alerts.length - 3 })}
                    </li>
                )}
            </ul>
        </Link>
    );
}
