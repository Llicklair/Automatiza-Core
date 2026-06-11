"use client";

import { useMemo, useState } from "react";
import { useTranslations } from "next-intl";

import { PageHeader } from "@/components/shared";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/button";
import { Plus, Building2, LayoutGrid, List, Upload } from "lucide-react";

import { useClientes } from "./_hooks/useClientes";
import { ClienteDrawer } from "./_components/ClienteDrawer";
import { ClientesTable } from "./_components/ClientesTable";
import { ClientesCardGrid } from "./_components/ClientesCardGrid";
import { ClientesEmptyState } from "./_components/ClientesEmptyState";
import { ClienteFormModal } from "./_components/ClienteFormModal";
import { ClientesImportModal } from "./_components/ClientesImportModal";
import { ClientTypeMap } from "./_components/clientHealth";
import { PageContainer } from "@/components/shared/PageContainer";

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
    const [showImport, setShowImport] = useState(false);

    const CLIENT_TYPE_MAP = useMemo<ClientTypeMap>(() => ({
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

    // ── Render ────────────────────────────────────────────────────────────────

    if (error && !loading) {
        return (
            <PageContainer width="7xl">
                <EmptyState icon={Building2} title={t("errorLoading")} description={error} />
            </PageContainer>
        );
    }

    return (
        <PageContainer width="7xl" className="relative">
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
                             aria-label="Vista tabla">
                                <List className="h-3.5 w-3.5" aria-hidden="true" />
                            </Button>
                            <Button
                                variant={viewMode === "cards" ? "secondary" : "ghost"}
                                size="icon"
                                className="h-7 w-7"
                                onClick={() => setViewMode("cards")}
                                title="Vista tarjetas"
                             aria-label="Vista tarjetas">
                                <LayoutGrid className="h-3.5 w-3.5" aria-hidden="true" />
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
                <ClientesEmptyState openCreateModal={openCreateModal} sendAiTask={sendAiTask} />
            ) : viewMode === "table" ? (
                <ClientesTable
                    clients={clients}
                    loading={loading}
                    deleting={deleting}
                    clientTypeMap={CLIENT_TYPE_MAP}
                    clientTypeOptions={CLIENT_TYPE_OPTIONS}
                    openClientDrawer={openClientDrawer}
                    openEditClient={openEditClient}
                    handleDeleteClient={handleDeleteClient}
                />
            ) : (
                <ClientesCardGrid
                    clients={clients}
                    deleting={deleting}
                    clientTypeMap={CLIENT_TYPE_MAP}
                    openClientDrawer={openClientDrawer}
                    openEditClient={openEditClient}
                    handleDeleteClient={handleDeleteClient}
                />
            )}

            {/* FormModal: Create / Edit */}
            <ClienteFormModal
                isCreating={isCreating}
                editingClient={editingClient}
                newClient={newClient}
                setNewClient={setNewClient}
                saving={saving}
                clientTypeOptions={CLIENT_TYPE_OPTIONS}
                closeModal={closeModal}
                handleCreateClient={handleCreateClient}
            />

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

            <ClientesImportModal open={showImport} onClose={() => setShowImport(false)} />
        </PageContainer>
    );
}
