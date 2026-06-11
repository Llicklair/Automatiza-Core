"use client";

import { useTranslations } from "next-intl";
import { useFormat } from "@/hooks/useFormat";
import { Calculator, CheckCircle2, Loader2, X } from "lucide-react";
import { endOfMonth, startOfMonth } from "date-fns";
import type { Employee, PayrollCalculation } from "@/lib/api";

interface Props {
    autoEmployees:      Employee[];
    autoEmpLoading:     boolean;
    autoEmpId:          string;
    setAutoEmpId:       (id: string) => void;
    autoPreview:        PayrollCalculation | null;
    autoPreviewLoading: boolean;
    autoSubmitting:     boolean;
    fmt:                (v: number) => string;
    onClose:            () => void;
    onSubmit:           () => void;
}

export function AutoPayrollModal({
    autoEmployees, autoEmpLoading, autoEmpId, setAutoEmpId,
    autoPreview, autoPreviewLoading, autoSubmitting,
    fmt, onClose, onSubmit,
}: Props) {
    const t = useTranslations("rrhh");
    const tc = useTranslations("common");
    const { fmtDate } = useFormat();
    return (
        <div
            className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
            role="dialog"
            aria-modal="true"
            aria-labelledby="auto-payroll-title"
            onClick={(e) => e.target === e.currentTarget && !autoSubmitting && onClose()}
        >
            <div className="w-full max-w-lg rounded-2xl border border-border bg-card shadow-2xl overflow-hidden">
                <div className="flex items-center justify-between px-5 py-4 border-b border-border">
                    <h2 id="auto-payroll-title" className="text-lg font-medium text-foreground flex items-center gap-2">
                        <Calculator className="w-5 h-5 text-emerald-400" />
                        {t("nominas.autoModal.title")}
                    </h2>
                    <button type="button" disabled={autoSubmitting} onClick={onClose}
                        className="p-2 rounded-lg text-muted-foreground hover:bg-muted disabled:opacity-50" aria-label={tc("close")}>
                        <X className="w-4 h-4" />
                    </button>
                </div>

                <div className="p-5 space-y-4 max-h-[70vh] overflow-y-auto">
                    {autoEmpLoading ? (
                        <div className="flex justify-center py-8">
                            <Loader2 className="w-8 h-8 animate-spin text-emerald-500" />
                        </div>
                    ) : autoEmployees.length === 0 ? (
                        <p className="text-sm text-muted-foreground text-center py-4">{t("nominas.autoModal.noEmployees")}</p>
                    ) : (
                        <>
                            <label className="block text-xs text-muted-foreground uppercase tracking-wide">{t("nominas.autoModal.employee")}</label>
                            <select value={autoEmpId} onChange={(e) => setAutoEmpId(e.target.value)}
                                className="w-full bg-background border border-border rounded-lg px-3 py-2.5 text-sm text-foreground focus:outline-none focus:border-emerald-500">
                                {autoEmployees.map((e) => (
                                    <option key={e.id} value={e.id}>
                                        {e.name} — {e.base_salary != null ? t("nominas.autoModal.salaryPerMonth", { amount: fmt(e.base_salary) }) : t("nominas.autoModal.noBaseSalary")}
                                    </option>
                                ))}
                            </select>
                            <p className="text-xs text-muted-foreground">
                                {t("nominas.autoModal.period")}{" "}
                                <span className="text-foreground">
                                    {fmtDate(startOfMonth(new Date()), { day: "numeric", month: "short" })} –{" "}
                                    {fmtDate(endOfMonth(new Date()), { day: "numeric", month: "short", year: "numeric" })}
                                </span>
                            </p>
                            <div className="rounded-xl border border-border bg-background p-4">
                                <p className="text-xs font-medium text-muted-foreground mb-3">{t("nominas.autoModal.previewTitle")}</p>
                                {autoPreviewLoading ? (
                                    <div className="flex justify-center py-6">
                                        <Loader2 className="w-6 h-6 animate-spin text-emerald-500" />
                                    </div>
                                ) : autoPreview ? (
                                    <dl className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-sm">
                                        <dt className="text-muted-foreground">{t("nominas.autoModal.gross")}</dt>
                                        <dd className="text-right text-foreground">{fmt(autoPreview.base_salary)}</dd>
                                        <dt className="text-muted-foreground text-[11px] col-span-2 pt-1 border-t border-border">
                                            {t("nominas.autoModal.ssContributions")}
                                        </dt>
                                        <dt className="text-muted-foreground pl-2 text-xs">{t("nominas.autoModal.commonContingencies")}</dt>
                                        <dd className="text-right text-red-400/80 text-xs">−{fmt(autoPreview.ss_contingencias_comunes)}</dd>
                                        <dt className="text-muted-foreground pl-2 text-xs">{t("nominas.autoModal.unemployment")}</dt>
                                        <dd className="text-right text-red-400/80 text-xs">−{fmt(autoPreview.ss_desempleo)}</dd>
                                        <dt className="text-muted-foreground pl-2 text-xs">{t("nominas.autoModal.professionalTraining")}</dt>
                                        <dd className="text-right text-red-400/80 text-xs">−{fmt(autoPreview.ss_formacion_profesional)}</dd>
                                        <dt className="text-muted-foreground pl-2 text-xs">{t("nominas.autoModal.mei")}</dt>
                                        <dd className="text-right text-red-400/80 text-xs">−{fmt(autoPreview.ss_mei)}</dd>
                                        <dt className="text-muted-foreground">{t("nominas.autoModal.totalSs")}</dt>
                                        <dd className="text-right text-red-400/90">−{fmt(autoPreview.total_ss)}</dd>
                                        <dt className="text-muted-foreground">{t("nominas.autoModal.irpf", { rate: autoPreview.irpf_rate_applied })}</dt>
                                        <dd className="text-right text-red-400/90">−{fmt(autoPreview.irpf)}</dd>
                                        <dt className="text-muted-foreground">{t("nominas.autoModal.totalDeductions")}</dt>
                                        <dd className="text-right text-muted-foreground">−{fmt(autoPreview.deductions)}</dd>
                                        <dt className="text-muted-foreground font-medium pt-1 border-t border-border">{t("nominas.autoModal.estimatedNet")}</dt>
                                        <dd className="text-right font-semibold text-emerald-400 pt-1 border-t border-border">{fmt(autoPreview.net_salary)}</dd>
                                    </dl>
                                ) : (
                                    <p className="text-xs text-muted-foreground py-2">{t("nominas.autoModal.selectEmployeeHint")}</p>
                                )}
                            </div>
                        </>
                    )}
                </div>

                <div className="flex justify-end gap-2 px-5 py-4 border-t border-border bg-background">
                    <button type="button" disabled={autoSubmitting} onClick={onClose}
                        className="px-4 py-2 text-sm rounded-lg text-muted-foreground hover:bg-muted disabled:opacity-50">
                        {tc("cancel")}
                    </button>
                    <button type="button"
                        disabled={autoSubmitting || !autoEmpId || autoPreviewLoading || !autoPreview || autoEmployees.length === 0}
                        onClick={onSubmit}
                        className="flex items-center gap-2 px-4 py-2 text-sm rounded-lg font-medium bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-foreground">
                        {autoSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
                        {t("nominas.autoModal.createDraft")}
                    </button>
                </div>
            </div>
        </div>
    );
}
