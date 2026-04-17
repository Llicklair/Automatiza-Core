"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, Invoice } from "@/lib/api";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";
import { useTranslations } from "next-intl";

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

export function useFacturaDetalle() {
    const t = useTranslations("ventas");
    const tc = useTranslations("common");
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
            .catch((e: any) => setError(e?.message || t("errorLoadingInvoice")))
            .finally(() => setLoading(false));
    }, [invoiceId, t]);

    const handleStatusChange = async (nextStatus: string) => {
        if (!invoice) return;
        setStatusLoading(true);
        try {
            const updated = await api.erp.invoices.updateStatus(invoice.id, nextStatus);
            setInvoice(updated);
        } catch (e: any) {
            toast.error(e?.message || t("errorChangingStatus"));
        } finally {
            setStatusLoading(false);
        }
    };

    const handleDelete = async () => {
        if (!invoice) return;
        if (!await showConfirm({ message: t("deleteInvoice"), confirmLabel: tc("delete"), confirmVariant: "danger" })) return;
        setDeleting(true);
        try {
            await api.erp.invoices.delete(invoice.id);
            router.push("/ventas/facturas");
        } catch (e: any) {
            toast.error(e?.message || "Error eliminando factura");
            setDeleting(false);
        }
    };

    const handleDownload = async () => {
        if (!invoice) return;
        try {
            setDownloading(true);
            await downloadInvoicePdf(invoice.id, invoice.invoice_number);
        } catch (e: any) {
            toast.error(e?.message || t("errorDownloadPdf"));
        } finally {
            setDownloading(false);
        }
    };

    const totals = useMemo(() => {
        const base = Number(invoice?.amount_base ?? 0);
        const tax = Number(invoice?.tax_amount ?? 0);
        const total = Number(invoice?.amount_total ?? 0);
        return { base, tax, total };
    }, [invoice]);

    const STATUS_TRANSITIONS: Record<string, { label: string; next: string; color: string }[]> = {
        draft:     [{ label: t("sendPending"), next: "pending",   color: "bg-blue-600 hover:bg-blue-500" }],
        pending:   [{ label: t("markPaid"),    next: "paid",      color: "bg-emerald-600 hover:bg-emerald-500" },
                    { label: tc("cancel"),      next: "cancelled", color: "bg-red-700 hover:bg-red-600" }],
        paid:      [{ label: t("reopenPending"), next: "pending", color: "bg-accent hover:bg-muted-foreground" }],
        cancelled: [{ label: t("reopenDraft"),  next: "draft",    color: "bg-accent hover:bg-muted-foreground" }],
    };

    const STATUS_LABELS: Record<string, { label: string; color: string }> = {
        draft:     { label: t("draft"),      color: "bg-accent text-foreground" },
        pending:   { label: t("pending"),    color: "bg-amber-500/20 text-amber-300 border border-amber-500/30" },
        paid:      { label: t("paid"),       color: "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30" },
        cancelled: { label: t("cancelled"),  color: "bg-red-500/20 text-red-300 border border-red-500/30" },
    };

    return {
        t, tc,
        invoice, loading, error,
        downloading, statusLoading, deleting,
        totals,
        STATUS_TRANSITIONS,
        STATUS_LABELS,
        handleStatusChange,
        handleDelete,
        handleDownload,
    };
}
