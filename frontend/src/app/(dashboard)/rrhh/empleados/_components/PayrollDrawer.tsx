"use client";

import Link from "next/link";
import { format } from "date-fns";
import { es } from "date-fns/locale";
import { WalletCards, Loader2, X, Download } from "lucide-react";
import { api, Employee, Payroll } from "@/lib/api";
import { currencyFmt } from "../_hooks/useEmpleados";

// ── Props ────────────────────────────────────────────────────────────────────

export interface PayrollDrawerProps {
    selectedEmp: Employee;
    onClose: () => void;
    empPayrolls: Payroll[];
    loadingPayrolls: boolean;
}

// ── Component ────────────────────────────────────────────────────────────────

export function PayrollDrawer({
    selectedEmp, onClose, empPayrolls, loadingPayrolls,
}: PayrollDrawerProps) {
    return (
        <div
            className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
            role="dialog"
            aria-modal="true"
            onClick={(e) => e.target === e.currentTarget && onClose()}
        >
            <div className="w-full max-w-lg rounded-2xl border border-border bg-card shadow-2xl overflow-hidden">
                <div className="flex items-center justify-between px-5 py-4 border-b border-border">
                    <div>
                        <h2 className="text-lg font-medium text-foreground flex items-center gap-2">
                            <WalletCards className="w-5 h-5 text-emerald-400" />
                            Nóminas de {selectedEmp.name}
                        </h2>
                        {selectedEmp.department && (
                            <p className="text-xs text-muted-foreground mt-0.5">{selectedEmp.department} · {selectedEmp.role || "Staff"}</p>
                        )}
                    </div>
                    <button
                        type="button"
                        onClick={onClose}
                        className="p-2 rounded-lg text-muted-foreground hover:bg-muted"
                        aria-label="Cerrar"
                    >
                        <X className="w-4 h-4" />
                    </button>
                </div>
                <div className="p-5 space-y-3 max-h-[60vh] overflow-y-auto">
                    {loadingPayrolls ? (
                        <div className="flex justify-center py-8">
                            <Loader2 className="w-6 h-6 animate-spin text-emerald-500" />
                        </div>
                    ) : empPayrolls.length === 0 ? (
                        <div className="text-center py-8">
                            <WalletCards className="w-8 h-8 text-muted-foreground mx-auto mb-2" />
                            <p className="text-sm text-muted-foreground">Este empleado no tiene nóminas generadas.</p>
                            <Link href="/rrhh/nominas" className="text-xs text-primary hover:underline mt-2 inline-block">
                                Ir a Nóminas para generar
                            </Link>
                        </div>
                    ) : (
                        empPayrolls.map((p) => (
                            <div key={p.id} className="flex items-center justify-between gap-3 bg-muted/50 border border-border rounded-xl px-4 py-3">
                                <div className="flex-1 min-w-0">
                                    <div className="text-sm font-medium text-foreground">
                                        {format(new Date(p.period_start), "d MMM", { locale: es })} – {format(new Date(p.period_end), "d MMM yyyy", { locale: es })}
                                    </div>
                                    <div className="flex items-center gap-3 text-xs text-muted-foreground mt-0.5">
                                        <span>Bruto: {currencyFmt.format(p.gross_salary ?? p.base_salary)}</span>
                                        <span className="text-emerald-400 font-medium">Neto: {currencyFmt.format(p.net_salary)}</span>
                                    </div>
                                </div>
                                <div className="flex items-center gap-2">
                                    <span className={`text-[10px] px-2 py-0.5 rounded-full border ${
                                        p.status === "paid" ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                                        : p.status === "draft" ? "bg-amber-500/10 text-amber-500 border-amber-500/20"
                                        : "bg-blue-500/10 text-blue-400 border-blue-500/20"
                                    }`}>
                                        {p.status === "paid" ? "Pagada" : p.status === "draft" ? "Borrador" : "Emitida"}
                                    </span>
                                    <button
                                        onClick={() => api.hr.payrolls.downloadPdf(p.id, `Nomina_${selectedEmp.name.replace(/\s+/g, "_")}_${format(new Date(p.period_start), "yyyy-MM")}.pdf`)}
                                        className="p-1.5 text-muted-foreground hover:text-primary bg-background hover:bg-primary/10 rounded-lg transition-colors"
                                        title="Descargar PDF"
                                     aria-label="Descargar PDF">
                                        <Download className="w-3.5 h-3.5" aria-hidden="true" />
                                    </button>
                                </div>
                            </div>
                        ))
                    )}
                </div>
                <div className="flex justify-between items-center px-5 py-3 border-t border-border bg-background">
                    <Link href="/rrhh/nominas" className="text-xs text-primary hover:underline">
                        Ver todas las nóminas →
                    </Link>
                    <button
                        type="button"
                        onClick={onClose}
                        className="px-4 py-2 text-sm rounded-lg text-muted-foreground hover:bg-muted"
                    >
                        Cerrar
                    </button>
                </div>
            </div>
        </div>
    );
}
