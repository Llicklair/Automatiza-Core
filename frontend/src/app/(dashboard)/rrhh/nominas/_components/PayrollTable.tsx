import { format } from "date-fns";
import { es } from "date-fns/locale";
import { WalletCards, Download, CheckCircle2, Loader2 } from "lucide-react";
import type { Payroll } from "@/lib/api";
import { PayrollStatusBadge } from "./PayrollStatusBadge";

interface PayrollTableProps {
    filtered: Payroll[];
    isLoading: boolean;
    fmt: (n: number) => string;
    downloadingId: string | null;
    approvingId: string | null;
    handleDownloadPdf: (p: Payroll) => void;
    handleApprove: (p: Payroll) => Promise<void>;
}

export function PayrollTable({
    filtered, isLoading, fmt, downloadingId, approvingId,
    handleDownloadPdf, handleApprove,
}: PayrollTableProps) {
    return (
            <div className="overflow-x-auto">
                <table className="w-full text-left text-sm whitespace-nowrap min-w-[900px]">
                    <thead className="bg-muted/50 text-muted-foreground border-b border-border">
                        <tr>
                            <th className="px-6 py-4 font-medium">Empleado</th>
                            <th className="px-6 py-4 font-medium">Período</th>
                            <th className="px-6 py-4 font-medium text-right">Bruto</th>
                            <th className="px-6 py-4 font-medium text-right">Deducciones</th>
                            <th className="px-6 py-4 font-medium text-right border-l border-border">Neto</th>
                            <th className="px-6 py-4 font-medium text-center">Estado</th>
                            <th className="px-6 py-4 font-medium text-right">Acciones</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-800/50">
                        {isLoading ? (
                            <tr><td colSpan={7} className="px-6 py-12 text-center">
                                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-emerald-500 mx-auto" />
                            </td></tr>
                        ) : filtered.length === 0 ? (
                            <tr><td colSpan={7} className="px-6 py-16 text-center">
                                <WalletCards className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
                                <p className="text-muted-foreground font-medium">No hay nóminas aún</p>
                                <p className="text-muted-foreground text-xs mt-2">
                                    Usa &quot;Calcular automática&quot; (preview + reglas fijas) o &quot;Generar con IA&quot; para el agente RRHH.
                                </p>
                            </td></tr>
                        ) : filtered.map((payroll) => (
                            <tr key={payroll.id} className="hover:bg-emerald-500/[0.02] transition-colors group">
                                <td className="px-6 py-4">
                                    <div className="font-medium text-foreground">{payroll.employee?.name ?? "—"}</div>
                                    <div className="text-[10px] font-mono text-muted-foreground uppercase">PAY-{payroll.id.slice(0, 8)}</div>
                                </td>
                                <td className="px-6 py-4 text-foreground">
                                    <span className="bg-muted text-xs px-2 py-1 rounded">
                                        {format(new Date(payroll.period_start), "d MMM", { locale: es })} – {format(new Date(payroll.period_end), "d MMM yyyy", { locale: es })}
                                    </span>
                                </td>
                                <td className="px-6 py-4 text-right text-muted-foreground">{fmt(payroll.base_salary)}</td>
                                <td className="px-6 py-4 text-right text-red-400/80 text-xs">−{fmt(payroll.deductions)}</td>
                                <td className="px-6 py-4 text-right font-semibold text-emerald-400 border-l border-border bg-muted/20 text-base">{fmt(payroll.net_salary)}</td>
                                <td className="px-6 py-4"><div className="flex justify-center"><PayrollStatusBadge status={payroll.status} /></div></td>
                                <td className="px-6 py-4 text-right">
                                    <div className="flex items-center justify-end gap-1.5">
                                        <button onClick={() => handleDownloadPdf(payroll)} disabled={downloadingId === payroll.id}
                                            className="p-1.5 text-muted-foreground hover:text-primary bg-muted hover:bg-primary/10 rounded-lg transition-colors disabled:opacity-50" title="Descargar PDF">
                                            {downloadingId === payroll.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                                        </button>
                                        {payroll.status === "draft" && (
                                            <button onClick={() => handleApprove(payroll)} disabled={approvingId === payroll.id}
                                                className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-emerald-400 hover:text-emerald-300 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/20 rounded-lg transition-colors disabled:opacity-50">
                                                {approvingId === payroll.id ? <Loader2 className="w-3 h-3 animate-spin" /> : <CheckCircle2 className="w-3 h-3" />}
                                                Aprobar
                                            </button>
                                        )}
                                    </div>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
    );
}
