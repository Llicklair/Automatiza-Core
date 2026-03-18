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

const fmt = (n: number) => n.toLocaleString("es-ES", { style: "currency", currency: "EUR" });

const INTERVAL_MAP: Record<string, string> = {
    weekly: "Semanal",
    monthly: "Mensual",
    quarterly: "Trimestral",
    yearly: "Anual",
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
        if (!await showConfirm({ message: `¿Generar ahora una factura para "${rec.name}"?`, confirmLabel: "Generar", confirmVariant: "primary" })) return;
        setRunningId(rec.id);
        try {
            await api.erp.recurring.run(rec.id);
            toast.success("Factura generada y guardada como borrador en Ventas → Facturas.");
            load();
        } catch (err: any) {
            toast.error(err?.message || "Error al generar factura");
        } finally {
            setRunningId(null);
        }
    };

    const handleDelete = async (id: string) => {
        if (!await showConfirm({ message: "¿Eliminar esta plantilla recurrente?", confirmLabel: "Eliminar", confirmVariant: "danger" })) return;
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
                    <h1 className="text-3xl font-bold text-white tracking-tight">Facturación Recurrente</h1>
                    <p className="mt-1 text-sm text-zinc-400">Plantillas que generan facturas automáticamente cada período.</p>
                </div>
                <button onClick={openNew} className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium px-4 py-2.5 rounded-xl transition-colors">
                    <Plus className="w-4 h-4" /> Nueva plantilla
                </button>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-3 gap-4">
                <div className="bg-[#111113] border border-[#27272a] rounded-2xl p-5">
                    <p className="text-xs text-zinc-500 uppercase tracking-wider mb-1">Plantillas activas</p>
                    <p className="text-2xl font-bold text-white">{recurrings.filter(r => r.is_active).length}</p>
                </div>
                <div className={`rounded-2xl p-5 border ${dueToday > 0 ? "bg-amber-500/10 border-amber-500/20" : "bg-[#111113] border-[#27272a]"}`}>
                    <p className={`text-xs uppercase tracking-wider mb-1 ${dueToday > 0 ? "text-amber-400" : "text-zinc-500"}`}>Vencidas hoy</p>
                    <p className={`text-2xl font-bold ${dueToday > 0 ? "text-amber-400" : "text-white"}`}>{dueToday}</p>
                </div>
                <div className="bg-[#111113] border border-[#27272a] rounded-2xl p-5">
                    <p className="text-xs text-zinc-500 uppercase tracking-wider mb-1">Facturación mensual estimada</p>
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
                        <span className="font-semibold">{dueToday} plantilla{dueToday > 1 ? "s" : ""}</span> {dueToday > 1 ? "están" : "está"} vencida{dueToday > 1 ? "s" : ""}.
                        Se procesarán automáticamente a las 8:00, o usa el botón <span className="font-mono">▶</span> para generarlas ahora.
                    </p>
                </div>
            )}

            {/* Search */}
            <div className="relative">
                <Search className="w-4 h-4 text-zinc-500 absolute left-3 top-1/2 -translate-y-1/2" />
                <input type="text" placeholder="Buscar por nombre o cliente..." value={search} onChange={e => setSearch(e.target.value)}
                    className="w-full bg-[#18181b] border border-[#3f3f46] text-white text-sm rounded-xl pl-9 pr-4 py-2.5 focus:outline-none focus:border-indigo-500 transition-colors" />
            </div>

            {/* List */}
            {loading ? (
                <div className="flex items-center justify-center py-24 text-zinc-500 gap-2">
                    <Loader2 className="w-5 h-5 animate-spin" /> Cargando plantillas…
                </div>
            ) : filtered.length === 0 ? (
                <div className="bg-[#111113] border border-[#27272a] rounded-2xl p-16 flex flex-col items-center text-center">
                    <RefreshCw className="w-12 h-12 text-zinc-700 mb-4" />
                    <h2 className="text-lg font-bold text-white mb-2">{recurrings.length === 0 ? "Sin plantillas" : "Sin resultados"}</h2>
                    <p className="text-sm text-zinc-500 max-w-sm">
                        {recurrings.length === 0
                            ? "Configura tu primera factura recurrente para automatizar la facturación periódica."
                            : `Sin resultados para "${search}"`}
                    </p>
                    {recurrings.length === 0 && (
                        <button onClick={openNew} className="mt-6 bg-indigo-600 hover:bg-indigo-500 text-white text-sm px-4 py-2 rounded-xl transition-colors">Crear plantilla</button>
                    )}
                </div>
            ) : (
                <div className="bg-[#111113] border border-[#27272a] rounded-2xl overflow-hidden">
                    <div className="grid grid-cols-12 gap-4 px-6 py-3 border-b border-[#27272a] text-xs font-medium text-zinc-500 uppercase tracking-wide bg-[#161618]">
                        <div className="col-span-3">Plantilla</div>
                        <div className="col-span-2">Cliente</div>
                        <div className="col-span-2">Intervalo</div>
                        <div className="col-span-2">Próxima emisión</div>
                        <div className="col-span-1 text-right">Importe</div>
                        <div className="col-span-2 text-right">Acciones</div>
                    </div>
                    {filtered.map(rec => {
                        const totalRec = rec.lines_json.reduce((acc, l) => acc + l.quantity * l.unit_price * (1 + l.tax_percentage / 100), 0);
                        const isDue = rec.is_active && rec.next_run_date <= new Date().toISOString().split("T")[0];
                        const intervalCls = INTERVAL_COLORS[rec.interval_type] || "text-zinc-400 bg-zinc-500/10 border-zinc-500/20";

                        return (
                            <div key={rec.id} className="grid grid-cols-12 gap-4 px-6 py-4 border-b border-[#27272a]/50 last:border-0 hover:bg-white/[0.02] transition-colors items-center">
                                <div className="col-span-3 flex items-center gap-3">
                                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${rec.is_active ? "bg-indigo-500/10 border border-indigo-500/20" : "bg-zinc-500/10 border border-zinc-500/20"}`}>
                                        <RefreshCw className={`w-4 h-4 ${rec.is_active ? "text-indigo-400" : "text-zinc-600"}`} />
                                    </div>
                                    <div>
                                        <p className={`text-sm font-medium ${rec.is_active ? "text-white" : "text-zinc-500"}`}>{rec.name}</p>
                                        {!rec.is_active && <p className="text-xs text-zinc-600">Pausada</p>}
                                    </div>
                                </div>
                                <div className="col-span-2">
                                    <p className="text-sm text-zinc-300 truncate">{rec.client?.name || "—"}</p>
                                </div>
                                <div className="col-span-2">
                                    <span className={`text-xs px-2 py-1 rounded-full border ${intervalCls}`}>
                                        {INTERVAL_MAP[rec.interval_type] || rec.interval_type}
                                    </span>
                                </div>
                                <div className="col-span-2">
                                    <div className="flex items-center gap-1.5">
                                        <Calendar className={`w-3 h-3 ${isDue ? "text-amber-400" : "text-zinc-600"}`} />
                                        <span className={`text-sm ${isDue ? "text-amber-400 font-medium" : "text-zinc-400"}`}>
                                            {new Date(rec.next_run_date).toLocaleDateString("es-ES")}
                                        </span>
                                        {isDue && <span className="text-xs bg-amber-500/20 text-amber-400 px-1.5 py-0.5 rounded-md border border-amber-500/30">Vencida</span>}
                                    </div>
                                    {rec.last_run_date && (
                                        <p className="text-xs text-zinc-600 mt-0.5 flex items-center gap-1">
                                            <CheckCircle2 className="w-3 h-3" /> Última: {new Date(rec.last_run_date).toLocaleDateString("es-ES")}
                                        </p>
                                    )}
                                </div>
                                <div className="col-span-1 text-right">
                                    <p className="text-sm font-bold text-white font-mono">{fmt(totalRec)}</p>
                                </div>
                                <div className="col-span-2 flex items-center justify-end gap-1">
                                    <button
                                        onClick={() => handleRun(rec)}
                                        disabled={runningId === rec.id}
                                        title="Generar factura ahora"
                                        className="p-1.5 rounded-lg hover:bg-emerald-500/10 text-zinc-500 hover:text-emerald-400 transition-colors"
                                    >
                                        {runningId === rec.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
                                    </button>
                                    <button onClick={() => handleToggleActive(rec)} title={rec.is_active ? "Pausar" : "Activar"}
                                        className="p-1.5 rounded-lg hover:bg-amber-500/10 text-zinc-500 hover:text-amber-400 transition-colors">
                                        {rec.is_active ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5 text-emerald-400" />}
                                    </button>
                                    <button onClick={() => openEdit(rec)} className="p-1.5 rounded-lg hover:bg-white/10 text-zinc-500 hover:text-white transition-colors">
                                        <Pencil className="w-3.5 h-3.5" />
                                    </button>
                                    <button onClick={() => handleDelete(rec.id)} disabled={deletingId === rec.id}
                                        className="p-1.5 rounded-lg hover:bg-rose-500/10 text-zinc-500 hover:text-rose-400 transition-colors">
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
                    <div className="bg-[#111113] border border-[#27272a] rounded-2xl p-8 w-full max-w-2xl shadow-2xl">
                        <div className="flex items-center justify-between mb-6">
                            <h2 className="text-lg font-bold text-white">{editingId ? "Editar plantilla" : "Nueva factura recurrente"}</h2>
                            <button onClick={() => setShowModal(false)} className="text-zinc-500 hover:text-white transition-colors"><X className="w-5 h-5" /></button>
                        </div>
                        <form onSubmit={handleSubmit} className="space-y-5">
                            <div>
                                <label className="block text-xs text-zinc-400 mb-1.5 font-medium">Nombre de la plantilla *</label>
                                <input type="text" required value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                                    className="w-full bg-[#18181b] border border-[#3f3f46] text-white text-sm rounded-xl px-3 py-2.5 focus:outline-none focus:border-indigo-500 transition-colors"
                                    placeholder="Ej: Cuota mensual soporte IT, Suscripción anual…" />
                            </div>
                            <div className="grid grid-cols-3 gap-4">
                                <div>
                                    <label className="block text-xs text-zinc-400 mb-1.5 font-medium">Cliente *</label>
                                    <select required value={form.client_id} onChange={e => setForm(f => ({ ...f, client_id: e.target.value }))}
                                        className="w-full bg-[#18181b] border border-[#3f3f46] text-white text-sm rounded-xl px-3 py-2.5 focus:outline-none focus:border-indigo-500 transition-colors">
                                        <option value="">Seleccionar…</option>
                                        {clients.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-xs text-zinc-400 mb-1.5 font-medium">Periodicidad</label>
                                    <select value={form.interval_type} onChange={e => setForm(f => ({ ...f, interval_type: e.target.value }))}
                                        className="w-full bg-[#18181b] border border-[#3f3f46] text-white text-sm rounded-xl px-3 py-2.5 focus:outline-none focus:border-indigo-500 transition-colors">
                                        <option value="weekly">Semanal</option>
                                        <option value="monthly">Mensual</option>
                                        <option value="quarterly">Trimestral</option>
                                        <option value="yearly">Anual</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-xs text-zinc-400 mb-1.5 font-medium">Primera emisión *</label>
                                    <input type="date" required value={form.next_run_date} onChange={e => setForm(f => ({ ...f, next_run_date: e.target.value }))}
                                        className="w-full bg-[#18181b] border border-[#3f3f46] text-white text-sm rounded-xl px-3 py-2.5 focus:outline-none focus:border-indigo-500 transition-colors" />
                                </div>
                            </div>

                            {/* Lines */}
                            <div>
                                <div className="flex items-center justify-between mb-3">
                                    <p className="text-sm font-semibold text-white">Líneas de factura</p>
                                    <button type="button" onClick={() => setForm(f => ({ ...f, lines: [...f.lines, { ...EMPTY_LINE }] }))}
                                        className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 transition-colors">
                                        <Plus className="w-3 h-3" /> Añadir
                                    </button>
                                </div>
                                <div className="space-y-2">
                                    {form.lines.map((line, i) => (
                                        <div key={i} className="grid grid-cols-12 gap-2 items-center bg-[#161618] rounded-xl p-3">
                                            <div className="col-span-5">
                                                <input type="text" placeholder="Descripción *" value={line.description} onChange={e => setLine(i, "description", e.target.value)}
                                                    className="w-full bg-[#18181b] border border-[#3f3f46] text-white text-xs rounded-lg px-2 py-2 focus:outline-none focus:border-indigo-500" />
                                            </div>
                                            <div className="col-span-2">
                                                <input type="number" min={0.01} step={0.01} placeholder="Cant." value={line.quantity} onChange={e => setLine(i, "quantity", parseFloat(e.target.value) || 0)}
                                                    className="w-full bg-[#18181b] border border-[#3f3f46] text-white text-xs rounded-lg px-2 py-2 focus:outline-none focus:border-indigo-500" />
                                            </div>
                                            <div className="col-span-2">
                                                <input type="number" min={0} step={0.01} placeholder="€/ud." value={line.unit_price} onChange={e => setLine(i, "unit_price", parseFloat(e.target.value) || 0)}
                                                    className="w-full bg-[#18181b] border border-[#3f3f46] text-white text-xs rounded-lg px-2 py-2 focus:outline-none focus:border-indigo-500" />
                                            </div>
                                            <div className="col-span-2">
                                                <select value={line.tax_percentage} onChange={e => setLine(i, "tax_percentage", parseFloat(e.target.value))}
                                                    className="w-full bg-[#18181b] border border-[#3f3f46] text-white text-xs rounded-lg px-2 py-2 focus:outline-none focus:border-indigo-500">
                                                    {[0, 4, 10, 21].map(t => <option key={t} value={t}>{t}%</option>)}
                                                </select>
                                            </div>
                                            <div className="col-span-1 flex justify-end">
                                                <button type="button" onClick={() => setForm(f => ({ ...f, lines: f.lines.filter((_, idx) => idx !== i) }))} disabled={form.lines.length === 1}
                                                    className="p-1.5 hover:bg-rose-500/10 rounded-lg text-zinc-600 hover:text-rose-400 transition-colors disabled:opacity-30">
                                                    <X className="w-3.5 h-3.5" />
                                                </button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                                <div className="flex justify-between items-center mt-3 px-3">
                                    <span className="text-xs text-zinc-500">Total por emisión</span>
                                    <span className="text-sm font-bold text-white font-mono">{fmt(totalAmount)}</span>
                                </div>
                            </div>

                            <div>
                                <label className="block text-xs text-zinc-400 mb-1.5 font-medium">Notas en la factura</label>
                                <textarea value={form.notes} rows={2} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
                                    className="w-full bg-[#18181b] border border-[#3f3f46] text-white text-sm rounded-xl px-3 py-2.5 focus:outline-none focus:border-indigo-500 transition-colors resize-none"
                                    placeholder="Se incluirá en cada factura generada." />
                            </div>

                            <div className="flex gap-3 pt-2">
                                <button type="button" onClick={() => setShowModal(false)} className="flex-1 py-2.5 rounded-xl border border-[#3f3f46] text-zinc-400 text-sm hover:bg-white/5 transition-colors">Cancelar</button>
                                <button type="submit" disabled={saving} className="flex-1 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium transition-colors disabled:opacity-50 flex items-center justify-center gap-2">
                                    {saving && <Loader2 className="w-4 h-4 animate-spin" />}
                                    {editingId ? "Guardar cambios" : "Crear plantilla"}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
