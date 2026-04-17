"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { api, Client, Invoice } from "@/lib/api";
import { useNotificationStore } from "@/stores/notifications";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";

export function useClientes() {
    const t = useTranslations("clientes");
    const tc = useTranslations("common");
    const toast = useToastStore();

    const [clients, setClients] = useState<Client[]>([]);
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

    // ── Data loading ──────────────────────────────────────────────────────────

    const loadClients = useCallback(async () => {
        try {
            setLoading(true);
            const data = await api.erp.clients.list();
            setClients(data);
        } catch (err: any) {
            setError(err.message || t("errorLoading"));
        } finally {
            setLoading(false);
        }
    }, [t]);

    useEffect(() => { loadClients(); }, [refreshKey, loadClients]);

    // ── CRUD handlers ─────────────────────────────────────────────────────────

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

    const closeDrawer = () => {
        setSelectedClient(null);
        setClientInvoices([]);
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

    const openClientDrawer = useCallback(async (client: Client) => {
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
    }, []);

    const sendAiTask = async (suggestion: string) => {
        try {
            await api.tasks.create("crm", suggestion);
            toast.show(t("taskSent"), "info");
        } catch {
            toast.show(t("errorSendingTask"), "error");
        }
    };

    const openCreateModal = () => {
        setIsCreating(true);
    };

    const closeModal = () => {
        setIsCreating(false);
        setEditingClient(null);
        setNewClient({ client_type: "customer" });
    };

    return {
        // data
        clients,
        loading,
        error,
        // drawer
        selectedClient,
        clientInvoices,
        loadingInvoices,
        // modal
        isCreating,
        editingClient,
        newClient,
        setNewClient,
        saving,
        deleting,
        // handlers
        openCreateModal,
        handleCreateClient,
        openEditClient,
        handleDeleteClient,
        openClientDrawer,
        closeDrawer,
        closeModal,
        sendAiTask,
    };
}
