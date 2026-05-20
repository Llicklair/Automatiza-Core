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

    const handleScan = useCallback(async (file: File) => {
        try {
            const draft = await api.erp.invoices.scan(file);

            const nif = (draft.emisor?.nif || "").trim().toUpperCase();
            let supplier = nif
                ? clients.find(c => (c.nif || "").trim().toUpperCase() === nif)
                : undefined;

            if (!supplier && draft.emisor?.name) {
                try {
                    supplier = await api.erp.clients.create({
                        name: draft.emisor.name,
                        nif: nif || undefined,
                        address: draft.emisor.address ?? undefined,
                        city: draft.emisor.city ?? undefined,
                        postal_code: draft.emisor.postal_code ?? undefined,
                        client_type: "supplier",
                    } as any);
                    setClients(prev => [...prev, supplier!]);
                    toast.info(`Proveedor creado: ${supplier.name}`);
                } catch {
                    // si falla por duplicado u otro motivo, caemos al modal
                }
            }

            const lines = (draft.lines || []).map(ln => ({
                description: ln.description || "Concepto",
                quantity: ln.quantity || 1,
                unit_price: ln.unit_price || 0,
                discount_percentage: 0,
                tax_percentage: ln.tax_percentage ?? 21,
            }));

            if (supplier && lines.length > 0) {
                const inv = await api.erp.invoices.create(supplier.id, {
                    invoice_number: draft.invoice_number || null,
                    date: new Date(draft.issue_date).toISOString(),
                    due_date: draft.due_date ? new Date(draft.due_date).toISOString() : null,
                    status: "pending",
                    invoice_type: "received",
                    lines,
                } as any);
                setInvoices(prev => [inv, ...prev]);
                const conf = Math.round((draft.confidence ?? 0.5) * 100);
                toast.success(
                    `Factura registrada: ${draft.emisor.name} · ${draft.amount_total.toFixed(2)} € (confianza ${conf}%)`,
                );
                draft.warnings?.forEach(w => toast.warning(w));
            } else {
                if (supplier) { setSupplierId(supplier.id); setUseExisting(true); }
                else { setSupplierName(draft.emisor?.name || ""); setUseExisting(false); }
                setInvoiceNumber(draft.invoice_number || "");
                setAmount(draft.amount_base.toFixed(2));
                setTaxPct(String(lines[0]?.tax_percentage ?? 21));
                setDate(draft.issue_date.slice(0, 10));
                setDueDate(draft.due_date ? draft.due_date.slice(0, 10) : "");
                setShowModal(true);
                toast.info("Revisa los datos antes de confirmar");
            }
        } catch (err: any) {
            toast.error(err?.message || "No se pudo leer la factura");
        }
    }, [clients, toast]);

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
        resetModal, handleRegister, handleScan, handleStatusChange, handleDeleteInvoice,
    };
}
