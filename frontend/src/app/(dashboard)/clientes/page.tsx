"use client";

import { useEffect, useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { ColumnDef } from "@tanstack/react-table";
import { api, Client, Invoice } from "@/lib/api";
import { useNotificationStore } from "@/stores/notifications";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";
import Link from "next/link";

import { PageHeader, StatusBadge, FormModal, FormField, KpiCard, EmptyState } from "@/components/shared";
import { DataTable, DataTableColumnHeader } from "@/components/data-table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";

import {
    Plus, Building2, UserCircle, Mail, MapPin, X,
    FileText, Phone, Loader2, Download, ExternalLink, Eye,
} from "lucide-react";

// ── Helpers ──────────────────────────────────────────────────────────────────

async function downloadInvoicePdf(invoiceId: string, invoiceNumber: string | null, errorMsg: string) {
    try {
        await api.erp.invoices.downloadPdf(invoiceId, invoiceNumber);
    } catch {
        useToastStore.getState().show(errorMsg, "error");
    }
}

function getInitials(name: string) {
    return name
        .split(/\s+/)
        .slice(0, 2)
        .map((w) => w[0])
        .join("")
        .toUpperCase();
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function ClientesPage() {
    const t = useTranslations("clientes");
    const tc = useTranslations("common");
    const toast = useToastStore();
    const [clients, setClients] = useState<Client[]>([]);

    const CLIENT_TYPE_MAP: Record<string, { label: string; variant: "info" | "warning" | "default" | "success" }> = {
        customer: { label: t("typeClient"), variant: "info" },
        supplier: { label: t("typeSupplier"), variant: "warning" },
        company: { label: t("typeCompany"), variant: "default" },
        lead: { label: t("typeLead"), variant: "success" },
    };

    const CLIENT_TYPE_OPTIONS = [
        { label: t("typeClient"), value: "customer" },
        { label: t("typeSupplier"), value: "supplier" },
        { label: t("typeCompany"), value: "company" },
        { label: t("typeLead"), value: "lead" },
    ];
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Drawer
    const [selectedClient, setSelectedClient] = useState<Client | null>(null);
    const [clientInvoices, setClientInvoices] = useState<Invoice[]>([]);
    const [loadingInvoices, setLoadingInvoices] = useState(false);

    // Creacion / Edicion
    const [isCreating, setIsCreating] = useState(false);
    const [editingClient, setEditingClient] = useState<Client | null>(null);
    const [newClient, setNewClient] = useState<Partial<Client>>({ client_type: "customer" });
    const [saving, setSaving] = useState(false);
    const [deleting, setDeleting] = useState(false);
    const refreshKey = useNotificationStore((s) => s.refreshKey);

    // ── Data loading ─────────────────────────────────────────────────────────

    const loadClients = async () => {
        try {
            setLoading(true);
            const data = await api.erp.clients.list();
            setClients(data);
        } catch (err: any) {
            setError(err.message || t("errorLoading"));
        } finally {
            setLoading(false);
        }
    };

    // eslint-disable-next-line react-hooks/exhaustive-deps
    useEffect(() => { loadClients(); }, [refreshKey]);

    // ── CRUD handlers ────────────────────────────────────────────────────────

    const handleCreateClient = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            setSaving(true);
            if (editingClient) {
                await api.erp.clients.update(editingClient.id, newClient);
            } else {
                await api.erp.clients.create(newClient);
            }
            setIsCreating(false);
            setEditingClient(null);
            setNewClient({ client_type: "customer" });
            loadClients();
        } catch (err: any) {
            toast.error(err.message || t("errorSaving"));
        } finally {
            setSaving(false);
        }
    };

    const openEditClient = (client: Client) => {
        setEditingClient(client);
        setNewClient({
            name: client.name, nif: client.nif, client_type: client.client_type,
            email: client.email, phone: client.phone, address: client.address,
            city: client.city, postal_code: client.postal_code,
        });
        setIsCreating(true);
        closeDrawer();
    };

    const handleDeleteClient = async (client: Client) => {
        if (!await showConfirm({ message: t("deleteConfirm", { name: client.name }), confirmLabel: tc("delete"), confirmVariant: "danger" })) return;
        setDeleting(true);
        try {
            await api.erp.clients.delete(client.id);
            closeDrawer();
            loadClients();
        } catch (err: any) {
            toast.error(err.message || t("errorDeleting"));
        } finally {
            setDeleting(false);
        }
    };

    const openClientDrawer = async (client: Client) => {
        setSelectedClient(client);
        setLoadingInvoices(true);
        try {
            const data = await api.erp.clients.invoices(client.id);
            setClientInvoices(data);
        } catch {
            setClientInvoices([]);
        } finally {
            setLoadingInvoices(false);
        }
    };

    const closeDrawer = () => {
        setSelectedClient(null);
        setClientInvoices([]);
    };

    const closeModal = () => {
        setIsCreating(false);
        setEditingClient(null);
        setNewClient({ client_type: "customer" });
    };

    // ── Derived data ─────────────────────────────────────────────────────────

    const totalFacturado = clientInvoices.reduce((s, i) => s + Number(i.amount_total), 0);

    // ── DataTable columns ────────────────────────────────────────────────────

    const columns = useMemo<ColumnDef<Client>[]>(() => [
        {
            accessorKey: "name",
            header: ({ column }) => <DataTableColumnHeader column={column} title={t("nameColumn")} />,
            cell: ({ row }) => {
                const client = row.original;
                return (
                    <div className="flex items-center gap-3 min-w-0">
                        <Avatar className="h-8 w-8 rounded-lg">
                            <AvatarFallback className="rounded-lg bg-primary/10 text-primary text-xs font-semibold">
                                {client.client_type === "company" || client.client_type === "supplier"
                                    ? <Building2 className="h-4 w-4" />
                                    : getInitials(client.name)
                                }
                            </AvatarFallback>
                        </Avatar>
                        <div className="min-w-0">
                            <p className="text-sm font-medium text-foreground truncate">{client.name}</p>
                            {client.city && <p className="text-xs text-muted-foreground truncate">{client.city}</p>}
                        </div>
                    </div>
                );
            },
        },
        {
            accessorKey: "nif",
            header: ({ column }) => <DataTableColumnHeader column={column} title={t("nifColumn")} />,
            cell: ({ row }) => {
                const nif = row.original.nif;
                return nif
                    ? <span className="text-xs font-mono bg-muted border border-border text-foreground px-2 py-0.5 rounded">{nif}</span>
                    : <span className="text-xs text-muted-foreground italic">{t("noNif")}</span>;
            },
        },
        {
            accessorKey: "client_type",
            header: ({ column }) => <DataTableColumnHeader column={column} title={t("typeColumn")} />,
            cell: ({ row }) => {
                const ct = CLIENT_TYPE_MAP[row.original.client_type] ?? { label: row.original.client_type, variant: "default" as const };
                return <StatusBadge status={row.original.client_type} label={ct.label} />;
            },
            filterFn: (row, id, value: string[]) => value.includes(row.getValue(id)),
        },
        {
            accessorKey: "email",
            header: ({ column }) => <DataTableColumnHeader column={column} title={t("emailColumn")} />,
            cell: ({ row }) => (
                <span className="text-xs text-muted-foreground truncate block max-w-[180px]">
                    {row.original.email || <span className="italic">--</span>}
                </span>
            ),
        },
        {
            accessorKey: "phone",
            header: ({ column }) => <DataTableColumnHeader column={column} title={t("phoneColumn")} />,
            cell: ({ row }) => (
                <span className="text-xs text-muted-foreground truncate">
                    {row.original.phone || <span>--</span>}
                </span>
            ),
        },
        {
            accessorKey: "created_at",
            header: ({ column }) => <DataTableColumnHeader column={column} title={t("createdColumn")} />,
            cell: ({ row }) => (
                <span className="text-xs text-muted-foreground">
                    {new Date(row.original.created_at).toLocaleDateString("es-ES", { day: "2-digit", month: "short", year: "2-digit" })}
                </span>
            ),
        },
        {
            id: "actions",
            cell: ({ row }) => (
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => openClientDrawer(row.original)}
                >
                    <Eye className="h-4 w-4 mr-1" />
                    {t("view")}
                </Button>
            ),
        },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    ], [t]);

    // ── Faceted filters ──────────────────────────────────────────────────────

    const facetedFilters = useMemo(() => [
        {
            column: "client_type",
            title: t("type"),
            options: CLIENT_TYPE_OPTIONS.map((o) => ({ label: o.label, value: o.value })),
        },
    ], [t, CLIENT_TYPE_OPTIONS]);

    // ── Render ───────────────────────────────────────────────────────────────

    if (error && !loading) {
        return (
            <div className="p-8 max-w-7xl mx-auto">
                <EmptyState title={t("errorLoading")} description={error} />
            </div>
        );
    }

    return (
        <div className="p-8 max-w-7xl mx-auto space-y-6 relative">
            {/* Header */}
            <PageHeader
                title={t("title")}
                description={t("contactCount", { count: clients.length })}
                icon={Building2}
                actions={
                    <Button onClick={() => setIsCreating(true)}>
                        <Plus className="h-4 w-4 mr-2" />
                        {t("newClient")}
                    </Button>
                }
            />

            {/* Table or Empty */}
            {!loading && clients.length === 0 ? (
                <EmptyState
                    icon={Building2}
                    title={t("emptyTitle")}
                    description={t("emptyDescription")}
                    action={
                        <div className="flex flex-col items-center gap-4">
                            <Button onClick={() => setIsCreating(true)}>
                                <Plus className="h-4 w-4 mr-2" />
                                {t("newClient")}
                            </Button>
                            <div className="flex flex-col items-center gap-2">
                                <p className="text-xs text-muted-foreground uppercase tracking-widest font-medium">{t("orCreateWithAI")}</p>
                                <div className="flex flex-wrap justify-center gap-2">
                                    {[
                                        t("aiSuggestion1"),
                                        t("aiSuggestion2"),
                                        t("aiSuggestion3"),
                                    ].map((suggestion) => (
                                        <Button
                                            key={suggestion}
                                            variant="outline"
                                            size="sm"
                                            className="text-xs"
                                            onClick={async () => {
                                                try {
                                                    await api.tasks.create("crm", suggestion);
                                                    useToastStore.getState().show(t("taskSent"), "info");
                                                } catch {
                                                    useToastStore.getState().show(t("errorSendingTask"), "error");
                                                }
                                            }}
                                        >
                                            {suggestion}
                                        </Button>
                                    ))}
                                </div>
                            </div>
                        </div>
                    }
                />
            ) : (
                <DataTable
                    columns={columns}
                    data={clients}
                    searchKey="name"
                    searchPlaceholder={t("searchPlaceholder")}
                    facetedFilters={facetedFilters}
                    isLoading={loading}
                    emptyMessage={t("noMatchFilter")}
                    pageSize={15}
                />
            )}

            {/* ── FormModal: Create / Edit ──────────────────────────────────── */}
            <FormModal
                open={isCreating}
                onClose={closeModal}
                title={editingClient ? t("editClient") : t("newClient")}
                description={editingClient ? t("editClientDesc") : t("newClientDesc")}
                onSubmit={handleCreateClient}
                isSubmitting={saving}
                submitLabel={editingClient ? t("saveChanges") : t("createClient")}
                className="sm:max-w-lg"
            >
                <div className="grid grid-cols-2 gap-4">
                    <FormField label={t("companyName")} required className="col-span-2">
                        <Input
                            required
                            value={newClient.name || ""}
                            onChange={(e) => setNewClient({ ...newClient, name: e.target.value })}
                            placeholder={t("namePlaceholder")}
                        />
                    </FormField>

                    <FormField label={t("nif")}>
                        <Input
                            value={newClient.nif || ""}
                            onChange={(e) => setNewClient({ ...newClient, nif: e.target.value })}
                            placeholder={t("nifPlaceholder")}
                            className="uppercase"
                        />
                    </FormField>

                    <FormField label={t("type")}>
                        <Select
                            value={newClient.client_type || "customer"}
                            onValueChange={(v) => setNewClient({ ...newClient, client_type: v })}
                        >
                            <SelectTrigger>
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                {CLIENT_TYPE_OPTIONS.map((o) => (
                                    <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </FormField>

                    <FormField label={t("email")}>
                        <Input
                            type="email"
                            value={newClient.email || ""}
                            onChange={(e) => setNewClient({ ...newClient, email: e.target.value })}
                            placeholder={t("emailPlaceholder")}
                        />
                    </FormField>

                    <FormField label={t("phone")}>
                        <Input
                            type="tel"
                            value={newClient.phone || ""}
                            onChange={(e) => setNewClient({ ...newClient, phone: e.target.value })}
                            placeholder={t("phonePlaceholder")}
                        />
                    </FormField>

                    <FormField label={t("address")} className="col-span-2">
                        <Input
                            value={newClient.address || ""}
                            onChange={(e) => setNewClient({ ...newClient, address: e.target.value })}
                            placeholder={t("addressPlaceholder")}
                        />
                    </FormField>

                    <FormField label={t("city")}>
                        <Input
                            value={newClient.city || ""}
                            onChange={(e) => setNewClient({ ...newClient, city: e.target.value })}
                            placeholder={t("cityPlaceholder")}
                        />
                    </FormField>

                    <FormField label={t("postalCode")}>
                        <Input
                            value={newClient.postal_code || ""}
                            onChange={(e) => setNewClient({ ...newClient, postal_code: e.target.value })}
                            placeholder={t("postalCodePlaceholder")}
                        />
                    </FormField>
                </div>
            </FormModal>

            {/* ── Backdrop for drawer ───────────────────────────────────────── */}
            {selectedClient && (
                <div
                    className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 transition-opacity"
                    onClick={closeDrawer}
                />
            )}

            {/* ── Drawer lateral detalle cliente ────────────────────────────── */}
            <div className={`fixed top-0 right-0 h-full w-full max-w-[480px] bg-card border-l border-border shadow-2xl z-50 transform transition-transform duration-300 ease-in-out flex flex-col ${selectedClient ? "translate-x-0" : "translate-x-full"}`}>
                {selectedClient && (
                    <>
                        {/* Header del drawer */}
                        <div className="px-6 py-5 border-b border-border bg-muted sticky top-0 z-10">
                            <div className="flex items-start justify-between gap-3">
                                <div className="flex items-center gap-3 min-w-0">
                                    <Avatar className="h-12 w-12 rounded-xl">
                                        <AvatarFallback className="rounded-xl bg-primary/10 text-primary text-sm font-bold">
                                            {selectedClient.client_type === "company" || selectedClient.client_type === "supplier"
                                                ? <Building2 className="h-6 w-6" />
                                                : getInitials(selectedClient.name)
                                            }
                                        </AvatarFallback>
                                    </Avatar>
                                    <div className="min-w-0">
                                        <h2 className="text-lg font-bold text-foreground leading-tight truncate">{selectedClient.name}</h2>
                                        <div className="flex items-center gap-2 mt-1 flex-wrap">
                                            {selectedClient.nif && (
                                                <span className="text-xs font-mono text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded">
                                                    {selectedClient.nif}
                                                </span>
                                            )}
                                            {(() => {
                                                const typeInfo = CLIENT_TYPE_MAP[selectedClient.client_type] ?? { label: selectedClient.client_type, variant: "default" as const };
                                                return <StatusBadge status={selectedClient.client_type} label={typeInfo.label} />;
                                            })()}
                                        </div>
                                    </div>
                                </div>
                                <Button variant="ghost" size="icon" onClick={closeDrawer} className="shrink-0">
                                    <X className="h-5 w-5" />
                                </Button>
                            </div>
                        </div>

                        <div className="flex-1 overflow-y-auto">
                            {/* Datos de contacto */}
                            <div className="px-6 py-5 border-b border-border">
                                <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">{t("contactInfo")}</h3>
                                <dl className="space-y-2.5">
                                    {selectedClient.email && (
                                        <div className="flex items-center gap-3">
                                            <Mail className="h-4 w-4 text-muted-foreground shrink-0" />
                                            <span className="text-sm text-foreground">{selectedClient.email}</span>
                                        </div>
                                    )}
                                    {selectedClient.phone && (
                                        <div className="flex items-center gap-3">
                                            <Phone className="h-4 w-4 text-muted-foreground shrink-0" />
                                            <span className="text-sm text-foreground">{selectedClient.phone}</span>
                                        </div>
                                    )}
                                    {selectedClient.address && (
                                        <div className="flex items-start gap-3">
                                            <MapPin className="h-4 w-4 text-muted-foreground shrink-0 mt-0.5" />
                                            <span className="text-sm text-foreground">{selectedClient.address}</span>
                                        </div>
                                    )}
                                    {(selectedClient.city || selectedClient.postal_code) && (
                                        <div className="flex items-center gap-3 pl-7">
                                            <span className="text-sm text-muted-foreground">
                                                {[selectedClient.postal_code, selectedClient.city].filter(Boolean).join(" · ")}
                                            </span>
                                        </div>
                                    )}
                                    {!selectedClient.email && !selectedClient.phone && !selectedClient.address && !selectedClient.city && (
                                        <p className="text-sm text-muted-foreground italic">{t("noContactData")}</p>
                                    )}
                                </dl>
                            </div>

                            {/* Metricas rapidas */}
                            <div className="px-6 py-4 border-b border-border grid grid-cols-3 gap-3">
                                <KpiCard title={t("invoicesKpi")} value={clientInvoices.length} icon={FileText} />
                                <KpiCard
                                    title={t("billedKpi")}
                                    value={`${totalFacturado.toLocaleString("es-ES", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}€`}
                                />
                                <KpiCard
                                    title={t("createdColumn")}
                                    value={new Date(selectedClient.created_at).toLocaleDateString("es-ES", { day: "2-digit", month: "short", year: "numeric" })}
                                />
                            </div>

                            {/* Historial de facturas */}
                            <div className="px-6 py-5">
                                <div className="flex items-center justify-between mb-4">
                                    <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                                        <FileText className="h-3.5 w-3.5" /> {t("invoiceHistory")}
                                    </h3>
                                    <Button variant="outline" size="sm" asChild>
                                        <Link href={`/ventas/facturas/nueva?client_id=${selectedClient.id}`}>
                                            <Plus className="h-3 w-3 mr-1" /> {t("newInvoice")}
                                        </Link>
                                    </Button>
                                </div>

                                {loadingInvoices ? (
                                    <div className="flex items-center justify-center gap-2 py-8 text-muted-foreground text-sm">
                                        <Loader2 className="h-4 w-4 animate-spin" /> {tc("loading")}
                                    </div>
                                ) : clientInvoices.length === 0 ? (
                                    <EmptyState
                                        icon={FileText}
                                        title={t("noInvoices")}
                                        className="py-10"
                                    />
                                ) : (
                                    <div className="space-y-2">
                                        {clientInvoices.map((inv) => (
                                            <div key={inv.id} className="bg-muted rounded-xl border border-border hover:border-primary/30 transition p-4 flex items-center gap-3">
                                                <div className="flex-1 min-w-0">
                                                    <div className="flex items-center gap-2 mb-1">
                                                        <span className="text-sm font-medium text-foreground truncate">
                                                            {inv.invoice_number || t("draft")}
                                                        </span>
                                                        <StatusBadge status={inv.status} />
                                                    </div>
                                                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                                        <span>{new Date(inv.date).toLocaleDateString("es-ES", { day: "2-digit", month: "short", year: "numeric" })}</span>
                                                        {inv.lines && inv.lines.length > 0 && (
                                                            <span>· {inv.lines[0].description?.slice(0, 40)}{(inv.lines[0].description?.length ?? 0) > 40 ? "..." : ""}</span>
                                                        )}
                                                    </div>
                                                </div>
                                                <div className="text-right shrink-0">
                                                    <p className="text-sm font-semibold text-foreground tabular-nums">
                                                        {Number(inv.amount_total).toLocaleString("es-ES", { minimumFractionDigits: 2 })}€
                                                    </p>
                                                    <p className="text-[10px] text-muted-foreground">
                                                        {t("base")} {Number(inv.amount_base).toLocaleString("es-ES", { minimumFractionDigits: 2 })}€
                                                    </p>
                                                </div>
                                                <Button
                                                    variant="ghost"
                                                    size="icon"
                                                    onClick={() => downloadInvoicePdf(inv.id, inv.invoice_number, t("errorDownloadPdf"))}
                                                    title={t("downloadPdf")}
                                                    className="shrink-0"
                                                >
                                                    <Download className="h-4 w-4" />
                                                </Button>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* Footer del drawer */}
                        <div className="px-6 py-4 border-t border-border bg-background space-y-2">
                            <div className="flex gap-2">
                                <Button
                                    variant="outline"
                                    className="flex-1"
                                    onClick={() => openEditClient(selectedClient)}
                                >
                                    <FileText className="h-4 w-4 mr-2" />
                                    {t("editClient")}
                                </Button>
                                <Button
                                    variant="destructive"
                                    onClick={() => handleDeleteClient(selectedClient)}
                                    disabled={deleting}
                                >
                                    {deleting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <X className="h-4 w-4 mr-2" />}
                                    {tc("delete")}
                                </Button>
                            </div>
                            <Button variant="outline" className="w-full" asChild>
                                <Link href={`/clientes/${selectedClient.id}`}>
                                    <ExternalLink className="h-4 w-4 mr-2" />
                                    {t("viewFullHistory")}
                                </Link>
                            </Button>
                            <Button variant="ghost" className="w-full" asChild>
                                <Link href="/ventas/facturas">
                                    <ExternalLink className="h-4 w-4 mr-2" />
                                    {t("viewAllInvoices")}
                                </Link>
                            </Button>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
}
