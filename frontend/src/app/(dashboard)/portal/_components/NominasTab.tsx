"use client";
import { FileText, Download, Banknote } from "lucide-react";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api";
import type { Payroll } from "@/lib/api";
import { STATUS_BADGE, fmt, currency } from "./constants";

interface NominasTabProps {
    payrolls: Payroll[];
}

export function NominasTab({ payrolls }: NominasTabProps) {
    const t = useTranslations("portal");
    return (
        <div className="space-y-3">
            <p className="text-xs text-muted-foreground">
                {t("nominas.intro")}
            </p>
            {payrolls.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-40 gap-2 text-muted-foreground">
                    <FileText className="w-8 h-8 opacity-30" />
                    <p className="text-sm">{t("nominas.emptyTitle")}</p>
                    <p className="text-xs max-w-xs text-center">
                        {t("nominas.emptyHint")}
                    </p>
                </div>
            ) : (
                payrolls.map((p: Payroll) => (
                    <div key={p.id} className="flex items-center justify-between rounded-xl border border-border bg-card px-5 py-4">
                        <div className="flex items-center gap-4">
                            <Banknote className="w-5 h-5 text-emerald-400 shrink-0" />
                            <div>
                                <p className="text-sm font-medium text-foreground">
                                    {fmt(p.period_start)} — {fmt(p.period_end)}
                                </p>
                                <p className="text-xs text-muted-foreground">{t("nominas.issued", { date: fmt(p.issue_date) })}</p>
                            </div>
                        </div>
                        <div className="flex items-center gap-4">
                            <div className="text-right">
                                <p className="text-sm font-semibold text-foreground">{currency(p.net_salary)}</p>
                                <p className="text-xs text-muted-foreground">{t("nominas.net")}</p>
                            </div>
                            <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${STATUS_BADGE[p.status] ?? ""}`}>
                                {t.has(`payrollStatus.${p.status}`) ? t(`payrollStatus.${p.status}`) : p.status}
                            </span>
                            <button
                                onClick={() => api.hr.payrolls.downloadPdf(p.id, `nomina-${p.period_start.slice(0, 7)}.pdf`)}
                                className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
                                title={t("nominas.downloadPdf")}
                            >
                                <Download className="w-4 h-4" />
                            </button>
                        </div>
                    </div>
                ))
            )}
        </div>
    );
}
