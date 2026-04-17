"use client";

import { useEffect, useState, useCallback } from "react";
import { api, type RecurringInvoice, type Client, type RecurringLineItem } from "@/lib/api";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";
import { logError } from "@/lib/logger";
import { useTranslations } from "next-intl";

export const fmt = (n: number) => n.toLocaleString("es-ES", { style: "currency", currency: "EUR" });

export const INTERVAL_MAP: Record<string, string> = {
    weekly: "weekly",
    monthly: "monthly",
    quarterly: "quarterly",
    yearly: "yearly",
};

export const INTERVAL_COLORS: Record<string, string> = {
    weekly: "text-purple-400 bg-purple-500/10 border-purple-500/20",
    monthly: "text-blue-400 bg-blue-500/10 border-blue-500/20",
    quarterly: "text-amber-400 bg-amber-500/10 border-amber-500/20",
    yearly: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
};

const EMPTY_LINE: RecurringLineItem = { description: "", quantity: 1, unit_price: 0, tax_percentage: 21 };

export interface RecurringForm {
    client_id: string;
    name: string;
    interval_type: string;
    next_run_date: string;
    notes: string;
    lines: RecurringLineItem[];
}

export function useRecurrentes() {
    const toast = useToastStore();
    const t = useTranslations("ventas");
    const tc = useTranslations("common");

    const [recurrings, setRecurrings] = useState<RecurringInvoice[]>([]);
    const [clients, setClients] = useState<Client[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState("");
    const [showModal, setShowModal] = useState(false);
    const [editingId, setEditingId] = useState<string | null>(null);
    const [saving, setSaving] = useState(false);
    const [runningId, setRunningId] = useState<string | null>(null);
    const [deletingId, setDeletingId] = useState<string | null>(null);

    const [form, setForm] = useState<RecurringForm>({
        client_id: "",
        name: "",
        interval_type: "monthly",
        next_run_date: "",
        notes: "",
        lines: [{ ...EMPTY_LINE }],
    });

    const load = useCallback(async () => {
        try {
            const [recs, cls] = await Promise.all([
                api.erp.recurring.list(),
                api.erp.clients.list({ limit: 200 }),
            ]);
            setRecurrings(recs);
            setClients(cls.filter(c => c.client_type === "customer"));
        } catch (err) { logError("ventas/recurrentes/page", err); }
        finally { setLoading(false); }
    }, []);

    useEffect(() => { load(); }, [load]);

    const openNew = () => {
        setForm({ client_id: "", name: "", interval_type: "monthly", next_run_date: "", notes: "", lines: [{ ...EMPTY_LINE }] });
        setEditingId(null);
        setShowModal(true);
    };

    const openEdit = (rec: RecurringInvoice) => {
        setForm({
            client_id: rec.client_id,
            name: rec.name,
            interval_type: rec.interval_type,
            next_run_date: rec.next_run_date,
            notes: rec.notes || "",
            lines: rec.lines_json.length > 0 ? rec.lines_json : [{ ...EMPTY_LINE }],
        });
        setEditingId(rec.id);
        setShowModal(true);
    };

    const setLine = (i: number, field: keyof RecurringLineItem, value: any) => {
        setForm(f => { const lines = [...f.lines]; lines[i] = { ...lines[i], [field]: value }; return { ...f, lines }; });
    };

    const addLine = () => setForm(f => ({ ...f, lines: [...f.lines, { ...EMPTY_LINE }] }));
    const removeLine = (i: number) => setForm(f => ({ ...f, lines: f.lines.filter((_, idx) => idx !== i) }));

    const lineTotal = (line: RecurringLineItem) => line.quantity * line.unit_price * (1 + line.tax_percentage / 100);
    const totalAmount = form.lines.reduce((acc, l) => acc + lineTotal(l), 0);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!form.client_id || !form.name || !form.next_run_date) return;
        setSaving(true);
        try {
            const payload = {
                client_id: form.client_id,
                name: form.name,
                interval_type: form.interval_type,
                next_run_date: form.next_run_date,
                notes: form.notes || undefined,
                lines: form.lines.filter(l => l.description.trim()),
            };
            if (editingId) {
                await api.erp.recurring.update(editingId, payload as any);
            } else {
                await api.erp.recurring.create(payload as any);
            }
            setShowModal(false);
            setLoading(true);
            load();
        } catch (err) { logError("ventas/recurrentes/page", err); }
        finally { setSaving(false); }
    };

    const handleToggleActive = async (rec: RecurringInvoice) => {
        try {
            const updated = await api.erp.recurring.update(rec.id, { is_active: !rec.is_active } as any);
            setRecurrings(prev => prev.map(r => r.id === rec.id ? updated : r));
        } catch (err) { logError("ventas/recurrentes/page", err); }
    };

    const handleRun = async (rec: RecurringInvoice) => {
        if (!await showConfirm({ message: t("recurringRunConfirm", { name: rec.name }), confirmLabel: t("recurringGenerate"), confirmVariant: "primary" })) return;
        setRunningId(rec.id);
        try {
            await api.erp.recurring.run(rec.id);
            toast.success(t("recurringRunSuccess"));
            load();
        } catch (err: any) {
            toast.error(err?.message || t("recurringRunError"));
        } finally {
            setRunningId(null);
        }
    };

    const handleDelete = async (id: string) => {
        if (!await showConfirm({ message: t("recurringDeleteConfirm"), confirmLabel: tc("delete"), confirmVariant: "danger" })) return;
        setDeletingId(id);
        try {
            await api.erp.recurring.delete(id);
            setRecurrings(prev => prev.filter(r => r.id !== id));
        } catch (err) { logError("ventas/recurrentes/page", err); }
        finally { setDeletingId(null); }
    };

    const q = search.toLowerCase();
    const filtered = recurrings.filter(r => !q || r.name.toLowerCase().includes(q) || (r.client?.name || "").toLowerCase().includes(q));
    const dueToday = recurrings.filter(r => r.is_active && r.next_run_date <= new Date().toISOString().split("T")[0]).length;

    const estimatedMonthly = recurrings.filter(r => r.is_active).reduce((acc, r) => {
        const total = r.lines_json.reduce((s, l) => s + l.quantity * l.unit_price * (1 + l.tax_percentage / 100), 0);
        const factor = { weekly: 4.3, monthly: 1, quarterly: 1 / 3, yearly: 1 / 12 }[r.interval_type] || 1;
        return acc + total * factor;
    }, 0);

    return {
        recurrings, filtered, loading, search, setSearch,
        showModal, setShowModal, editingId, saving, runningId, deletingId,
        form, setForm, clients,
        setLine, addLine, removeLine, lineTotal, totalAmount,
        openNew, openEdit,
        handleSubmit, handleToggleActive, handleRun, handleDelete,
        dueToday, estimatedMonthly,
        t, tc,
    };
}
