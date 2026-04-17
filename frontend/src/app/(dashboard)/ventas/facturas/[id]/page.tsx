"use client";

import Link from "next/link";
import { ArrowLeft, Download, FileText, Loader2, Trash2, CheckCircle2, Clock, XCircle, Send } from "lucide-react";
import { useFacturaDetalle } from "./_hooks/useFacturaDetalle";

const STATUS_ICONS: Record<string, React.ReactNode> = {
    pending:   <Send className="w-3.5 h-3.5" />,
    paid:      <CheckCircle2 className="w-3.5 h-3.5" />,
    cancelled: <XCircle className="w-3.5 h-3.5" />,
    draft:     <Clock className="w-3.5 h-3.5" />,
};

export default function FacturaDetallePage() {
    const {
        t, tc,
        invoice, loading, error,
        downloading, statusLoading, deleting,
        totals,
        STATUS_TRANSITIONS,
        STATUS_LABELS,
        handleStatusChange,
        handleDelete,
        handleDownload,
    } = useFacturaDetalle();

    return (
        <div className="p-8 max-w-5xl mx-auto space-y-6">
            <div className="flex items-start justify-between gap-4">
                <div className="space-y-2 min-w-0">
                    <Link
                        href="/ventas/facturas"
                        className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition"
                    >
                        <ArrowLeft className="w-4 h-4" />
                        {tc("back")}
                    </Link>
                    <div className="flex items-center gap-3 min-w-0">
                        <div className="w-10 h-10 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center flex-shrink-0">
                            <FileText className="w-5 h-5 text-primary" />
                        </div>
                        <div className="min-w-0">
                            <h1 className="text-2xl font-bold text-foreground truncate">
                                {invoice?.invoice_number ? `Factura ${invoice.invoice_number}` : "Detalle de factura"}
                            </h1>
                            <p className="text-sm text-muted-foreground">
                                {invoice?.client?.name ? invoice.client.name : "—"}
                            </p>
                        </div>
                    </div>
                </div>

                <div className="flex items-center gap-2 flex-wrap justify-end">
                    {invoice && (STATUS_TRANSITIONS[invoice.status] ?? []).map((tr) => (
                        <button
                            key={tr.next}
                            disabled={statusLoading}
                            onClick={() => handleStatusChange(tr.next)}
                            className={`inline-flex items-center gap-1.5 text-foreground px-3 py-2 rounded-xl transition text-sm font-medium disabled:opacity-50 ${tr.color}`}
                        >
                            {statusLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : (STATUS_ICONS[tr.next] ?? <Clock className="w-3.5 h-3.5" />)}
                            {tr.label}
                        </button>
                    ))}
                    <button
                        disabled={!invoice || downloading}
                        onClick={handleDownload}
                        className="inline-flex items-center gap-2 bg-primary hover:bg-primary disabled:opacity-50 text-foreground px-4 py-2.5 rounded-xl transition shadow-lg shadow-primary/20 font-medium"
                    >
                        {downloading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                        PDF
                    </button>
                    <button
                        disabled={!invoice || deleting}
                        onClick={handleDelete}
                        className="inline-flex items-center gap-2 bg-muted hover:bg-red-700 disabled:opacity-50 text-foreground hover:text-foreground px-3 py-2.5 rounded-xl transition font-medium"
                    >
                        {deleting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                    </button>
                </div>
            </div>

            {loading ? (
                <div className="bg-card border border-border rounded-2xl p-8 flex items-center justify-center text-muted-foreground gap-2">
                    <Loader2 className="w-4 h-4 animate-spin" /> {t("loading")}
                </div>
            ) : error ? (
                <div className="bg-red-500/10 border border-red-500/20 rounded-2xl p-6 text-red-300">
                    {error}
                </div>
            ) : !invoice ? (
                <div className="bg-card border border-border rounded-2xl p-6 text-muted-foreground">
                    {t("invoiceNotAvailable")}
                </div>
            ) : (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    <div className="lg:col-span-2 space-y-6">
                        <div className="bg-card border border-border rounded-2xl p-6">
                            <h2 className="text-sm font-semibold text-foreground mb-4">{t("invoiceLines")}</h2>
                            <div className="overflow-x-auto">
                                <table className="w-full text-left border-collapse">
                                    <thead>
                                        <tr className="border-b border-border text-xs text-muted-foreground">
                                            <th className="pb-3 font-medium">{t("descriptionLabel")}</th>
                                            <th className="pb-3 font-medium text-right">{t("qty")}</th>
                                            <th className="pb-3 font-medium text-right">{t("unitPrice")}</th>
                                            <th className="pb-3 font-medium text-right">{t("vat")}</th>
                                            <th className="pb-3 font-medium text-right">{t("total")}</th>
                                        </tr>
                                    </thead>
                                    <tbody className="text-sm">
                                        {(invoice.lines ?? []).length === 0 ? (
                                            <tr>
                                                <td colSpan={5} className="py-6 text-center text-muted-foreground">
                                                    {t("noLines")}
                                                </td>
                                            </tr>
                                        ) : (
                                            (invoice.lines ?? []).map((l, idx) => (
                                                <tr key={(l as any).id ?? idx} className="border-b border-border">
                                                    <td className="py-3 text-foreground">{l.description}</td>
                                                    <td className="py-3 text-right text-foreground tabular-nums">{Number(l.quantity).toLocaleString("es-ES")}</td>
                                                    <td className="py-3 text-right text-foreground tabular-nums">{Number(l.unit_price).toLocaleString("es-ES", { minimumFractionDigits: 2 })}€</td>
                                                    <td className="py-3 text-right text-foreground tabular-nums">{Number(l.tax_percentage).toLocaleString("es-ES", { maximumFractionDigits: 0 })}%</td>
                                                    <td className="py-3 text-right text-foreground font-medium tabular-nums">{Number((l as any).total ?? 0).toLocaleString("es-ES", { minimumFractionDigits: 2 })}€</td>
                                                </tr>
                                            ))
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </div>

                        {(invoice.notes || invoice.terms) && (
                            <div className="bg-card border border-border rounded-2xl p-6 space-y-4">
                                {invoice.notes && (
                                    <div>
                                        <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">{t("internalNotes")}</h3>
                                        <p className="text-sm text-foreground whitespace-pre-wrap">{invoice.notes}</p>
                                    </div>
                                )}
                                {invoice.terms && (
                                    <div>
                                        <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">{t("paymentTerms")}</h3>
                                        <p className="text-sm text-foreground whitespace-pre-wrap">{invoice.terms}</p>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>

                    <div className="space-y-6">
                        <div className="bg-card border border-border rounded-2xl p-6">
                            <h2 className="text-sm font-semibold text-foreground mb-4">{t("summary")}</h2>
                            <dl className="space-y-3 text-sm">
                                <div className="flex items-center justify-between gap-3">
                                    <dt className="text-muted-foreground">{t("date")}</dt>
                                    <dd className="text-foreground">
                                        {invoice.date ? new Date(invoice.date).toLocaleDateString("es-ES") : "—"}
                                    </dd>
                                </div>
                                <div className="flex items-center justify-between gap-3">
                                    <dt className="text-muted-foreground">{t("dueDate")}</dt>
                                    <dd className="text-foreground">
                                        {invoice.due_date ? new Date(invoice.due_date).toLocaleDateString("es-ES") : "—"}
                                    </dd>
                                </div>
                                <div className="flex items-center justify-between gap-3">
                                    <dt className="text-muted-foreground">{t("status")}</dt>
                                    <dd>
                                        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${(STATUS_LABELS[invoice.status] ?? { color: "bg-accent text-foreground" }).color}`}>
                                            {(STATUS_LABELS[invoice.status] ?? { label: invoice.status }).label}
                                        </span>
                                    </dd>
                                </div>
                                <div className="pt-3 border-t border-border space-y-3">
                                    <div className="flex items-center justify-between gap-3">
                                        <dt className="text-muted-foreground">{t("subtotal")}</dt>
                                        <dd className="text-foreground tabular-nums">
                                            {totals.base.toLocaleString("es-ES", { minimumFractionDigits: 2 })}€
                                        </dd>
                                    </div>
                                    <div className="flex items-center justify-between gap-3">
                                        <dt className="text-muted-foreground">{t("totalVat")}</dt>
                                        <dd className="text-foreground tabular-nums">
                                            {totals.tax.toLocaleString("es-ES", { minimumFractionDigits: 2 })}€
                                        </dd>
                                    </div>
                                    <div className="flex items-center justify-between gap-3">
                                        <dt className="text-muted-foreground font-semibold">{t("total")}</dt>
                                        <dd className="text-foreground font-bold tabular-nums">
                                            {totals.total.toLocaleString("es-ES", { minimumFractionDigits: 2 })}€
                                        </dd>
                                    </div>
                                </div>
                            </dl>
                        </div>

                        <div className="bg-card border border-border rounded-2xl p-6">
                            <h2 className="text-sm font-semibold text-foreground mb-4">{t("client")}</h2>
                            <div className="space-y-1 text-sm">
                                <p className="text-foreground font-medium">{invoice.client?.name || "—"}</p>
                                {invoice.client?.nif && <p className="text-muted-foreground">NIF/CIF: {invoice.client.nif}</p>}
                                {invoice.client?.email && <p className="text-muted-foreground">{invoice.client.email}</p>}
                                {invoice.client?.address && <p className="text-muted-foreground whitespace-pre-wrap">{invoice.client.address}</p>}
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
