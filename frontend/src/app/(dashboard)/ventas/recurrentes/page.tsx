"use client";

import { useEffect, useState } from "react";
import { api, type RecurringInvoice, type Client, type RecurringLineItem } from "@/lib/api";
import {
    RefreshCw, Plus, Search, Loader2, X, Pencil, Trash2,
    Play, Pause, CheckCircle2, Calendar, AlertCircle
} from "lucide-react";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";
import { logError } from "@/lib/logger";
import { useTranslations } from "next-intl";

const fmt = (n: number) => n.toLocaleString("es-ES", { style: "currency", currency: "EUR" });

const INTERVAL_MAP: Record<string, string> = {
    weekly: "weekly",
    monthly: "monthly",
    quarterly: "quarterly",
    yearly: "yearly",
};

const INTERVAL_COLORS: Record<string, string> = {
    weekly: "text-purple-400 bg-purple-500/10 border-purple-500/20",
    monthly: "text-blue-400 bg-blue-500/10 border-blue-500/20",
    quarterly: "text-amber-400 bg-amber-500/10 border-amber-500/20",
    yearly: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
};

const EMPTY_LINE: RecurringLineItem = { description: "", quantity: 1, unit_price: 0, tax_percentage: 21 };

export default function RecurrentesPage() {
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

    const [form, setForm] = useState({
        client_id: "",
        name: "",
        interval_type: "monthly",
        next_run_date: "",
        notes: "",
        lines: [{ ...EMPTY_LINE }] as RecurringLineItem[],
    });

    const load = async () => {
        try {
            const [recs, cls] = await Promise.all([
                api.erp.recurring.list(),
                api.erp.clients.list({ limit: 200 }),
            ]);
            setRecurrings(recs);
            setClients(cls.filter(c => c.client_type === "customer"));
        } catch (err) { logError("ventas/recurrentes/page", err); }
        finally { setLoading(false); }
    };

    useEffect(() => { load(); }, []);

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

    return (
        <div className="p-8 max-w-6xl mx-auto space-y-8">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-foreground tracking-tight">{t("recurring")}</h1>
                    <p className="mt-1 text-sm text-muted-foreground">{t("recurringDescription")}</p>
                </div>
                <button onClick={openNew} className="flex items-center gap-2 bg-primary hover:bg-primary text-foreground text-sm font-medium px-4 py-2.5 rounded-xl transition-colors">
                    <Plus className="w-4 h-4" /> {t("newRecurring")}
                </button>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-3 gap-4">
                <div className="bg-card border border-border rounded-2xl p-5">
                    <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">{t("recurringActiveTemplates")}</p>
                    <p className="text-2xl font-bold text-foreground">{recurrings.filter(r => r.is_active).length}</p>
                </div>
                <div className={`rounded-2xl p-5 border ${dueToday > 0 ? "bg-amber-500/10 border-amber-500/20" : "bg-card border-border"}`}>
                    <p className={`text-xs uppercase tracking-wider mb-1 ${dueToday > 0 ? "text-amber-400" : "text-muted-foreground"}`}>{t("recurringDueToday")}</p>
                    <p className={`text-2xl font-bold ${dueToday > 0 ? "text-amber-400" : "text-foreground"}`}>{dueToday}</p>
                </div>
                <div className="bg-card border border-border rounded-2xl p-5">
                    <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">{t("recurringEstimatedMonthly")}</p>
                    <p className="text-xl font-bold text-emerald-400">
                        {fmt(recurrings.filter(r => r.is_active).reduce((acc, r) => {
                            const total = r.lines_json.reduce((s, l) => s + l.quantity * l.unit_price * (1 + l.tax_percentage / 100), 0);
                            const factor = { weekly: 4.3, monthly: 1, quarterly: 1 / 3, yearly: 1 / 12 }[r.interval_type] || 1;
                            return acc + total * factor;
                        }, 0))}
                    </p>
                </div>
            </div>

            {dueToday > 0 && (
                <div className="flex items-center gap-3 bg-amber-500/10 border border-amber-500/20 rounded-xl p-4">
                    <AlertCircle className="w-5 h-5 text-amber-400 flex-shrink-0" />
                    <p className="text-sm text-amber-300">
                        {t("recurringDueWarning", { count: dueToday })}
                    </p>
                </div>
            )}

            {/* Search */}
            <div className="relative">
                <Search className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
                <input type="text" placeholder={t("recurringSearchPlaceholder")} value={search} onChange={e => setSearch(e.target.value)}
                    className="w-full bg-card border border-border text-foreground text-sm rounded-xl pl-9 pr-4 py-2.5 focus:outline-none focus:border-primary transition-colors" />
            </div>

            {/* List */}
            {loading ? (
                <div className="flex items-center justify-center py-24 text-muted-foreground gap-2">
                    <Loader2 className="w-5 h-5 animate-spin" /> {tc("loading")}
                </div>
            ) : filtered.length === 0 ? (
                <div className="bg-card border border-border rounded-2xl p-16 flex flex-col items-center text-center">
                    <RefreshCw className="w-12 h-12 text-muted-foreground mb-4" />
                    <h2 className="text-lg font-bold text-foreground mb-2">{recurrings.length === 0 ? t("recurringEmptyTitle") : tc("noResults")}</h2>
                    <p className="text-sm text-muted-foreground max-w-sm">
                        {recurrings.length === 0
                            ? t("recurringEmptyDescription")
                            : t("recurringNoResults", { search })}
                    </p>
                    {recurrings.length === 0 && (
                        <button onClick={openNew} className="mt-6 bg-primary hover:bg-primary text-foreground text-sm px-4 py-2 rounded-xl transition-colors">{t("createTemplate")}</button>
                    )}
                </div>
            ) : (
                <div className="bg-card border border-border rounded-2xl overflow-hidden">
                    <div className="grid grid-cols-12 gap-4 px-6 py-3 border-b border-border text-xs font-medium text-muted-foreground uppercase tracking-wide bg-muted">
                        <div className="col-span-3">{t("templateName")}</div>
                        <div className="col-span-2">{t("client")}</div>
                        <div className="col-span-2">{t("intervalType")}</div>
                        <div className="col-span-2">{t("nextIssue")}</div>
                        <div className="col-span-1 text-right">{t("recurringAmount")}</div>
                        <div className="col-span-2 text-right">{t("recurringActions")}</div>
                    </div>
                    {filtered.map(rec => {
                        const totalRec = rec.lines_json.reduce((acc, l) => acc + l.quantity * l.unit_price * (1 + l.tax_percentage / 100), 0);
                        const isDue = rec.is_active && rec.next_run_date <= new Date().toISOString().split("T")[0];
                        const intervalCls = INTERVAL_COLORS[rec.interval_type] || "text-muted-foreground bg-muted border-border";

                        return (
                            <div key={rec.id} className="grid grid-cols-12 gap-4 px-6 py-4 border-b border-border/50 last:border-0 hover:bg-accent/50 transition-colors items-center">
                                <div className="col-span-3 flex items-center gap-3">
                                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${rec.is_active ? "bg-primary/10 border border-primary/20" : "bg-muted border border-border"}`}>
                                        <RefreshCw className={`w-4 h-4 ${rec.is_active ? "text-primary" : "text-muted-foreground"}`} />
                                    </div>
                                    <div>
                                        <p className={`text-sm font-medium ${rec.is_active ? "text-foreground" : "text-muted-foreground"}`}>{rec.name}</p>
                                        {!rec.is_active && <p className="text-xs text-muted-foreground">{t("recurringPaused")}</p>}
                                    </div>
                                </div>
                                <div className="col-span-2">
                                    <p className="text-sm text-foreground truncate">{rec.client?.name || "—"}</p>
                                </div>
                                <div className="col-span-2">
                                    <span className={`text-xs px-2 py-1 rounded-full border ${intervalCls}`}>
                                        {INTERVAL_MAP[rec.interval_type] || rec.interval_type}
                                    </span>
                                </div>
                                <div className="col-span-2">
                                    <div className="flex items-center gap-1.5">
                                        <Calendar className={`w-3 h-3 ${isDue ? "text-amber-400" : "text-muted-foreground"}`} />
                                        <span className={`text-sm ${isDue ? "text-amber-400 font-medium" : "text-muted-foreground"}`}>
                                            {new Date(rec.next_run_date).toLocaleDateString("es-ES")}
                                        </span>
                                        {isDue && <span className="text-xs bg-amber-500/20 text-amber-400 px-1.5 py-0.5 rounded-md border border-amber-500/30">{t("recurringOverdue")}</span>}
                                    </div>
                                    {rec.last_run_date && (
                                        <p className="text-xs text-muted-foreground mt-0.5 flex items-center gap-1">
                                            <CheckCircle2 className="w-3 h-3" /> {t("recurringLastRun")}: {new Date(rec.last_run_date).toLocaleDateString("es-ES")}
                                        </p>
                                    )}
                                </div>
                                <div className="col-span-1 text-right">
                                    <p className="text-sm font-bold text-foreground font-mono">{fmt(totalRec)}</p>
                                </div>
                                <div className="col-span-2 flex items-center justify-end gap-1">
                                    <button
                                        onClick={() => handleRun(rec)}
                                        disabled={runningId === rec.id}
                                        title={t("recurringRunNow")}
                                        className="p-1.5 rounded-lg hover:bg-emerald-500/10 text-muted-foreground hover:text-emerald-400 transition-colors"
                                    >
                                        {runningId === rec.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
                                    </button>
                                    <button onClick={() => handleToggleActive(rec)} title={rec.is_active ? t("recurringPause") : t("recurringActivate")}
                                        className="p-1.5 rounded-lg hover:bg-amber-500/10 text-muted-foreground hover:text-amber-400 transition-colors">
                                        {rec.is_active ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5 text-emerald-400" />}
                                    </button>
                                    <button onClick={() => openEdit(rec)} className="p-1.5 rounded-lg hover:bg-accent text-muted-foreground hover:text-foreground transition-colors">
                                        <Pencil className="w-3.5 h-3.5" />
                                    </button>
                                    <button onClick={() => handleDelete(rec.id)} disabled={deletingId === rec.id}
                                        className="p-1.5 rounded-lg hover:bg-rose-500/10 text-muted-foreground hover:text-rose-400 transition-colors">
                                        {deletingId === rec.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Trash2 className="w-3.5 h-3.5" />}
                                    </button>
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}

            {/* Modal */}
            {showModal && (
                <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/60 backdrop-blur-sm pt-16 pb-8 overflow-y-auto">
                    <div className="bg-card border border-border rounded-2xl p-8 w-full max-w-2xl shadow-2xl">
                        <div className="flex items-center justify-between mb-6">
                            <h2 className="text-lg font-bold text-foreground">{editingId ? t("editRecurring") : t("newRecurring")}</h2>
                            <button onClick={() => setShowModal(false)} className="text-muted-foreground hover:text-foreground transition-colors"><X className="w-5 h-5" /></button>
                        </div>
                        <form onSubmit={handleSubmit} className="space-y-5">
                            <div>
                                <label className="block text-xs text-muted-foreground mb-1.5 font-medium">{t("templateName")} *</label>
                                <input type="text" required value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                                    className="w-full bg-card border border-border text-foreground text-sm rounded-xl px-3 py-2.5 focus:outline-none focus:border-primary transition-colors"
                                    placeholder={t("recurringNamePlaceholder")} />
                            </div>
                            <div className="grid grid-cols-3 gap-4">
                                <div>
                                    <label className="block text-xs text-muted-foreground mb-1.5 font-medium">{t("client")} *</label>
                                    <select required value={form.client_id} onChange={e => setForm(f => ({ ...f, client_id: e.target.value }))}
                                        className="w-full bg-card border border-border text-foreground text-sm rounded-xl px-3 py-2.5 focus:outline-none focus:border-primary transition-colors">
                                        <option value="">{t("recurringSelectClient")}</option>
                                        {clients.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-xs text-muted-foreground mb-1.5 font-medium">{t("intervalType")}</label>
                                    <select value={form.interval_type} onChange={e => setForm(f => ({ ...f, interval_type: e.target.value }))}
                                        className="w-full bg-card border border-border text-foreground text-sm rounded-xl px-3 py-2.5 focus:outline-none focus:border-primary transition-colors">
                                        <option value="weekly">{t("weekly")}</option>
                                        <option value="monthly">{t("monthly")}</option>
                                        <option value="quarterly">{t("quarterly")}</option>
                                        <option value="yearly">{t("yearly")}</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-xs text-muted-foreground mb-1.5 font-medium">{t("recurringFirstIssue")} *</label>
                                    <input type="date" required value={form.next_run_date} onChange={e => setForm(f => ({ ...f, next_run_date: e.target.value }))}
                                        className="w-full bg-card border border-border text-foreground text-sm rounded-xl px-3 py-2.5 focus:outline-none focus:border-primary transition-colors" />
                                </div>
                            </div>

                            {/* Lines */}
                            <div>
                                <div className="flex items-center justify-between mb-3">
                                    <p className="text-sm font-semibold text-foreground">{t("recurringInvoiceLines")}</p>
                                    <button type="button" onClick={() => setForm(f => ({ ...f, lines: [...f.lines, { ...EMPTY_LINE }] }))}
                                        className="text-xs text-primary hover:text-primary flex items-center gap-1 transition-colors">
                                        <Plus className="w-3 h-3" /> {t("add")}
                                    </button>
                                </div>
                                <div className="space-y-2">
                                    {form.lines.map((line, i) => (
                                        <div key={i} className="grid grid-cols-12 gap-2 items-center bg-muted rounded-xl p-3">
                                            <div className="col-span-5">
                                                <input type="text" placeholder={`${t("descriptionLabel")} *`} value={line.description} onChange={e => setLine(i, "description", e.target.value)}
                                                    className="w-full bg-card border border-border text-foreground text-xs rounded-lg px-2 py-2 focus:outline-none focus:border-primary" />
                                            </div>
                                            <div className="col-span-2">
                                                <input type="number" min={0.01} step={0.01} placeholder={t("quantity")} value={line.quantity} onChange={e => setLine(i, "quantity", parseFloat(e.target.value) || 0)}
                                                    className="w-full bg-card border border-border text-foreground text-xs rounded-lg px-2 py-2 focus:outline-none focus:border-primary" />
                                            </div>
                                            <div className="col-span-2">
                                                <input type="number" min={0} step={0.01} placeholder={t("unitPriceFull")} value={line.unit_price} onChange={e => setLine(i, "unit_price", parseFloat(e.target.value) || 0)}
                                                    className="w-full bg-card border border-border text-foreground text-xs rounded-lg px-2 py-2 focus:outline-none focus:border-primary" />
                                            </div>
                                            <div className="col-span-2">
                                                <select value={line.tax_percentage} onChange={e => setLine(i, "tax_percentage", parseFloat(e.target.value))}
                                                    className="w-full bg-card border border-border text-foreground text-xs rounded-lg px-2 py-2 focus:outline-none focus:border-primary">
                                                    {[0, 4, 10, 21].map(t => <option key={t} value={t}>{t}%</option>)}
                                                </select>
                                            </div>
                                            <div className="col-span-1 flex justify-end">
                                                <button type="button" onClick={() => setForm(f => ({ ...f, lines: f.lines.filter((_, idx) => idx !== i) }))} disabled={form.lines.length === 1}
                                                    className="p-1.5 hover:bg-rose-500/10 rounded-lg text-muted-foreground hover:text-rose-400 transition-colors disabled:opacity-30">
                                                    <X className="w-3.5 h-3.5" />
                                                </button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                                <div className="flex justify-between items-center mt-3 px-3">
                                    <span className="text-xs text-muted-foreground">{t("recurringTotalPerIssue")}</span>
                                    <span className="text-sm font-bold text-foreground font-mono">{fmt(totalAmount)}</span>
                                </div>
                            </div>

                            <div>
                                <label className="block text-xs text-muted-foreground mb-1.5 font-medium">{t("invoiceNotes")}</label>
                                <textarea value={form.notes} rows={2} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
                                    className="w-full bg-card border border-border text-foreground text-sm rounded-xl px-3 py-2.5 focus:outline-none focus:border-primary transition-colors resize-none"
                                    placeholder={t("recurringNotesPlaceholder")} />
                            </div>

                            <div className="flex gap-3 pt-2">
                                <button type="button" onClick={() => setShowModal(false)} className="flex-1 py-2.5 rounded-xl border border-border text-muted-foreground text-sm hover:bg-accent/50 transition-colors">{tc("cancel")}</button>
                                <button type="submit" disabled={saving} className="flex-1 py-2.5 rounded-xl bg-primary hover:bg-primary text-foreground text-sm font-medium transition-colors disabled:opacity-50 flex items-center justify-center gap-2">
                                    {saving && <Loader2 className="w-4 h-4 animate-spin" />}
                                    {editingId ? t("saveChanges") : t("createTemplate")}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
