"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { DeliveryNote, DeliveryNoteCreate } from "@/lib/api/albaranes";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";
import { logError } from "@/lib/logger";

export type LineForm = { description: string; quantity: string; unit_price: string; tax_percentage: string };

export const emptyLine = (): LineForm => ({ description: "", quantity: "1", unit_price: "0", tax_percentage: "21" });

export const STATUS_LABELS: Record<string, { label: string; color: string }> = {
    draft:     { label: "Borrador",   color: "text-muted-foreground bg-muted border-border" },
    confirmed: { label: "Confirmado", color: "text-primary bg-primary/10 border-primary/20" },
    delivered: { label: "Entregado",  color: "text-emerald-400 bg-emerald-400/10 border-emerald-400/20" },
};

export const fmt = (n: number) => n.toLocaleString("es-ES", { style: "currency", currency: "EUR" });

export function useAlbaranes() {
    const toast = useToastStore();
    const router = useRouter();
    const [albaranes, setAlbaranes] = useState<DeliveryNote[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState("");
    const [filterStatus, setFilterStatus] = useState("");
    const [showModal, setShowModal] = useState(false);
    const [saving, setSaving] = useState(false);
    const [clientName, setClientName] = useState("");
    const [date, setDate] = useState(new Date().toISOString().split("T")[0]);
    const [notes, setNotes] = useState("");
    const [lines, setLines] = useState<LineForm[]>([emptyLine(), emptyLine()]);

    const loadData = async () => {
        setLoading(true);
        try { setAlbaranes(await api.albaranes.list()); }
        catch (e) { logError("albaranes/page", e); }
        finally { setLoading(false); }
    };

    useEffect(() => { loadData(); }, []);

    const resetModal = () => {
        setClientName(""); setDate(new Date().toISOString().split("T")[0]);
        setNotes(""); setLines([emptyLine(), emptyLine()]);
    };

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        const validLines = lines.filter(l => l.description.trim());
        if (!validLines.length) { toast.warning("Añade al menos una línea con descripción."); return; }
        setSaving(true);
        try {
            const payload: DeliveryNoteCreate = {
                client_name: clientName || undefined,
                date,
                notes: notes || undefined,
                lines: validLines.map(l => ({
                    description: l.description,
                    quantity: parseFloat(l.quantity) || 1,
                    unit_price: parseFloat(l.unit_price) || 0,
                    tax_percentage: parseFloat(l.tax_percentage) || 21,
                })),
            };
            await api.albaranes.create(payload);
            setShowModal(false); resetModal(); await loadData();
            toast.success("Albarán creado correctamente");
        } catch (e: unknown) { toast.error("Error creando albarán: " + (e instanceof Error ? e.message : "Error desconocido")); }
        finally { setSaving(false); }
    };

    const handleDelete = async (id: string) => {
        const ok = await showConfirm({ title: "Eliminar albarán", message: "¿Eliminar este albarán? Esta acción no se puede deshacer.", confirmLabel: "Eliminar", cancelLabel: "Cancelar", confirmVariant: "danger" });
        if (!ok) return;
        try { await api.albaranes.delete(id); setAlbaranes(prev => prev.filter(a => a.id !== id)); toast.success("Albarán eliminado"); }
        catch (e: unknown) { toast.error(e instanceof Error ? e.message : "Error desconocido"); }
    };

    const handleStatusChange = async (id: string, status: string) => {
        try {
            const updated = await api.albaranes.updateStatus(id, status);
            setAlbaranes(prev => prev.map(a => a.id === id ? updated : a));
        } catch (e: unknown) { toast.error(e instanceof Error ? e.message : "Error desconocido"); }
    };

    const handleDownloadPdf = (id: string) => {
        const token = localStorage.getItem("access_token");
        const base = process.env.NEXT_PUBLIC_API_URL || "";
        const url = `${base}${api.albaranes.pdfUrl(id)}`;
        const a = document.createElement("a");
        a.href = url;
        a.target = "_blank";
        if (token) a.href = url + `?token=${token}`;
        a.click();
    };

    const handleConvertToInvoice = (albaran: DeliveryNote) => {
        router.push(`/ventas/facturas/nueva?from_albaran=${albaran.id}`);
    };

    const filtered = albaranes.filter(a => {
        const matchSearch = !search || a.albaran_number.toLowerCase().includes(search.toLowerCase());
        const matchStatus = !filterStatus || a.status === filterStatus;
        return matchSearch && matchStatus;
    });

    return {
        albaranes, loading, search, setSearch, filterStatus, setFilterStatus,
        showModal, setShowModal, saving,
        clientName, setClientName, date, setDate, notes, setNotes, lines, setLines,
        resetModal, handleCreate, handleDelete, handleStatusChange, handleDownloadPdf, handleConvertToInvoice,
        filtered,
    };
}
