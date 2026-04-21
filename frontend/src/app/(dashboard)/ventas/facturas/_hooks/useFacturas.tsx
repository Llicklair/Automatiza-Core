"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { api, Invoice } from "@/lib/api";
import { useToastStore } from "@/stores/toast";
import { useNotificationStore } from "@/stores/notifications";
import { showConfirm } from "@/stores/confirm";
import { useTranslations } from "next-intl";
import { ColumnDef } from "@tanstack/react-table";
import { DataTableColumnHeader } from "@/components/data-table";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { Button } from "@/components/ui/button";
import { Download, Copy, Trash2, FileText } from "lucide-react";
import Link from "next/link";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8080";

function getToken(): string {
    return typeof window !== "undefined" ? (localStorage.getItem("access_token") ?? "") : "";
}

export async function downloadInvoicePdf(invoiceId: string, invoiceNumber: string | null) {
    try {
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
    } catch {
        useToastStore.getState().error("Error al descargar el PDF");
    }
}

export function useFacturas() {
    const t = useTranslations("ventas");
    const tc = useTranslations("common");
    const router = useRouter();
    const [invoices, setInvoices] = useState<Invoice[]>([]);
    const [loading, setLoading] = useState(true);
    const [dateFrom, setDateFrom] = useState("");
    const [dateTo, setDateTo] = useState("");
    const refreshKey = useNotificationStore((s) => s.refreshKey);

    const statusFilterOptions = [
        { label: t("draft"), value: "draft" },
        { label: t("pending"), value: "pending" },
        { label: t("paid"), value: "paid" },
        { label: t("overdue"), value: "overdue" },
    ];

    useEffect(() => {
        setLoading(true);
        api.erp.invoices.list()
            .then(data => setInvoices(data))
            .catch(err => useToastStore.getState().error(err?.message || t("errorLoadingInvoices")))
            .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [refreshKey]);

    const kpis = useMemo(() => {
        const now = new Date();
        const month = now.getMonth();
        const year = now.getFullYear();
        const thisMonth = invoices.filter(inv => {
            if (!inv.date) return false;
            const d = new Date(inv.date);
            return d.getMonth() === month && d.getFullYear() === year;
        });
        return {
            facturadoMes: thisMonth.reduce((s, i) => s + Number(i.amount_total), 0),
            pendienteCobro: invoices.filter(i => i.status === "pending").reduce((s, i) => s + Number(i.amount_total), 0),
            vencidas: invoices.filter(i => i.status === "overdue").length,
            numFacturasMes: thisMonth.length,
        };
    }, [invoices]);

    const filteredInvoices = useMemo(() => {
        return invoices.filter(inv => {
            if (!inv.date) return true;
            const d = inv.date.slice(0, 10);
            if (dateFrom && d < dateFrom) return false;
            if (dateTo && d > dateTo) return false;
            return true;
        });
    }, [invoices, dateFrom, dateTo]);

    const handleDeleteInvoice = async (id: string) => {
        const confirmed = await showConfirm({
            title: t("deleteInvoice"),
            message: t("deleteInvoice"),
            confirmLabel: tc("delete"),
            cancelLabel: tc("cancel"),
            confirmVariant: "danger",
        });
        if (!confirmed) return;
        try {
            await api.erp.invoices.delete(id);
            setInvoices(prev => prev.filter(i => i.id !== id));
            useToastStore.getState().success("Factura eliminada");
        } catch (err: any) {
            useToastStore.getState().error(err?.message || "Error al eliminar factura");
        }
    };

    const columns: ColumnDef<Invoice, any>[] = [
        {
            accessorKey: "invoice_number",
            header: ({ column }) => <DataTableColumnHeader column={column} title={t("number")} />,
            cell: ({ row }) => {
                const inv = row.original;
                return (
                    <Link
                        href={`/ventas/facturas/${inv.id}`}
                        className="font-medium text-foreground flex items-center gap-2 hover:text-primary transition-colors"
                    >
                        <FileText className="w-4 h-4 text-muted-foreground" />
                        {inv.invoice_number || <span className="text-muted-foreground italic">{t("draft")}</span>}
                    </Link>
                );
            },
        },
        {
            id: "client_name",
            accessorFn: (row) => row.client?.name || t("unknownClient"),
            header: ({ column }) => <DataTableColumnHeader column={column} title={t("contact")} />,
            cell: ({ row }) => {
                const inv = row.original;
                return (
                    <div className="flex flex-col">
                        <span className="font-medium">{inv.client?.name || t("unknownClient")}</span>
                        {inv.client?.nif && <span className="text-xs text-muted-foreground">{inv.client.nif}</span>}
                    </div>
                );
            },
        },
        {
            accessorKey: "status",
            header: ({ column }) => <DataTableColumnHeader column={column} title={t("status")} />,
            cell: ({ row }) => <StatusBadge status={row.getValue("status")} />,
            filterFn: (row, id, value) => value.includes(row.getValue(id)),
        },
        {
            accessorKey: "date",
            header: ({ column }) => <DataTableColumnHeader column={column} title={t("date")} />,
            cell: ({ row }) => {
                const date = row.getValue("date") as string;
                return <span className="text-muted-foreground">{date ? new Date(date).toLocaleDateString("es-ES") : "-"}</span>;
            },
        },
        {
            accessorKey: "due_date",
            header: ({ column }) => <DataTableColumnHeader column={column} title={t("dueDate")} />,
            cell: ({ row }) => {
                const date = row.getValue("due_date") as string;
                return <span className="text-muted-foreground">{date ? new Date(date).toLocaleDateString("es-ES") : "-"}</span>;
            },
        },
        {
            accessorKey: "amount_total",
            header: ({ column }) => <DataTableColumnHeader column={column} title={t("total")} />,
            cell: ({ row }) => (
                <span className="font-medium text-right tabular-nums">
                    {Number(row.getValue("amount_total")).toLocaleString("es-ES", { minimumFractionDigits: 2 })}€
                </span>
            ),
        },
        {
            id: "actions",
            cell: ({ row }) => {
                const inv = row.original;
                return (
                    <div className="flex items-center justify-end gap-1">
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            onClick={() => downloadInvoicePdf(inv.id, inv.invoice_number)}
                            title={t("downloadPdf")}
                        >
                            <Download className="h-4 w-4" />
                        </Button>
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            onClick={() => router.push(`/ventas/facturas/nueva?duplicate_id=${inv.id}`)}
                            title={t("duplicate")}
                        >
                            <Copy className="h-4 w-4" />
                        </Button>
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 text-destructive hover:text-destructive"
                            onClick={() => handleDeleteInvoice(inv.id)}
                            title={tc("delete")}
                        >
                            <Trash2 className="h-4 w-4" />
                        </Button>
                    </div>
                );
            },
        },
    ];

    return {
        invoices, loading, dateFrom, setDateFrom, dateTo, setDateTo,
        kpis, filteredInvoices, handleDeleteInvoice, columns, statusFilterOptions,
    };
}
