"use client";

import { useTranslations } from "next-intl";

const STATUS_STYLE: Record<string, { color: string; dot: string }> = {
    pending: { color: "text-muted-foreground", dot: "bg-muted-foreground" },
    planning: { color: "text-blue-400", dot: "bg-blue-400" },
    executing: { color: "text-primary", dot: "bg-primary" },
    awaiting_approval: { color: "text-amber-400", dot: "bg-amber-400" },
    done: { color: "text-emerald-400", dot: "bg-emerald-400" },
    failed: { color: "text-red-400", dot: "bg-red-500" },
    cancelled: { color: "text-muted-foreground", dot: "bg-accent" },
};

const STATUS_LABEL_KEY: Record<string, string> = {
    pending: "badges.statusPending",
    planning: "badges.statusPlanning",
    executing: "badges.statusExecuting",
    awaiting_approval: "badges.statusAwaitingApproval",
    done: "badges.statusDone",
    failed: "badges.statusFailed",
    cancelled: "badges.statusCancelled",
};

export function StatusBadge({ status }: { status: string }) {
    const t = useTranslations("dashboard");
    const style = STATUS_STYLE[status] ?? { color: "text-muted-foreground", dot: "bg-muted-foreground" };
    const labelKey = STATUS_LABEL_KEY[status];
    const label = labelKey ? t(labelKey) : status;
    return (
        <span className={`inline-flex items-center gap-1.5 text-[11px] font-medium px-2.5 py-1 rounded-full bg-muted border border-border ${style.color}`}>
            <span className={`w-1.5 h-1.5 rounded-full ${style.dot}`} />
            {label}
        </span>
    );
}

export function InvBadge({ status }: { status: string }) {
    const t = useTranslations("dashboard");
    switch (status) {
        case 'draft': return <span className="text-[10px] uppercase font-bold text-muted-foreground">{t("badges.invDraft")}</span>;
        case 'pending': return <span className="text-[10px] uppercase font-bold text-amber-500">{t("badges.invPending")}</span>;
        case 'paid': return <span className="text-[10px] uppercase font-bold text-emerald-500">{t("badges.invPaid")}</span>;
        case 'overdue': return <span className="text-[10px] uppercase font-bold text-red-500">{t("badges.invOverdue")}</span>;
        default: return <span className="text-[10px] uppercase font-bold text-muted-foreground">{status}</span>;
    }
}
