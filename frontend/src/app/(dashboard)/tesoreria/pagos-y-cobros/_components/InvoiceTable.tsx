import type { Invoice } from "@/lib/api";
import { CheckCircle2 } from "lucide-react";
import { format } from "date-fns";
import { es } from "date-fns/locale";
import DueBadge from "./DueBadge";

const fmt = (v: number) =>
    new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" }).format(v);

interface InvoiceTableProps {
    items: Invoice[];
    total: number;
    variant: "cobros" | "pagos";
}

export default function InvoiceTable({ items, total, variant }: InvoiceTableProps) {
    const isCobros = variant === "cobros";
    const emptyIcon = <CheckCircle2 className="w-10 h-10 text-emerald-600 mx-auto mb-3" />;
    const emptyTitle = isCobros ? "Sin cobros pendientes" : "Sin pagos pendientes";
    const emptyDesc = isCobros
        ? "Todas las facturas emitidas estan pagadas."
        : "Todas las facturas recibidas estan pagadas.";
    const entityLabel = isCobros ? "Cliente" : "Proveedor";
    const amountColor = isCobros ? "text-emerald-400" : "text-red-400";
    const hoverBg = isCobros ? "hover:bg-emerald-500/[0.02]" : "hover:bg-red-500/[0.02]";

    if (items.length === 0) {
        return (
            <div className="py-16 text-center">
                {emptyIcon}
                <p className="text-muted-foreground font-medium">{emptyTitle}</p>
                <p className="text-xs text-muted-foreground mt-1">{emptyDesc}</p>
            </div>
        );
    }

    return (
        <table className="w-full text-left text-sm">
            <thead className="bg-muted/50 text-muted-foreground border-b border-border">
                <tr>
                    <th className="px-6 py-3 font-medium">N Factura</th>
                    <th className="px-6 py-3 font-medium">{entityLabel}</th>
                    <th className="px-6 py-3 font-medium text-right">Importe</th>
                    <th className="px-6 py-3 font-medium">Vencimiento</th>
                    <th className="px-6 py-3 font-medium">Estado</th>
                </tr>
            </thead>
            <tbody className="divide-y divide-border">
                {items.map(inv => (
                    <tr key={inv.id} className={`${hoverBg} transition-colors`}>
                        <td className="px-6 py-4 font-mono text-xs text-muted-foreground">{inv.invoice_number || inv.id.slice(0, 8)}</td>
                        <td className="px-6 py-4 text-foreground font-medium">{inv.client?.name || "\u2014"}</td>
                        <td className={`px-6 py-4 text-right font-semibold ${amountColor}`}>{fmt(Number(inv.amount_total))}</td>
                        <td className="px-6 py-4">
                            {inv.due_date ? (
                                <span className="text-xs text-foreground">{format(new Date(inv.due_date), "d MMM yyyy", { locale: es })}</span>
                            ) : <span className="text-xs text-muted-foreground">\u2014</span>}
                        </td>
                        <td className="px-6 py-4"><DueBadge dueDate={inv.due_date} /></td>
                    </tr>
                ))}
            </tbody>
            <tfoot className="border-t border-border bg-muted/30">
                <tr>
                    <td colSpan={2} className="px-6 py-3 text-sm font-semibold text-foreground">Total</td>
                    <td className={`px-6 py-3 text-right font-bold ${amountColor}`}>{fmt(total)}</td>
                    <td colSpan={2} />
                </tr>
            </tfoot>
        </table>
    );
}
