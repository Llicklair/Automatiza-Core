"use client";
import { FileText, Download, Banknote } from "lucide-react";
import { api } from "@/lib/api";
import type { Payroll } from "@/lib/api";
import { STATUS_BADGE, PAYROLL_LABEL, fmt, currency } from "./constants";

interface NominasTabProps {
    payrolls: Payroll[];
}

export function NominasTab({ payrolls }: NominasTabProps) {
    return (
        <div className="space-y-3">
            <p className="text-xs text-muted-foreground">
                Histórico de nóminas emitidas a tu nombre. Pulsa el icono de descarga para guardar el PDF.
            </p>
            {payrolls.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-40 gap-2 text-muted-foreground">
                    <FileText className="w-8 h-8 opacity-30" />
                    <p className="text-sm">Aún no tienes nóminas generadas</p>
                    <p className="text-xs max-w-xs text-center">
                        Tu nómina aparecerá aquí cuando RRHH la emita y apruebe el cálculo del mes.
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
                                <p className="text-xs text-muted-foreground">Emitida: {fmt(p.issue_date)}</p>
                            </div>
                        </div>
                        <div className="flex items-center gap-4">
                            <div className="text-right">
                                <p className="text-sm font-semibold text-foreground">{currency(p.net_salary)}</p>
                                <p className="text-xs text-muted-foreground">neto</p>
                            </div>
                            <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${STATUS_BADGE[p.status] ?? ""}`}>
                                {PAYROLL_LABEL[p.status] ?? p.status}
                            </span>
                            <button
                                onClick={() => api.hr.payrolls.downloadPdf(p.id, `nomina-${p.period_start.slice(0, 7)}.pdf`)}
                                className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
                                title="Descargar PDF"
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
