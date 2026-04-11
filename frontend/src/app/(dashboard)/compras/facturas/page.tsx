"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import { api, Invoice, Client } from "@/lib/api";
import { ColumnDef } from "@tanstack/react-table";
import {
    ArrowDownToLine, CheckCircle2, Clock, Plus, Loader2, Inbox, Trash2,
} from "lucide-react";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";
import { PageHeader } from "@/components/shared/PageHeader";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { DataTable, DataTableColumnHeader } from "@/components/data-table";
import { FormModal, FormField } from "@/components/shared";
import { EmptyState } from "@/components/shared/EmptyState";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
    Select, SelectTrigger, SelectValue, SelectContent, SelectItem,
} from "@/components/ui/select";

const today = () => new Date().toISOString().slice(0, 10);

const STATUS_FILTER_OPTIONS = [
    { label: "Borrador", value: "draft" },
    { label: "Pendiente", value: "pending" },
    { label: "Pagada", value: "paid" },
    { label: "Cancelada", value: "cancelled" },
];

export default function FacturasRecibidasPage() {
    const toast = useToastStore();
    const [invoices, setInvoices] = useState<Invoice[]>([]);
    const [clients, setClients] = useState<Client[]>([]);
    const [loading, setLoading] = useState(true);

    // Modal registro manual
    const [showModal, setShowModal] = useState(false);
    const [supplierId, setSupplierId] = useState("");
    const [supplierName, setSupplierName] = useState("");
    const [useExisting, setUseExisting] = useState(true);
    const [invoiceNumber, setInvoiceNumber] = useState("");
    const [amount, setAmount] = useState("");
    const [taxPct, setTaxPct] = useState("21");
    const [date, setDate] = useState(today());
    const [dueDate, setDueDate] = useState("");
    const [invStatus, setInvStatus] = useState("pending");
    const [submitting, setSubmitting] = useState(false);

    const loadData = useCallback(async () => {
        setLoading(true);
        try {
            const [allInvoices, allClients] = await Promise.all([
                api.erp.invoices.list({ limit: 200 }),
                api.erp.clients.list({ limit: 200 }),
            ]);
            setInvoices(allInvoices.filter(i => i.invoice_type === "received"));
            setClients(allClients);
        } catch { /* silent */ }
        finally { setLoading(false); }
    }, []);

    useEffect(() => { loadData(); }, [loadData]);

    const handleRegister = async (e: React.FormEvent) => {
        e.preventDefault();
        setSubmitting(true);
        try {
            let clientId = supplierId;
            if (!useExisting || !supplierId) {
                if (!supplierName.trim()) { toast.warning("Indica el nombre del proveedor"); setSubmitting(false); return; }
                const newClient = await api.erp.clients.create({ name: supplierName, client_type: "supplier" });
                clientId = newClient.id;
            }
            const baseAmount = parseFloat(amount) || 0;
            const inv = await api.erp.invoices.create(clientId, {
                invoice_number: invoiceNumber || null,
                date: new Date(date).toISOString(),
                due_date: dueDate ? new Date(dueDate).toISOString() : null,
                status: invStatus,
                invoice_type: "received",
                lines: [{
                    description: "Factura recibida",
                    quantity: 1,
                    unit_price: baseAmount,
                    discount_percentage: 0,
                    tax_percentage: parseFloat(taxPct),
                }],
            } as any);
            setInvoices(prev => [inv, ...prev]);
            setShowModal(false);
            resetModal();
        } catch (err: any) {
            toast.error(err?.message || "Error registrando factura");
        } finally {
            setSubmitting(false);
        }
    };

    const resetModal = () => {
        setSupplierId(""); setSupplierName(""); setUseExisting(true);
        setInvoiceNumber(""); setAmount(""); setTaxPct("21");
        setDate(today()); setDueDate(""); setInvStatus("pending");
    };

    const handleStatusChange = useCallback(async (invId: string, nextStatus: string) => {
        try {
            const updated = await api.erp.invoices.updateStatus(invId, nextStatus);
            setInvoices(prev => prev.map(i => i.id === invId ? updated : i));
        } catch (err: any) {
            toast.error(err?.message || "Error cambiando estado");
        }
    }, [toast]);

    const handleDeleteInvoice = useCallback(async (id: string) => {
        const confirmed = await showConfirm({
            title: "Eliminar factura",
            message: "¿Eliminar esta factura? Esta acción no se puede deshacer.",
            confirmVariant: "danger",
            confirmLabel: "Eliminar",
        });
        if (!confirmed) return;
        try {
            await api.erp.invoices.delete(id);
            setInvoices(prev => prev.filter(i => i.id !== id));
            toast.success("Factura eliminada");
        } catch (err: any) {
            toast.error(err?.message || "Error al eliminar factura");
        }
    }, [toast]);

    const totalPendiente = invoices.filter(i => i.status === "pending").reduce((a, b) => a + Number(b.amount_total), 0);
    const thirtyDaysAgo = new Date(); thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
    const totalPagado30 = invoices
        .filter(i => i.status === "paid" && new Date(i.created_at) >= thirtyDaysAgo)
        .reduce((a, b) => a + Number(b.amount_total), 0);

    const columns = useMemo<ColumnDef<Invoice, any>[]>(() => [
        {
            accessorKey: "supplier",
            accessorFn: (row) => row.client?.name || "Desconocido",
            header: ({ column }) => <DataTableColumnHeader column={column} title="Proveedor" />,
            cell: ({ row }) => (
                <div>
                    <div className="font-semibold text-foreground">{row.original.client?.name || "Desconocido"}</div>
                    <div className="text-xs text-muted-foreground font-mono mt-0.5">{row.original.invoice_number || "S/N"}</div>
                </div>
            ),
            filterFn: (row, _columnId, filterValue: string) => {
                const name = (row.original.client?.name || "").toLowerCase();
                const num = (row.original.invoice_number || "").toLowerCase();
                const term = filterValue.toLowerCase();
                return name.includes(term) || num.includes(term);
            },
        },
        {
            accessorKey: "status",
            header: ({ column }) => <DataTableColumnHeader column={column} title="Estado" />,
            cell: ({ row }) => <StatusBadge status={row.original.status} />,
            filterFn: (row, id, value) => (value as string[]).includes(row.getValue(id)),
        },
        {
            accessorKey: "date",
            header: ({ column }) => <DataTableColumnHeader column={column} title="Fecha" />,
            cell: ({ row }) => (
                <span className="text-sm text-muted-foreground">
                    {row.original.date ? new Date(row.original.date).toLocaleDateString("es-ES") : "\u2014"}
                </span>
            ),
        },
        {
            accessorKey: "due_date",
            header: ({ column }) => <DataTableColumnHeader column={column} title="Vencimiento" />,
            cell: ({ row }) => (
                <span className="text-sm text-muted-foreground">
                    {row.original.due_date ? new Date(row.original.due_date).toLocaleDateString("es-ES") : "\u2014"}
                </span>
            ),
        },
        {
            accessorKey: "amount_total",
            header: ({ column }) => <DataTableColumnHeader column={column} title="Monto" />,
            cell: ({ row }) => (
                <span className="font-bold text-foreground">
                    {Number(row.original.amount_total).toLocaleString("es-ES", { minimumFractionDigits: 2 })}\u20AC
                </span>
            ),
        },
        {
            id: "actions",
            header: "Acción",
            cell: ({ row }) => {
                const inv = row.original;
                return (
                    <div className="flex items-center justify-end gap-2">
                        {inv.status === "pending" && (
                            <Button
                                variant="outline"
                                size="sm"
                                className="text-xs text-emerald-500 border-emerald-500/20 hover:border-emerald-400/40 hover:text-emerald-400"
                                onClick={() => handleStatusChange(inv.id, "paid")}
                            >
                                Marcar pagada
                            </Button>
                        )}
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 text-destructive/60 hover:text-destructive hover:bg-destructive/10"
                            onClick={() => handleDeleteInvoice(inv.id)}
                            title="Eliminar factura"
                        >
                            <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                    </div>
                );
            },
        },
    ], [handleDeleteInvoice, handleStatusChange]);

    return (
        <div className="p-8 max-w-6xl mx-auto space-y-8">
            <PageHeader
                title="Facturas Recibidas"
                description="Gestiona tus compras, gastos y proveedores."
                actions={
                    <Button onClick={() => setShowModal(true)}>
                        <Plus className="mr-2 h-4 w-4" />
                        Registrar Factura
                    </Button>
                }
            />

            {/* KPI cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-card border border-border p-6 rounded-2xl flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center">
                        <Clock className="w-6 h-6 text-amber-500" />
                    </div>
                    <div>
                        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-1">Pendiente de Pago</p>
                        <p className="text-2xl font-bold text-amber-500">{totalPendiente.toLocaleString("es-ES", { minimumFractionDigits: 2 })}\u20AC</p>
                    </div>
                </div>
                <div className="bg-card border border-border p-6 rounded-2xl flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
                        <CheckCircle2 className="w-6 h-6 text-emerald-500" />
                    </div>
                    <div>
                        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-1">Pagado (últimos 30d)</p>
                        <p className="text-2xl font-bold text-emerald-500">{totalPagado30.toLocaleString("es-ES", { minimumFractionDigits: 2 })}\u20AC</p>
                    </div>
                </div>
            </div>

            {/* Data table */}
            {!loading && invoices.length === 0 ? (
                <div className="bg-card border border-border rounded-2xl">
                    <EmptyState
                        icon={Inbox}
                        title="No tienes facturas de compra registradas"
                        description="Registra tu primera factura para empezar a gestionar tus compras."
                        action={
                            <Button variant="outline" onClick={() => setShowModal(true)}>
                                <Plus className="mr-2 h-4 w-4" />
                                Registrar primera factura
                            </Button>
                        }
                    />
                </div>
            ) : (
                <div className="bg-card border border-border rounded-2xl overflow-hidden shadow-xl shadow-black/20">
                    <DataTable
                        columns={columns}
                        data={invoices}
                        searchKey="supplier"
                        searchPlaceholder="Buscar por proveedor o número..."
                        facetedFilters={[
                            {
                                column: "status",
                                title: "Estado",
                                options: STATUS_FILTER_OPTIONS,
                            },
                        ]}
                        isLoading={loading}
                        emptyMessage="Sin resultados para tu búsqueda."
                    />
                </div>
            )}

            {/* Modal registrar factura recibida */}
            <FormModal
                open={showModal}
                onClose={() => { setShowModal(false); resetModal(); }}
                title="Registrar Factura Recibida"
                description="Completa los datos de la factura de compra."
                onSubmit={handleRegister}
                isSubmitting={submitting}
                submitLabel="Registrar"
                className="sm:max-w-lg"
            >
                <FormField label="Proveedor" required>
                    <div className="flex gap-2 mb-2">
                        <Button
                            type="button"
                            size="sm"
                            variant={useExisting ? "default" : "outline"}
                            onClick={() => setUseExisting(true)}
                        >
                            Existente
                        </Button>
                        <Button
                            type="button"
                            size="sm"
                            variant={!useExisting ? "default" : "outline"}
                            onClick={() => setUseExisting(false)}
                        >
                            Nuevo
                        </Button>
                    </div>
                    {useExisting ? (
                        <Select value={supplierId} onValueChange={setSupplierId}>
                            <SelectTrigger>
                                <SelectValue placeholder="Seleccionar proveedor..." />
                            </SelectTrigger>
                            <SelectContent>
                                {clients.map(c => (
                                    <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    ) : (
                        <Input
                            required={!useExisting}
                            value={supplierName}
                            onChange={e => setSupplierName(e.target.value)}
                            placeholder="Nombre del proveedor"
                        />
                    )}
                </FormField>

                <div className="grid grid-cols-2 gap-4">
                    <FormField label="Nº Factura">
                        <Input
                            value={invoiceNumber}
                            onChange={e => setInvoiceNumber(e.target.value)}
                            placeholder="Opcional"
                        />
                    </FormField>
                    <FormField label="Estado">
                        <Select value={invStatus} onValueChange={setInvStatus}>
                            <SelectTrigger>
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="pending">Pendiente</SelectItem>
                                <SelectItem value="paid">Pagada</SelectItem>
                                <SelectItem value="draft">Borrador</SelectItem>
                            </SelectContent>
                        </Select>
                    </FormField>
                    <FormField label="Importe base (€)" required>
                        <Input
                            type="number"
                            required
                            min="0"
                            step="0.01"
                            value={amount}
                            onChange={e => setAmount(e.target.value)}
                            placeholder="0.00"
                        />
                    </FormField>
                    <FormField label="% IVA">
                        <Select value={taxPct} onValueChange={setTaxPct}>
                            <SelectTrigger>
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="21">21%</SelectItem>
                                <SelectItem value="10">10%</SelectItem>
                                <SelectItem value="4">4%</SelectItem>
                                <SelectItem value="0">0%</SelectItem>
                            </SelectContent>
                        </Select>
                    </FormField>
                    <FormField label="Fecha" required>
                        <Input
                            type="date"
                            required
                            value={date}
                            onChange={e => setDate(e.target.value)}
                        />
                    </FormField>
                    <FormField label="Vencimiento">
                        <Input
                            type="date"
                            value={dueDate}
                            onChange={e => setDueDate(e.target.value)}
                        />
                    </FormField>
                </div>
            </FormModal>
        </div>
    );
}
