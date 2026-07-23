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

export type LineForm = { description: string; quantity: string; unit_price: string; tax_percentage: string };

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
        if (!validLines.length) { toast.warning(t("toasts.needLine")); return; }
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
            toast.success(t("toasts.created"));
        } catch (e: unknown) { toast.error(t("toasts.createError", { error: e instanceof Error ? e.message : t("toasts.unknownError") })); }
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

    const filtered = albaranes.filter(a => {
        const matchSearch = !search || a.albaran_number.toLowerCase().includes(search.toLowerCase());
        const matchStatus = !filterStatus || a.status === filterStatus;
        return matchSearch && matchStatus;
    });

    return {
        albaranes, loading, search, setSearch, filterStatus, setFilterStatus,
        showModal, setShowModal, saving,
        clientName, setClientName, date, setDate, notes, setNotes, lines, setLines,
        resetModal, handleCreate, handleDelete, handleStatusChange, handleDownloadPdf, handleConvertToInvoice, handlePrintTicket,
        handleFacturar,
        reload: loadData,
        filtered,
    };
}
