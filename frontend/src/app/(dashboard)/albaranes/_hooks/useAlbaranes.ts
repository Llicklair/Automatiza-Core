"use client";

import { useEffect, useState } from "react";
import { printTicket } from "@/lib/print/ticket";
import { getPrinterSettings } from "@/lib/print/printerSettings";
import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { getToken } from "@/lib/api/client";
import type { DeliveryNote, DeliveryNoteCreate } from "@/lib/api/albaranes";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";
import { logError } from "@/lib/logger";

export type LineForm = { description: string; quantity: string; unit_price: string; tax_percentage: string; product_id?: string | null };

export const emptyLine = (): LineForm => ({ description: "", quantity: "1", unit_price: "0", tax_percentage: "21" });

export const STATUS_COLORS: Record<string, string> = {
    draft:      "text-muted-foreground bg-muted border-border",
    confirmed:  "text-primary bg-primary/10 border-primary/20",
    recibido:   "text-sky-400 bg-sky-400/10 border-sky-400/20",
    en_proceso: "text-amber-400 bg-amber-400/10 border-amber-400/20",
    listo:      "text-violet-400 bg-violet-400/10 border-violet-400/20",
    delivered:  "text-emerald-400 bg-emerald-400/10 border-emerald-400/20",
    anulado:    "text-rose-400 bg-rose-400/10 border-rose-400/20",
};

export const fmt = (n: number) => n.toLocaleString("es-ES", { style: "currency", currency: "EUR" });

export function useAlbaranes() {
    const t = useTranslations("albaranes");
    const tc = useTranslations("common");
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
    // T8: id del albarán en edición (null = creando).
    const [editingId, setEditingId] = useState<string | null>(null);

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
        setEditingId(null);
    };

    // T8: precarga el modal con un albarán existente para editarlo.
    const openEdit = (a: DeliveryNote) => {
        setEditingId(a.id);
        setClientName(a.client_name ?? "");
        setDate(a.date.split("T")[0]);
        setNotes(a.notes ?? "");
        setLines(a.lines.length
            ? a.lines.map(l => ({
                description: l.description,
                quantity: String(l.quantity),
                unit_price: String(l.unit_price),
                tax_percentage: String(l.tax_percentage),
                product_id: l.product_id,
            }))
            : [emptyLine()]);
        setShowModal(true);
    };

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        const validLines = lines.filter(l => l.description.trim());
        if (!validLines.length) { toast.warning(t("toasts.needLine")); return; }
        setSaving(true);
        const mappedLines = validLines.map(l => ({
            product_id: l.product_id ?? undefined,
            description: l.description,
            quantity: parseFloat(l.quantity) || 1,
            unit_price: parseFloat(l.unit_price) || 0,
            tax_percentage: parseFloat(l.tax_percentage) || 21,
        }));
        try {
            if (editingId) {
                // client_name/notes van siempre: "" limpia el campo en el backend.
                await api.albaranes.update(editingId, { client_name: clientName, date, notes, lines: mappedLines });
                setShowModal(false); resetModal(); await loadData();
                toast.success(t("toasts.updated"));
            } else {
                const payload: DeliveryNoteCreate = {
                    client_name: clientName || undefined,
                    date,
                    notes: notes || undefined,
                    lines: mappedLines,
                };
                await api.albaranes.create(payload);
                setShowModal(false); resetModal(); await loadData();
                toast.success(t("toasts.created"));
            }
        } catch (e: unknown) {
            if (editingId) toast.error(e instanceof Error ? e.message : t("toasts.updateError"));
            else toast.error(t("toasts.createError", { error: e instanceof Error ? e.message : t("toasts.unknownError") }));
        }
        finally { setSaving(false); }
    };

    const handleDelete = async (id: string) => {
        const ok = await showConfirm({ title: t("delete.title"), message: t("delete.message"), confirmLabel: tc("delete"), cancelLabel: tc("cancel"), confirmVariant: "danger" });
        if (!ok) return;
        try { await api.albaranes.delete(id); setAlbaranes(prev => prev.filter(a => a.id !== id)); toast.success(t("toasts.deleted")); }
        catch (e: unknown) { toast.error(e instanceof Error ? e.message : t("toasts.unknownError")); }
    };

    const handleStatusChange = async (id: string, status: string) => {
        try {
            const updated = await api.albaranes.updateStatus(id, status);
            setAlbaranes(prev => prev.map(a => a.id === id ? updated : a));
        } catch (e: unknown) { toast.error(e instanceof Error ? e.message : t("toasts.unknownError")); }
    };

    // Ticket-resguardo 80 mm (tintorería): imprime en térmica o impresora normal.
    const handlePrintTicket = async (id: string) => {
        try {
            const html = await api.albaranes.ticketHtml(id);
            const settings = getPrinterSettings();
            await printTicket(html, { silent: false, deviceName: settings.deviceName });
        } catch (e) {
            console.error("albaranes/printTicket", e);
        }
    };

    // T7: factura agrupada de los albaranes seleccionados (mismo cliente).
    const handleFacturar = async (ids: string[]): Promise<boolean> => {
        try {
            const inv = await api.albaranes.facturar(ids);
            toast.success(t("toasts.facturarOk", { number: inv.invoice_number ?? inv.id.slice(0, 8) }));
            await loadData();
            return true;
        } catch (e) {
            toast.error(e instanceof Error ? e.message : t("toasts.facturarError"));
            return false;
        }
    };

    const handleDownloadPdf = (id: string) => {
        const token = getToken();
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

    // Buscador del mostrador (T4): número, cliente, NIF/DNI, teléfono o email.
    // El teléfono se compara solo por dígitos ("612 34 56" encuentra "612345678").
    const q = search.trim().toLowerCase();
    const qDigits = q.replace(/\D/g, "");
    const filtered = albaranes.filter(a => {
        const matchSearch = !q
            || a.albaran_number.toLowerCase().includes(q)
            || (a.client_name ?? "").toLowerCase().includes(q)
            || (a.client_nif ?? "").toLowerCase().includes(q)
            || (a.client_email ?? "").toLowerCase().includes(q)
            || (qDigits.length >= 3 && (a.client_phone ?? "").replace(/\D/g, "").includes(qDigits));
        const matchStatus = !filterStatus || a.status === filterStatus;
        return matchSearch && matchStatus;
    });

    return {
        albaranes, loading, search, setSearch, filterStatus, setFilterStatus,
        showModal, setShowModal, saving,
        clientName, setClientName, date, setDate, notes, setNotes, lines, setLines,
        resetModal, handleCreate, handleDelete, handleStatusChange, handleDownloadPdf, handleConvertToInvoice, handlePrintTicket,
        handleFacturar,
        openEdit, editingId,
        reload: loadData,
        filtered,
    };
}
