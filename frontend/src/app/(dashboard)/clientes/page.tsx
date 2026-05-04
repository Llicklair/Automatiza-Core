"use client";

import { useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { ColumnDef } from "@tanstack/react-table";
import { Client } from "@/lib/api";

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
import { Plus, Building2, Eye, Pencil, Trash2, LayoutGrid, List, Mail, Phone, Upload } from "lucide-react";

import { useClientes } from "./_hooks/useClientes";
import { ClienteDrawer } from "./_components/ClienteDrawer";
import { ImportCsvModal } from "@/components/shared/ImportCsvModal";
import { api } from "@/lib/api";

// ── Helpers ───────────────────────────────────────────────────────────────────

function getInitials(name: string) {
    return name.split(/\s+/).slice(0, 2).map((w) => w[0]).join("").toUpperCase();
}

type HealthLevel = "complete" | "partial" | "incomplete";

function clientHealth(c: Client): HealthLevel {
    const hasContact = !!(c.email || c.phone);
    const hasNif = !!c.nif;
    if (hasContact && hasNif) return "complete";
    if (hasContact || hasNif) return "partial";
    return "incomplete";
}

const HEALTH_CONFIG: Record<HealthLevel, { dot: string; ring: string; label: string }> = {
    complete:   { dot: "bg-emerald-400", ring: "ring-emerald-400/30", label: "Datos completos" },
    partial:    { dot: "bg-amber-400",   ring: "ring-amber-400/30",   label: "Datos parciales" },
    incomplete: { dot: "bg-red-400",     ring: "ring-red-400/30",     label: "Sin contacto" },
};

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

    const [viewMode, setViewMode] = useState<"table" | "cards">("table");
    const [cardSearch, setCardSearch] = useState("");
    const [showImport, setShowImport] = useState(false);

    const CLIENT_TYPE_MAP = useMemo<Record<string, { label: string; variant: "info" | "warning" | "default" | "success" }>>(() => ({
        customer: { label: t("typeClient"),   variant: "info" },
        supplier: { label: t("typeSupplier"), variant: "warning" },
        company:  { label: t("typeCompany"),  variant: "default" },
        lead:     { label: t("typeLead"),     variant: "success" },
    }), [t]);

    const CLIENT_TYPE_OPTIONS = useMemo(() => [
        { label: t("typeClient"),   value: "customer" },
        { label: t("typeSupplier"), value: "supplier" },
        { label: t("typeCompany"),  value: "company" },
        { label: t("typeLead"),     value: "lead" },
    ], [t]);

    const filteredForCards = useMemo(() => {
        if (!cardSearch.trim()) return clients;
        const q = cardSearch.toLowerCase();
        return clients.filter(c =>
            c.name.toLowerCase().includes(q) ||
            c.email?.toLowerCase().includes(q) ||
            c.nif?.toLowerCase().includes(q)
        );
    }, [clients, cardSearch]);

    const columns = useMemo<ColumnDef<Client>[]>(() => [
        {
            accessorKey: "name",
            header: ({ column }) => <DataTableColumnHeader column={column} title={t("nameColumn")} />,
            cell: ({ row }) => {
                const client = row.original;
                const h = clientHealth(client);
                const cfg = HEALTH_CONFIG[h];
                return (
                    <div className="flex items-center gap-3 min-w-0">
                        <div className="relative shrink-0">
                            <Avatar className="h-8 w-8 rounded-lg">
                                <AvatarFallback className="rounded-lg bg-primary/10 text-primary text-xs font-semibold">
                                    {client.client_type === "company" || client.client_type === "supplier"
                                        ? <Building2 className="h-4 w-4" />
                                        : getInitials(client.name)
                                    }
                                </AvatarFallback>
                            </Avatar>
                            <span
                                className={`absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full border-2 border-card ${cfg.dot}`}
                                title={cfg.label}
                            />
                        </div>
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
                <div className="flex items-center gap-1">
                    <Button variant="ghost" size="sm" onClick={() => openClientDrawer(row.original)}>
                        <Eye className="h-4 w-4 mr-1" />
                        {t("view")}
                    </Button>
                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-muted-foreground hover:text-foreground"
                        onClick={() => openEditClient(row.original)}
                    >
                        <Pencil className="h-3.5 w-3.5" />
                    </Button>
                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-red-400/60 hover:text-red-400 hover:bg-red-500/10"
                        onClick={() => handleDeleteClient(row.original)}
                        disabled={deleting}
                    >
                        <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                </div>
            ),
        },
    ], [t, openClientDrawer, openEditClient, handleDeleteClient, deleting, CLIENT_TYPE_MAP]);

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
                    <div className="flex items-center gap-2">
                        {/* View toggle */}
                        <div className="flex items-center rounded-lg border border-border bg-card p-0.5 gap-0.5">
                            <Button
                                variant={viewMode === "table" ? "secondary" : "ghost"}
                                size="icon"
                                className="h-7 w-7"
                                onClick={() => setViewMode("table")}
                                title="Vista tabla"
                            >
                                <List className="h-3.5 w-3.5" />
                            </Button>
                            <Button
                                variant={viewMode === "cards" ? "secondary" : "ghost"}
                                size="icon"
                                className="h-7 w-7"
                                onClick={() => setViewMode("cards")}
                                title="Vista tarjetas"
                            >
                                <LayoutGrid className="h-3.5 w-3.5" />
                            </Button>
                        </div>
                        <Button variant="outline" size="sm" onClick={() => setShowImport(true)}>
                            <Upload className="h-4 w-4 mr-2" /> Importar CSV
                        </Button>
                        <Button onClick={openCreateModal}>
                            <Plus className="h-4 w-4 mr-2" />
                            {t("newClient")}
                        </Button>
                    </div>
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
                                    {[t("aiSuggestion1"), t("aiSuggestion2"), t("aiSuggestion3")].map((suggestion) => (
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
            ) : viewMode === "table" ? (
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
            ) : (
                /* ── Card view ────────────────────────────────────────── */
                <div className="space-y-4">
                    {/* Search for card mode */}
                    <Input
                        placeholder={t("searchPlaceholder")}
                        value={cardSearch}
                        onChange={(e) => setCardSearch(e.target.value)}
                        className="max-w-sm"
                    />

                    {/* Health legend */}
                    <div className="flex items-center gap-4 text-xs text-muted-foreground">
                        {(Object.entries(HEALTH_CONFIG) as [HealthLevel, typeof HEALTH_CONFIG[HealthLevel]][]).map(([, cfg]) => (
                            <div key={cfg.label} className="flex items-center gap-1.5">
                                <span className={`w-2 h-2 rounded-full ${cfg.dot}`} />
                                {cfg.label}
                            </div>
                        ))}
                    </div>

                    {filteredForCards.length === 0 ? (
                        <p className="text-sm text-muted-foreground py-8 text-center">{t("noMatchFilter")}</p>
                    ) : (
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                            {filteredForCards.map((client) => {
                                const h = clientHealth(client);
                                const cfg = HEALTH_CONFIG[h];
                                const ct = CLIENT_TYPE_MAP[client.client_type];
                                return (
                                    <div
                                        key={client.id}
                                        className="bg-card border border-border rounded-2xl p-5 flex flex-col gap-3 hover:border-primary/30 transition-colors group"
                                    >
                                        {/* Top row */}
                                        <div className="flex items-start justify-between gap-2">
                                            <div className="flex items-center gap-3 min-w-0">
                                                <div className={`relative shrink-0 w-10 h-10 rounded-xl bg-primary/10 border border-primary/20 ring-2 ${cfg.ring} flex items-center justify-center`}>
                                                    {client.client_type === "company" || client.client_type === "supplier"
                                                        ? <Building2 className="h-4 w-4 text-primary" />
                                                        : <span className="text-xs font-bold text-primary">{getInitials(client.name)}</span>
                                                    }
                                                    <span className={`absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full border-2 border-card ${cfg.dot}`} title={cfg.label} />
                                                </div>
                                                <div className="min-w-0">
                                                    <p className="text-sm font-semibold text-foreground truncate">{client.name}</p>
                                                    {client.city && <p className="text-xs text-muted-foreground truncate">{client.city}</p>}
                                                </div>
                                            </div>
                                            {ct && <StatusBadge status={client.client_type} label={ct.label} />}
                                        </div>

                                        {/* Contact info */}
                                        <div className="space-y-1.5 min-h-[40px]">
                                            {client.email ? (
                                                <div className="flex items-center gap-2 text-xs text-muted-foreground truncate">
                                                    <Mail className="h-3 w-3 shrink-0" />
                                                    <span className="truncate">{client.email}</span>
                                                </div>
                                            ) : null}
                                            {client.phone ? (
                                                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                                    <Phone className="h-3 w-3 shrink-0" />
                                                    <span>{client.phone}</span>
                                                </div>
                                            ) : null}
                                            {!client.email && !client.phone && (
                                                <p className="text-xs text-red-400/70 italic">Sin datos de contacto</p>
                                            )}
                                        </div>

                                        {/* NIF */}
                                        {client.nif && (
                                            <span className="text-xs font-mono bg-muted border border-border text-muted-foreground px-2 py-0.5 rounded w-fit">
                                                {client.nif}
                                            </span>
                                        )}

                                        {/* Actions */}
                                        <div className="flex items-center gap-1 pt-1 border-t border-border mt-auto">
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                className="flex-1 text-xs h-7"
                                                onClick={() => openClientDrawer(client)}
                                            >
                                                <Eye className="h-3 w-3 mr-1" />
                                                {t("view")}
                                            </Button>
                                            <Button
                                                variant="ghost"
                                                size="icon"
                                                className="h-7 w-7 text-muted-foreground hover:text-foreground"
                                                onClick={() => openEditClient(client)}
                                            >
                                                <Pencil className="h-3 w-3" />
                                            </Button>
                                            <Button
                                                variant="ghost"
                                                size="icon"
                                                className="h-7 w-7 text-red-400/60 hover:text-red-400 hover:bg-red-500/10"
                                                onClick={() => handleDeleteClient(client)}
                                                disabled={deleting}
                                            >
                                                <Trash2 className="h-3 w-3" />
                                            </Button>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>
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

            <ImportCsvModal
                open={showImport}
                onClose={() => setShowImport(false)}
                entityName="clientes"
                columns={[
                    { header: "Nombre", field: "nombre", required: true, example: "Acme S.L." },
                    { header: "NIF", field: "nif", example: "B12345678" },
                    { header: "Email", field: "email", example: "contacto@acme.com" },
                    { header: "Teléfono", field: "telefono", example: "91 234 56 78" },
                    { header: "Dirección", field: "direccion", example: "Calle Mayor 1" },
                    { header: "Ciudad", field: "ciudad", example: "Madrid" },
                    { header: "Código postal", field: "codigo_postal", example: "28001" },
                    { header: "Tipo", field: "tipo", example: "customer" },
                ]}
                onImport={(rows) => api.importBulk.clients(rows)}
                onSuccess={() => window.location.reload()}
            />
        </div>
    );
}
