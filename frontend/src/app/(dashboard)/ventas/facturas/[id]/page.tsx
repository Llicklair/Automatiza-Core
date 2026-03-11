"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, Invoice } from "@/lib/api";
import { ArrowLeft, Download, FileText, Loader2, Trash2, CheckCircle2, Clock, XCircle, Send } from "lucide-react";
import { useToastStore } from "@/stores/toast";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8080";

function getToken(): string {
    return typeof window !== "undefined" ? (localStorage.getItem("access_token") ?? "") : "";
}

async function downloadInvoicePdf(invoiceId: string, invoiceNumber: string | null) {
    const res = await fetch(`${API_BASE}/api/v1/invoices/${invoiceId}/pdf`, {
        headers: { Authorization: `Bearer ${getToken()}` },
    });
    if (!res.ok) throw new Error("Error al descargar el PDF");
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `Factura_${invoiceNumber || invoiceId.slice(0, 8)}.pdf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

const STATUS_TRANSITIONS: Record<string, { label: string; next: string; icon: React.ReactNode; color: string }[]> = {
    draft:     [{ label: "Enviar (Pendiente)", next: "pending",   icon: <Send className="w-3.5 h-3.5" />,        color: "bg-blue-600 hover:bg-blue-500" }],
    pending:   [{ label: "Marcar Pagada",      next: "paid",      icon: <CheckCircle2 className="w-3.5 h-3.5" />, color: "bg-emerald-600 hover:bg-emerald-500" },
                { label: "Cancelar",            next: "cancelled", icon: <XCircle className="w-3.5 h-3.5" />,     color: "bg-red-700 hover:bg-red-600" }],
    paid:      [{ label: "Reabrir (Pendiente)",next: "pending",   icon: <Clock className="w-3.5 h-3.5" />,       color: "bg-zinc-600 hover:bg-zinc-500" }],
    cancelled: [{ label: "Reabrir (Borrador)", next: "draft",     icon: <Clock className="w-3.5 h-3.5" />,       color: "bg-zinc-600 hover:bg-zinc-500" }],
};

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
    draft:     { label: "Borrador",  color: "bg-zinc-700 text-zinc-300" },
    pending:   { label: "Pendiente", color: "bg-amber-500/20 text-amber-300 border border-amber-500/30" },
    paid:      { label: "Pagada",    color: "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30" },
    cancelled: { label: "Cancelada", color: "bg-red-500/20 text-red-300 border border-red-500/30" },
};

export default function FacturaDetallePage() {
    const toast = useToastStore();
    const params = useParams<{ id: string }>();
    const router = useRouter();
    const invoiceId = params?.id;

    const [invoice, setInvoice] = useState<Invoice | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [downloading, setDownloading] = useState(false);
    const [statusLoading, setStatusLoading] = useState(false);
    const [deleting, setDeleting] = useState(false);

    useEffect(() => {
        if (!invoiceId) return;
        setLoading(true);
        setError(null);
        api.erp.invoices.get(invoiceId)
            .then(setInvoice)
            .catch((e: any) => setError(e?.message || "Error cargando factura"))
            .finally(() => setLoading(false));
    }, [invoiceId]);

    const handleStatusChange = async (nextStatus: string) => {
        if (!invoice) return;
        setStatusLoading(true);
        try {
            const updated = await api.erp.invoices.updateStatus(invoice.id, nextStatus);
            setInvoice(updated);
        } catch (e: any) {
            toast.error(e?.message || "Error cambiando estado");
        } finally {
            setStatusLoading(false);
        }
    };

    const handleDelete = async () => {
        if (!invoice || !confirm("¿Eliminar esta factura? Esta acción no se puede deshacer.")) return;
        setDeleting(true);
        try {
            await api.erp.invoices.delete(invoice.id);
            router.push("/ventas/facturas");
        } catch (e: any) {
            toast.error(e?.message || "Error eliminando factura");
            setDeleting(false);
        }
    };

    const totals = useMemo(() => {
        const base = Number(invoice?.amount_base ?? 0);
        const tax = Number(invoice?.tax_amount ?? 0);
        const total = Number(invoice?.amount_total ?? 0);
        return { base, tax, total };
    }, [invoice]);

    return (
        <div className="p-8 max-w-5xl mx-auto space-y-6">
            <div className="flex items-start justify-between gap-4">
                <div className="space-y-2 min-w-0">
                    <Link
                        href="/ventas/facturas"
                        className="inline-flex items-center gap-2 text-sm text-zinc-400 hover:text-white transition"
                    >
                        <ArrowLeft className="w-4 h-4" />
                        Volver a facturas
                    </Link>
                    <div className="flex items-center gap-3 min-w-0">
                        <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center flex-shrink-0">
                            <FileText className="w-5 h-5 text-indigo-400" />
                        </div>
                        <div className="min-w-0">
                            <h1 className="text-2xl font-bold text-white truncate">
                                {invoice?.invoice_number ? `Factura ${invoice.invoice_number}` : "Detalle de factura"}
                            </h1>
                            <p className="text-sm text-zinc-400">
                                {invoice?.client?.name ? invoice.client.name : "—"}
                            </p>
                        </div>
                    </div>
                </div>

                <div className="flex items-center gap-2 flex-wrap justify-end">
                    {invoice && (STATUS_TRANSITIONS[invoice.status] ?? []).map((t) => (
                        <button
                            key={t.next}
                            disabled={statusLoading}
                            onClick={() => handleStatusChange(t.next)}
                            className={`inline-flex items-center gap-1.5 text-white px-3 py-2 rounded-xl transition text-sm font-medium disabled:opacity-50 ${t.color}`}
                        >
                            {statusLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : t.icon}
                            {t.label}
                        </button>
                    ))}
                    <button
                        disabled={!invoice || downloading}
                        onClick={async () => {
                            if (!invoice) return;
                            try {
                                setDownloading(true);
                                await downloadInvoicePdf(invoice.id, invoice.invoice_number);
                            } catch (e: any) {
                                toast.error(e?.message || "No se pudo descargar el PDF");
                            } finally {
                                setDownloading(false);
                            }
                        }}
                        className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white px-4 py-2.5 rounded-xl transition shadow-lg shadow-indigo-500/20 font-medium"
                    >
                        {downloading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                        PDF
                    </button>
                    <button
                        disabled={!invoice || deleting}
                        onClick={handleDelete}
                        className="inline-flex items-center gap-2 bg-zinc-800 hover:bg-red-700 disabled:opacity-50 text-zinc-300 hover:text-white px-3 py-2.5 rounded-xl transition font-medium"
                    >
                        {deleting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                    </button>
                </div>
            </div>

            {loading ? (
                <div className="bg-zinc-900/50 border border-white/5 rounded-2xl p-8 flex items-center justify-center text-zinc-400 gap-2">
                    <Loader2 className="w-4 h-4 animate-spin" /> Cargando detalle…
                </div>
            ) : error ? (
                <div className="bg-red-500/10 border border-red-500/20 rounded-2xl p-6 text-red-300">
                    {error}
                </div>
            ) : !invoice ? (
                <div className="bg-zinc-900/50 border border-white/5 rounded-2xl p-6 text-zinc-400">
                    Factura no disponible.
                </div>
            ) : (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    <div className="lg:col-span-2 space-y-6">
                        <div className="bg-zinc-900/50 border border-white/5 rounded-2xl p-6">
                            <h2 className="text-sm font-semibold text-zinc-300 mb-4">Líneas</h2>
                            <div className="overflow-x-auto">
                                <table className="w-full text-left border-collapse">
                                    <thead>
                                        <tr className="border-b border-white/5 text-xs text-zinc-500">
                                            <th className="pb-3 font-medium">Descripción</th>
                                            <th className="pb-3 font-medium text-right">Cant.</th>
                                            <th className="pb-3 font-medium text-right">P. unit.</th>
                                            <th className="pb-3 font-medium text-right">IVA</th>
                                            <th className="pb-3 font-medium text-right">Total</th>
                                        </tr>
                                    </thead>
                                    <tbody className="text-sm">
                                        {(invoice.lines ?? []).length === 0 ? (
                                            <tr>
                                                <td colSpan={5} className="py-6 text-center text-zinc-500">
                                                    Sin líneas
                                                </td>
                                            </tr>
                                        ) : (
                                            (invoice.lines ?? []).map((l, idx) => (
                                                <tr key={(l as any).id ?? idx} className="border-b border-white/5">
                                                    <td className="py-3 text-zinc-200">{l.description}</td>
                                                    <td className="py-3 text-right text-zinc-300 tabular-nums">{Number(l.quantity).toLocaleString("es-ES")}</td>
                                                    <td className="py-3 text-right text-zinc-300 tabular-nums">{Number(l.unit_price).toLocaleString("es-ES", { minimumFractionDigits: 2 })}€</td>
                                                    <td className="py-3 text-right text-zinc-300 tabular-nums">{Number(l.tax_percentage).toLocaleString("es-ES", { maximumFractionDigits: 0 })}%</td>
                                                    <td className="py-3 text-right text-white font-medium tabular-nums">{Number((l as any).total ?? 0).toLocaleString("es-ES", { minimumFractionDigits: 2 })}€</td>
                                                </tr>
                                            ))
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </div>

                        {(invoice.notes || invoice.terms) && (
                            <div className="bg-zinc-900/50 border border-white/5 rounded-2xl p-6 space-y-4">
                                {invoice.notes && (
                                    <div>
                                        <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-wide mb-2">Notas</h3>
                                        <p className="text-sm text-zinc-300 whitespace-pre-wrap">{invoice.notes}</p>
                                    </div>
                                )}
                                {invoice.terms && (
                                    <div>
                                        <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-wide mb-2">Términos</h3>
                                        <p className="text-sm text-zinc-300 whitespace-pre-wrap">{invoice.terms}</p>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>

                    <div className="space-y-6">
                        <div className="bg-zinc-900/50 border border-white/5 rounded-2xl p-6">
                            <h2 className="text-sm font-semibold text-zinc-300 mb-4">Resumen</h2>
                            <dl className="space-y-3 text-sm">
                                <div className="flex items-center justify-between gap-3">
                                    <dt className="text-zinc-500">Fecha</dt>
                                    <dd className="text-zinc-200">
                                        {invoice.date ? new Date(invoice.date).toLocaleDateString("es-ES") : "—"}
                                    </dd>
                                </div>
                                <div className="flex items-center justify-between gap-3">
                                    <dt className="text-zinc-500">Vencimiento</dt>
                                    <dd className="text-zinc-200">
                                        {invoice.due_date ? new Date(invoice.due_date).toLocaleDateString("es-ES") : "—"}
                                    </dd>
                                </div>
                                <div className="flex items-center justify-between gap-3">
                                    <dt className="text-zinc-500">Estado</dt>
                                    <dd>
                                        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${(STATUS_LABELS[invoice.status] ?? { color: "bg-zinc-700 text-zinc-300" }).color}`}>
                                            {(STATUS_LABELS[invoice.status] ?? { label: invoice.status }).label}
                                        </span>
                                    </dd>
                                </div>
                                <div className="pt-3 border-t border-white/5 space-y-3">
                                    <div className="flex items-center justify-between gap-3">
                                        <dt className="text-zinc-500">Base</dt>
                                        <dd className="text-zinc-200 tabular-nums">
                                            {totals.base.toLocaleString("es-ES", { minimumFractionDigits: 2 })}€
                                        </dd>
                                    </div>
                                    <div className="flex items-center justify-between gap-3">
                                        <dt className="text-zinc-500">IVA</dt>
                                        <dd className="text-zinc-200 tabular-nums">
                                            {totals.tax.toLocaleString("es-ES", { minimumFractionDigits: 2 })}€
                                        </dd>
                                    </div>
                                    <div className="flex items-center justify-between gap-3">
                                        <dt className="text-zinc-400 font-semibold">Total</dt>
                                        <dd className="text-white font-bold tabular-nums">
                                            {totals.total.toLocaleString("es-ES", { minimumFractionDigits: 2 })}€
                                        </dd>
                                    </div>
                                </div>
                            </dl>
                        </div>

                        <div className="bg-zinc-900/50 border border-white/5 rounded-2xl p-6">
                            <h2 className="text-sm font-semibold text-zinc-300 mb-4">Cliente</h2>
                            <div className="space-y-1 text-sm">
                                <p className="text-zinc-200 font-medium">{invoice.client?.name || "—"}</p>
                                {invoice.client?.nif && <p className="text-zinc-500">NIF/CIF: {invoice.client.nif}</p>}
                                {invoice.client?.email && <p className="text-zinc-500">{invoice.client.email}</p>}
                                {invoice.client?.address && <p className="text-zinc-500 whitespace-pre-wrap">{invoice.client.address}</p>}
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

