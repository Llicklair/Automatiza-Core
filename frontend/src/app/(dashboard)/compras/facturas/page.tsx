"use client";

import { useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { ColumnDef } from "@tanstack/react-table";
import { ArrowDownToLine, CheckCircle2, Clock, Plus, Inbox, Trash2, Sparkles, Loader2 } from "lucide-react";
import { type Invoice } from "@/lib/api";
import { PageHeader } from "@/components/shared/PageHeader";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { DataTable, DataTableColumnHeader } from "@/components/data-table";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/button";
import { useFacturasRecibidas } from "./_hooks/useFacturasRecibidas";
import { RegistrarFacturaModal } from "./_components/RegistrarFacturaModal";
import { PageContainer } from "@/components/shared/PageContainer";

const STATUS_FILTER_OPTIONS = [
    { labelKey: "statusOptions.draft",     value: "draft" },
    { labelKey: "statusOptions.pending",   value: "pending" },
    { labelKey: "statusOptions.paid",      value: "paid" },
    { labelKey: "statusOptions.cancelled", value: "cancelled" },
];

export default function FacturasRecibidasPage() {
    const t = useTranslations("compras.facturas");
    const {
        invoices, clients, loading,
        showModal, setShowModal,
        supplierId, setSupplierId,
        supplierName, setSupplierName,
        useExisting, setUseExisting,
        invoiceNumber, setInvoiceNumber,
        amount, setAmount,
        taxPct, setTaxPct,
        date, setDate,
        dueDate, setDueDate,
        invStatus, setInvStatus,
        fiscalRegime, setFiscalRegime,
        retencionRate, setRetencionRate,
        submitting,
        totalPendiente, totalPagado30,
        resetModal, handleRegister, handleScan, handleStatusChange, handleDeleteInvoice,
    } = useFacturasRecibidas();

    const [scanning, setScanning] = useState(false);

    const onFileSelected = async (file: File) => {
        if (!file) return;
        if (!file.type.startsWith("image/") && file.type !== "application/pdf") {
            return;
        }
        setScanning(true);
        try {
            await handleScan(file);
        } finally {
            setScanning(false);
        }
    };

    const columns = useMemo<ColumnDef<Invoice, any>[]>(() => [
        {
            accessorKey: "supplier",
            accessorFn: row => row.client?.name || t("unknownSupplier"),
            header: ({ column }) => <DataTableColumnHeader column={column} title={t("columns.supplier")} />,
            cell: ({ row }) => (
                <div>
                    <div className="font-semibold text-foreground">{row.original.client?.name || t("unknownSupplier")}</div>
                    <div className="text-xs text-muted-foreground font-mono mt-0.5">{row.original.invoice_number || t("noNumber")}</div>
                </div>
            ),
            filterFn: (row, _id, filterValue: string) => {
                const name = (row.original.client?.name || "").toLowerCase();
                const num  = (row.original.invoice_number || "").toLowerCase();
                const term = filterValue.toLowerCase();
                return name.includes(term) || num.includes(term);
            },
        },
        {
            accessorKey: "status",
            header: ({ column }) => <DataTableColumnHeader column={column} title={t("columns.status")} />,
            cell: ({ row }) => <StatusBadge status={row.original.status} />,
            filterFn: (row, id, value) => (value as string[]).includes(row.getValue(id)),
        },
        {
            accessorKey: "date",
            header: ({ column }) => <DataTableColumnHeader column={column} title={t("columns.date")} />,
            cell: ({ row }) => (
                <span className="text-sm text-muted-foreground">
                    {row.original.date ? new Date(row.original.date).toLocaleDateString("es-ES") : "—"}
                </span>
            ),
        },
        {
            accessorKey: "due_date",
            header: ({ column }) => <DataTableColumnHeader column={column} title={t("columns.dueDate")} />,
            cell: ({ row }) => (
                <span className="text-sm text-muted-foreground">
                    {row.original.due_date ? new Date(row.original.due_date).toLocaleDateString("es-ES") : "—"}
                </span>
            ),
        },
        {
            accessorKey: "amount_total",
            header: ({ column }) => <DataTableColumnHeader column={column} title={t("columns.amount")} />,
            cell: ({ row }) => (
                <span className="font-bold text-foreground">
                    {Number(row.original.amount_total).toLocaleString("es-ES", { minimumFractionDigits: 2 })}€
                </span>
            ),
        },
        {
            id: "actions",
            header: t("columns.action"),
            cell: ({ row }) => {
                const inv = row.original;
                return (
                    <div className="flex items-center justify-end gap-2">
                        {inv.status === "pending" && (
                            <Button variant="outline" size="sm"
                                className="text-xs text-emerald-500 border-emerald-500/20 hover:border-emerald-400/40 hover:text-emerald-400"
                                onClick={() => handleStatusChange(inv.id, "paid")}>
                                {t("markPaid")}
                            </Button>
                        )}
                        <Button variant="ghost" size="icon"
                            className="h-8 w-8 text-destructive/60 hover:text-destructive hover:bg-destructive/10"
                            onClick={() => handleDeleteInvoice(inv.id)} title={t("deleteInvoice")} aria-label={t("deleteInvoice")}>
                            <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                        </Button>
                    </div>
                );
            },
        },
    ], [handleDeleteInvoice, handleStatusChange, t]);

    const statusFilterOptions = STATUS_FILTER_OPTIONS.map(o => ({ label: t(o.labelKey), value: o.value }));

    return (
        <PageContainer width="6xl" className="space-y-8">
            <PageHeader
                title={t("title")}
                description={t("description")}
                actions={
                    <div className="flex items-center gap-2">
                        <label
                            className={`inline-flex items-center gap-2 rounded-md border border-primary/30 bg-primary/10 text-primary hover:bg-primary/20 px-3 h-9 text-sm font-medium cursor-pointer transition-colors ${scanning ? "opacity-50 pointer-events-none" : ""}`}
                            title={t("scanTooltip")}
                        >
                            {scanning
                                ? <><Loader2 className="h-4 w-4 animate-spin" /> {t("scanning")}</>
                                : <><Sparkles className="h-4 w-4" /> {t("scan")}</>}
                            <input
                                type="file"
                                accept="image/png,image/jpeg,image/webp,application/pdf"
                                className="hidden"
                                onChange={(e) => {
                                    const f = e.target.files?.[0];
                                    if (f) onFileSelected(f);
                                    e.target.value = "";
                                }}
                            />
                        </label>
                        <Button onClick={() => setShowModal(true)}>
                            <Plus className="mr-2 h-4 w-4" /> {t("register")}
                        </Button>
                    </div>
                }
            />

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-card border border-border p-6 rounded-2xl flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center">
                        <Clock className="w-6 h-6 text-amber-500" />
                    </div>
                    <div>
                        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-1">{t("stats.pending")}</p>
                        <p className="text-2xl font-bold text-amber-500">{totalPendiente.toLocaleString("es-ES", { minimumFractionDigits: 2 })}€</p>
                    </div>
                </div>
                <div className="bg-card border border-border p-6 rounded-2xl flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
                        <CheckCircle2 className="w-6 h-6 text-emerald-500" />
                    </div>
                    <div>
                        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-1">{t("stats.paid30")}</p>
                        <p className="text-2xl font-bold text-emerald-500">{totalPagado30.toLocaleString("es-ES", { minimumFractionDigits: 2 })}€</p>
                    </div>
                </div>
            </div>

            {!loading && invoices.length === 0 ? (
                <div className="bg-card border border-border rounded-2xl">
                    <EmptyState
                        icon={Inbox}
                        title={t("empty.title")}
                        description={t("empty.description")}
                        action={{ label: t("empty.action"), onClick: () => setShowModal(true) }}
                        size="sm"
                    />
                </div>
            ) : (
                <div className="bg-card border border-border rounded-2xl overflow-hidden shadow-xl shadow-black/20">
                    <DataTable
                        columns={columns}
                        data={invoices}
                        searchKey="supplier"
                        searchPlaceholder={t("searchPlaceholder")}
                        facetedFilters={[{ column: "status", title: t("columns.status"), options: statusFilterOptions }]}
                        isLoading={loading}
                        emptyMessage={t("noResults")}
                    />
                </div>
            )}

            <RegistrarFacturaModal
                open={showModal}
                onClose={() => { setShowModal(false); resetModal(); }}
                clients={clients}
                supplierId={supplierId} setSupplierId={setSupplierId}
                supplierName={supplierName} setSupplierName={setSupplierName}
                useExisting={useExisting} setUseExisting={setUseExisting}
                invoiceNumber={invoiceNumber} setInvoiceNumber={setInvoiceNumber}
                amount={amount} setAmount={setAmount}
                taxPct={taxPct} setTaxPct={setTaxPct}
                date={date} setDate={setDate}
                dueDate={dueDate} setDueDate={setDueDate}
                invStatus={invStatus} setInvStatus={setInvStatus}
                fiscalRegime={fiscalRegime} setFiscalRegime={setFiscalRegime}
                retencionRate={retencionRate} setRetencionRate={setRetencionRate}
                submitting={submitting}
                onSubmit={handleRegister}
            />
        </PageContainer>
    );
}
