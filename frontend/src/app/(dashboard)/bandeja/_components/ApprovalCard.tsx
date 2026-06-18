"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import type { Approval } from "@/lib/api";
import { CheckCircle2, XCircle, Clock, ChevronDown } from "lucide-react";
import { RISK_STYLE, buildRiskLabels, minutesUntil } from "./approval-constants";

// Helper para evitar error de importación si CheckCircle2 no funciona bien a veces
const CheckCircle = CheckCircle2;

export function ApprovalCard({
    approval: a,
    deciding,
    onApprove,
    onRejectClick,
}: {
    approval: Approval;
    deciding: string | null;
    onApprove: (id: string) => void;
    onRejectClick: (id: string) => void;
}) {
    const t = useTranslations("bandeja");
    const [open, setOpen] = useState(false);
    const riskLabels = buildRiskLabels(t);
    const mins = minutesUntil(a.expires_at);
    const urgent = mins < 15;

    return (
        <div
            className={`rounded-xl border p-6 transition duration-300 ${urgent ? "border-amber-500/40 bg-amber-500/5" : "border-border bg-card"
                }`}
        >
            <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                    <p className="text-foreground font-medium">{a.action_description}</p>

                    <div className="flex items-center gap-3 mt-3">
                        <span className={`text-xs px-2.5 py-1 rounded-full border font-medium ${RISK_STYLE[a.risk_level] ?? RISK_STYLE.low}`}>
                            {t("approvals.riskBadge", { level: riskLabels[a.risk_level] ?? a.risk_level })}
                        </span>
                        <span className={`flex items-center gap-1 text-xs ${urgent ? "text-amber-400" : "text-muted-foreground"}`}>
                            <Clock className="w-3.5 h-3.5" />
                            {mins > 0 ? t("approvals.expiresIn", { mins }) : t("approvals.expired")}
                        </span>
                    </div>

                    {Boolean(a.action_payload) && (
                        <div className="mt-4">
                            <button
                                onClick={() => setOpen(!open)}
                                className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground transition-colors select-none"
                            >
                                <span>{t("approvals.viewDetails")}</span>
                                <ChevronDown className={`w-3.5 h-3.5 transition-transform duration-300 ${open ? "rotate-180" : ""}`} />
                            </button>
                            <div
                                className={`grid transition-[grid-template-rows,opacity,margin] duration-300 ease-in-out ${open ? "grid-rows-[1fr] opacity-100 mt-3" : "grid-rows-[0fr] opacity-0 mt-0"
                                    }`}
                            >
                                <div className="overflow-hidden">
                                    <pre className="px-4 py-3 rounded-lg bg-background text-xs text-foreground border border-border overflow-x-auto">
                                        {JSON.stringify(a.action_payload, null, 2)}
                                    </pre>
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                <div className="flex gap-2 flex-shrink-0">
                    <button
                        onClick={() => onRejectClick(a.id)}
                        disabled={deciding === a.id || mins === 0}
                        className="flex items-center gap-1.5 px-4 py-2 rounded-lg border border-red-500/30 text-red-400 hover:bg-red-500/10 disabled:opacity-40 text-sm transition"
                    >
                        <XCircle className="w-4 h-4" /> {t("approvals.reject")}
                    </button>
                    <button
                        onClick={() => onApprove(a.id)}
                        disabled={deciding === a.id || mins === 0}
                        className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-foreground text-sm transition shadow-[0_0_15px_rgba(16,185,129,0.2)] hover:shadow-[0_0_20px_rgba(16,185,129,0.3)]"
                    >
                        <CheckCircle className="w-4 h-4" /> {t("approvals.approve")}
                    </button>
                </div>
            </div>
        </div>
    );
}
