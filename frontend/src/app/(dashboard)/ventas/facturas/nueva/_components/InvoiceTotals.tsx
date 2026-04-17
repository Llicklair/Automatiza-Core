import Link from "next/link";
import { Loader2, FileText } from "lucide-react";
import { useTranslations } from "next-intl";

interface InvoiceTotalsProps {
    totals: { base: number; tax: number; total: number };
    submitting: boolean;
}

export default function InvoiceTotals({ totals, submitting }: InvoiceTotalsProps) {
    const t = useTranslations("ventas");
    const tc = useTranslations("common");

    return (
        <div className="flex flex-col sm:flex-row items-start sm:items-end justify-between gap-6">
            <div className="bg-card border border-border rounded-2xl p-5 w-full sm:w-72 space-y-2 text-sm">
                <div className="flex justify-between text-muted-foreground">
                    <span>{t("subtotal")}</span>
                    <span className="tabular-nums">{totals.base.toLocaleString("es-ES", { minimumFractionDigits: 2 })}&euro;</span>
                </div>
                <div className="flex justify-between text-muted-foreground">
                    <span>{t("totalVat")}</span>
                    <span className="tabular-nums">{totals.tax.toLocaleString("es-ES", { minimumFractionDigits: 2 })}&euro;</span>
                </div>
                <div className="flex justify-between text-foreground font-bold border-t border-border pt-2">
                    <span>{t("total")}</span>
                    <span className="tabular-nums">{totals.total.toLocaleString("es-ES", { minimumFractionDigits: 2 })}&euro;</span>
                </div>
            </div>
            <div className="flex gap-3">
                <Link
                    href="/ventas/facturas"
                    className="inline-flex items-center gap-2 bg-muted hover:bg-accent text-foreground px-5 py-2.5 rounded-xl transition font-medium text-sm"
                >
                    {tc("cancel")}
                </Link>
                <button
                    type="submit"
                    disabled={submitting}
                    className="inline-flex items-center gap-2 bg-primary hover:bg-primary disabled:opacity-50 text-foreground px-6 py-2.5 rounded-xl transition font-medium text-sm shadow-lg shadow-primary/20"
                >
                    {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileText className="w-4 h-4" />}
                    {t("createInvoice")}
                </button>
            </div>
        </div>
    );
}
