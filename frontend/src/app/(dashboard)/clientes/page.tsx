"use client";

import { useMemo } from "react";
import { useTranslations } from "next-intl";
import { ColumnDef } from "@tanstack/react-table";
import { Client } from "@/lib/api";
import Link from "next/link";

import { PageHeader, StatusBadge, FormModal, FormField, EmptyState } from "@/components/shared";
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
import { Plus, Building2, Eye } from "lucide-react";

import { useClientes } from "./_hooks/useClientes";
import { ClienteDrawer } from "./_components/ClienteDrawer";

// ── Helpers ───────────────────────────────────────────────────────────────────

function getInitials(name: string) {
    return name
        .split(/\s+/)
        .slice(0, 2)
        .map((w) => w[0])
        .join("")
        .toUpperCase();
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ClientesPage() {
    const t = useTranslations("clientes");

    const {
        clients, loading, error,
        selectedClient, clientInvoices, loadingInvoices,
        isCreating, editingClient, newClient, setNewClient, saving, deleting,
        openCreateModal, handleCreateClient, openEditClient, handleDeleteClient,
        openClientDrawer, closeDrawer, closeModal, sendAiTask,
    } = useClientes();

    const CLIENT_TYPE_MAP = useMemo<Record<string, { label: string; variant: "info" | "warning" | "default" | "success" }>>(() => ({
        customer: { label: t("typeClient"), variant: "info" },
        supplier: { label: t("typeSupplier"), variant: "warning" },
        company: { label: t("typeCompany"), variant: "default" },
        lead: { label: t("typeLead"), variant: "success" },
    }), [t]);

    const CLIENT_TYPE_OPTIONS = useMemo(() => [
        { label: t("typeClient"), value: "customer" },
        { label: t("typeSupplier"), value: "supplier" },
        { label: t("typeCompany"), value: "company" },
        { label: t("typeLead"), value: "lead" },
    ], [t]);

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
                <Button variant="ghost" size="sm" onClick={() => openClientDrawer(row.original)}>
                    <Eye className="h-4 w-4 mr-1" />
                    {t("view")}
                </Button>
            ),
        },
    ], [t, openClientDrawer, CLIENT_TYPE_MAP]);

    const facetedFilters = useMemo(() => [
        {
            column: "client_type",
            title: t("type"),
            options: CLIENT_TYPE_OPTIONS.map((o) => ({ label: o.label, value: o.value })),
        },
    ], [t, CLIENT_TYPE_OPTIONS]);

    // ── Render ────────────────────────────────────────────────────────────────

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
                    <Button onClick={openCreateModal}>
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
                            <Button onClick={openCreateModal}>
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
                                            onClick={() => sendAiTask(suggestion)}
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

            {/* FormModal: Create / Edit */}
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

            {/* Drawer lateral */}
            <ClienteDrawer
                selectedClient={selectedClient}
                clientInvoices={clientInvoices}
                loadingInvoices={loadingInvoices}
                deleting={deleting}
                clientTypeMap={CLIENT_TYPE_MAP}
                onClose={closeDrawer}
                onEdit={openEditClient}
                onDelete={handleDeleteClient}
            />
        </div>
    );
}
