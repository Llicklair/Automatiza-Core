"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { api, type Client, type Invoice } from "@/lib/api";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";

const today = () => new Date().toISOString().slice(0, 10);

export function useFacturasRecibidas() {
    const toast = useToastStore();
    const [invoices, setInvoices] = useState<Invoice[]>([]);
    const [clients, setClients]   = useState<Client[]>([]);
    const [loading, setLoading]   = useState(true);

    // Modal state
    const [showModal, setShowModal]       = useState(false);
    const [supplierId, setSupplierId]     = useState("");
    const [supplierName, setSupplierName] = useState("");
    const [useExisting, setUseExisting]   = useState(true);
    const [invoiceNumber, setInvoiceNumber] = useState("");
    const [amount, setAmount]             = useState("");
    const [taxPct, setTaxPct]             = useState("21");
    const [date, setDate]                 = useState(today());
    const [dueDate, setDueDate]           = useState("");
    const [invStatus, setInvStatus]       = useState("pending");
    const [submitting, setSubmitting]     = useState(false);

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

    const resetModal = () => {
        setSupplierId(""); setSupplierName(""); setUseExisting(true);
        setInvoiceNumber(""); setAmount(""); setTaxPct("21");
        setDate(today()); setDueDate(""); setInvStatus("pending");
    };

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
                lines: [{ description: "Factura recibida", quantity: 1, unit_price: baseAmount, discount_percentage: 0, tax_percentage: parseFloat(taxPct) }],
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
            confirmVariant: "danger", confirmLabel: "Eliminar",
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

    return {
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
        submitting,
        totalPendiente, totalPagado30,
        resetModal, handleRegister, handleStatusChange, handleDeleteInvoice,
    };
}
