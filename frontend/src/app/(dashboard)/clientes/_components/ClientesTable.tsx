"use client";

import { useMemo } from "react";
import { useTranslations } from "next-intl";
import { ColumnDef } from "@tanstack/react-table";
import { Client } from "@/lib/api";

import { StatusBadge } from "@/components/shared";
import { DataTable, DataTableColumnHeader } from "@/components/data-table";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Building2, Eye, Pencil, Trash2 } from "lucide-react";

import { getInitials, clientHealth, HEALTH_CONFIG, ClientTypeMap, ClientTypeOption } from "./clientHealth";

interface ClientesTableProps {
    clients: Client[];
    loading: boolean;
    deleting: boolean;
    clientTypeMap: ClientTypeMap;
    clientTypeOptions: ClientTypeOption[];
    openClientDrawer: (client: Client) => void;
    openEditClient: (client: Client) => void;
    handleDeleteClient: (client: Client) => void;
}

export function ClientesTable({
    clients,
    loading,
    deleting,
    clientTypeMap,
    clientTypeOptions,
    openClientDrawer,
    openEditClient,
    handleDeleteClient,
}: ClientesTableProps) {
    const t = useTranslations("clientes");

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
                const ct = clientTypeMap[row.original.client_type] ?? { label: row.original.client_type, variant: "default" as const };
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
                     aria-label={t("editClientAria")}>
                        <Pencil className="h-3.5 w-3.5" aria-hidden="true" />
                    </Button>
                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-red-400/60 hover:text-red-400 hover:bg-red-500/10"
                        onClick={() => handleDeleteClient(row.original)}
                        disabled={deleting}
                     aria-label={t("deleteClientAria")}>
                        <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                    </Button>
                </div>
            ),
        },
    ], [t, openClientDrawer, openEditClient, handleDeleteClient, deleting, clientTypeMap]);

    const facetedFilters = useMemo(() => [
        {
            column: "client_type",
            title: t("type"),
            options: clientTypeOptions.map((o) => ({ label: o.label, value: o.value })),
        },
    ], [t, clientTypeOptions]);

    return (
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
    );
}
