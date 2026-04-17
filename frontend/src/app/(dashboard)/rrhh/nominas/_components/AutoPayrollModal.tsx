"use client";

import { Calculator, CheckCircle2, Loader2, X } from "lucide-react";
import { format, endOfMonth, startOfMonth } from "date-fns";
import { es } from "date-fns/locale";
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
                        Nómina automática (mes actual)
                    </h2>
                    <button type="button" disabled={autoSubmitting} onClick={onClose}
                        className="p-2 rounded-lg text-muted-foreground hover:bg-muted disabled:opacity-50" aria-label="Cerrar">
                        <X className="w-4 h-4" />
                    </button>
                </div>

                <div className="p-5 space-y-4 max-h-[70vh] overflow-y-auto">
                    {autoEmpLoading ? (
                        <div className="flex justify-center py-8">
                            <Loader2 className="w-8 h-8 animate-spin text-emerald-500" />
                        </div>
                    ) : autoEmployees.length === 0 ? (
                        <p className="text-sm text-muted-foreground text-center py-4">No hay empleados. Crea uno en RRHH primero.</p>
                    ) : (
                        <>
                            <label className="block text-xs text-muted-foreground uppercase tracking-wide">Empleado</label>
                            <select value={autoEmpId} onChange={(e) => setAutoEmpId(e.target.value)}
                                className="w-full bg-background border border-border rounded-lg px-3 py-2.5 text-sm text-foreground focus:outline-none focus:border-emerald-500">
                                {autoEmployees.map((e) => (
                                    <option key={e.id} value={e.id}>
                                        {e.name}{e.base_salary != null ? ` — ${fmt(e.base_salary)}/mes` : " — sin salario base"}
                                    </option>
                                ))}
                            </select>
                            <p className="text-xs text-muted-foreground">
                                Período:{" "}
                                <span className="text-foreground">
                                    {format(startOfMonth(new Date()), "d MMM", { locale: es })} –{" "}
                                    {format(endOfMonth(new Date()), "d MMM yyyy", { locale: es })}
                                </span>
                            </p>
                            <div className="rounded-xl border border-border bg-background p-4">
                                <p className="text-xs font-medium text-muted-foreground mb-3">Previsualización del cálculo</p>
                                {autoPreviewLoading ? (
                                    <div className="flex justify-center py-6">
                                        <Loader2 className="w-6 h-6 animate-spin text-emerald-500" />
                                    </div>
                                ) : autoPreview ? (
                                    <dl className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-sm">
                                        <dt className="text-muted-foreground">Bruto</dt>
                                        <dd className="text-right text-foreground">{fmt(autoPreview.base_salary)}</dd>
                                        <dt className="text-muted-foreground text-[11px] col-span-2 pt-1 border-t border-border">
                                            Cotizaciones SS (empleado, régimen general)
                                        </dt>
                                        <dt className="text-muted-foreground pl-2 text-xs">Contingencias comunes</dt>
                                        <dd className="text-right text-red-400/80 text-xs">−{fmt(autoPreview.ss_contingencias_comunes)}</dd>
                                        <dt className="text-muted-foreground pl-2 text-xs">Desempleo</dt>
                                        <dd className="text-right text-red-400/80 text-xs">−{fmt(autoPreview.ss_desempleo)}</dd>
                                        <dt className="text-muted-foreground pl-2 text-xs">Formación profesional</dt>
                                        <dd className="text-right text-red-400/80 text-xs">−{fmt(autoPreview.ss_formacion_profesional)}</dd>
                                        <dt className="text-muted-foreground pl-2 text-xs">MEI</dt>
                                        <dd className="text-right text-red-400/80 text-xs">−{fmt(autoPreview.ss_mei)}</dd>
                                        <dt className="text-muted-foreground">SS total</dt>
                                        <dd className="text-right text-red-400/90">−{fmt(autoPreview.total_ss)}</dd>
                                        <dt className="text-muted-foreground">IRPF ({autoPreview.irpf_rate_applied}%)</dt>
                                        <dd className="text-right text-red-400/90">−{fmt(autoPreview.irpf)}</dd>
                                        <dt className="text-muted-foreground">Deducciones totales</dt>
                                        <dd className="text-right text-muted-foreground">−{fmt(autoPreview.deductions)}</dd>
                                        <dt className="text-muted-foreground font-medium pt-1 border-t border-border">Neto estimado</dt>
                                        <dd className="text-right font-semibold text-emerald-400 pt-1 border-t border-border">{fmt(autoPreview.net_salary)}</dd>
                                    </dl>
                                ) : (
                                    <p className="text-xs text-muted-foreground py-2">Selecciona un empleado con salario base.</p>
                                )}
                            </div>
                        </>
                    )}
                </div>

                <div className="flex justify-end gap-2 px-5 py-4 border-t border-border bg-background">
                    <button type="button" disabled={autoSubmitting} onClick={onClose}
                        className="px-4 py-2 text-sm rounded-lg text-muted-foreground hover:bg-muted disabled:opacity-50">
                        Cancelar
                    </button>
                    <button type="button"
                        disabled={autoSubmitting || !autoEmpId || autoPreviewLoading || !autoPreview || autoEmployees.length === 0}
                        onClick={onSubmit}
                        className="flex items-center gap-2 px-4 py-2 text-sm rounded-lg font-medium bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-foreground">
                        {autoSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
                        Crear borrador
                    </button>
                </div>
            </div>
        </div>
    );
}
