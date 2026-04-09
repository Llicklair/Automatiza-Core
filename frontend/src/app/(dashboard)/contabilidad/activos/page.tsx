"use client";

import { useEffect, useState } from "react";
import { api, type FixedAsset } from "@/lib/api";
import { logError } from "@/lib/logger";
import {
    Monitor, Building2, Car, Package, Loader2, Plus, X,
    Pencil, Trash2, TrendingDown, Wallet, Archive
} from "lucide-react";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";

const fmt = (n: number) => n.toLocaleString("es-ES", { style: "currency", currency: "EUR" });

const CATEGORIES = [
    { value: "equipment", label: "Equipos informáticos", icon: Monitor, color: "text-blue-400 bg-blue-500/10 border-blue-500/20" },
    { value: "furniture", label: "Mobiliario e instalaciones", icon: Building2, color: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20" },
    { value: "vehicle", label: "Vehículos", icon: Car, color: "text-amber-400 bg-amber-500/10 border-amber-500/20" },
    { value: "intangible", label: "Inmovilizado intangible", icon: Package, color: "text-purple-400 bg-purple-500/10 border-purple-500/20" },
    { value: "other", label: "Otros activos", icon: Archive, color: "text-muted-foreground bg-muted border-border" },
];

const ACCOUNT_CODES = [
    { code: "210", label: "210 — Terrenos y bienes naturales" },
    { code: "211", label: "211 — Construcciones" },
    { code: "212", label: "212 — Instalaciones técnicas" },
    { code: "213", label: "213 — Maquinaria" },
    { code: "214", label: "214 — Utillaje" },
    { code: "215", label: "215 — Otras instalaciones" },
    { code: "216", label: "216 — Mobiliario" },
    { code: "217", label: "217 — Equipos para procesos de información" },
    { code: "218", label: "218 — Elementos de transporte" },
    { code: "219", label: "219 — Otro inmovilizado material" },
    { code: "200", label: "200 — Investigación" },
    { code: "201", label: "201 — Desarrollo" },
    { code: "203", label: "203 — Propiedad industrial" },
    { code: "205", label: "205 — Derechos de traspaso" },
    { code: "206", label: "206 — Aplicaciones informáticas" },
];

/** Accumulated depreciation (linear) in euros from purchase date to today */
function calcDepreciation(asset: FixedAsset): number {
    const depreciable = Number(asset.purchase_value) - Number(asset.residual_value);
    const monthlyRate = depreciable / (Number(asset.useful_life_years) * 12);
    const purchaseDate = new Date(asset.purchase_date);
    const today = new Date();
    const months = Math.max(0,
        (today.getFullYear() - purchaseDate.getFullYear()) * 12 +
        (today.getMonth() - purchaseDate.getMonth())
    );
    return Math.min(depreciable, monthlyRate * months);
}

type FormState = {
    name: string; category: string; description: string;
    purchase_date: string; purchase_value: string;
    useful_life_years: string; residual_value: string;
    account_code: string; reference_invoice: string; notes: string;
};

const emptyForm = (): FormState => ({
    name: "", category: "equipment", description: "",
    purchase_date: new Date().toISOString().slice(0, 10),
    purchase_value: "", useful_life_years: "5", residual_value: "0",
    account_code: "217", reference_invoice: "", notes: "",
});

export default function ActivosFijosPage() {
    const toast = useToastStore();
    const [assets, setAssets] = useState<FixedAsset[]>([]);
    const [loading, setLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);
    const [editingId, setEditingId] = useState<string | null>(null);
    const [form, setForm] = useState<FormState>(emptyForm());
    const [saving, setSaving] = useState(false);
    const [deletingId, setDeletingId] = useState<string | null>(null);

    useEffect(() => {
        api.accounting.assets.list()
            .then(setAssets)
            .catch(err => logError("contabilidad/activos", err))
            .finally(() => setLoading(false));
    }, []);

    const openCreate = () => { setEditingId(null); setForm(emptyForm()); setShowModal(true); };
    const openEdit = (a: FixedAsset) => {
        setEditingId(a.id);
        setForm({
            name: a.name, category: a.category || "other", description: a.description || "",
            purchase_date: a.purchase_date.slice(0, 10),
            purchase_value: String(a.purchase_value),
            useful_life_years: String(a.useful_life_years),
            residual_value: String(a.residual_value),
            account_code: a.account_code || "213",
            reference_invoice: a.reference_invoice || "",
            notes: a.notes || "",
        });
        setShowModal(true);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setSaving(true);
        const payload = {
            name: form.name,
            category: form.category,
            description: form.description || null,
            purchase_date: form.purchase_date,
            purchase_value: parseFloat(form.purchase_value),
            useful_life_years: parseFloat(form.useful_life_years),
            residual_value: parseFloat(form.residual_value) || 0,
            account_code: form.account_code || null,
            reference_invoice: form.reference_invoice || null,
            notes: form.notes || null,
        };
        try {
            if (editingId) {
                const updated = await api.accounting.assets.update(editingId, payload);
                setAssets(prev => prev.map(a => a.id === editingId ? updated : a));
            } else {
                const created = await api.accounting.assets.create(payload);
                setAssets(prev => [created, ...prev]);
            }
            setShowModal(false);
        } catch (err: any) {
            toast.error(err?.message || "Error guardando activo");
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = async (id: string, name: string) => {
        if (!await showConfirm({ message: `¿Eliminar "${name}"? Esta acción no se puede deshacer.`, confirmLabel: "Eliminar", confirmVariant: "danger" })) return;
        setDeletingId(id);
        try {
            await api.accounting.assets.delete(id);
            setAssets(prev => prev.filter(a => a.id !== id));
        } catch (err: any) {
            toast.error(err?.message || "Error eliminando activo");
        } finally {
            setDeletingId(null);
        }
    };

    const totalValue = assets.reduce((s, a) => s + Number(a.purchase_value), 0);
    const totalDepreciation = assets.reduce((s, a) => s + calcDepreciation(a), 0);
    const netBookValue = totalValue - totalDepreciation;

    const f = (field: keyof FormState, val: string) => setForm(prev => ({ ...prev, [field]: val }));

    return (
        <div className="p-8 max-w-6xl mx-auto space-y-8">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-foreground tracking-tight">Activos y Amortizaciones</h1>
                    <p className="mt-1 text-sm text-muted-foreground">
                        Control del inmovilizado material e intangible y sus cuotas de amortización lineal.
                    </p>
                </div>
                <button
                    onClick={openCreate}
                    className="flex items-center gap-2 bg-primary hover:bg-primary text-foreground px-5 py-2.5 rounded-xl font-medium transition-colors text-sm shadow-lg shadow-primary/20"
                >
                    <Plus className="w-4 h-4" /> Añadir Activo
                </button>
            </div>

            {/* KPIs */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-card border border-border rounded-2xl p-6">
                    <div className="flex items-center gap-3 mb-3">
                        <div className="w-10 h-10 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center">
                            <Wallet className="w-5 h-5 text-primary" />
                        </div>
                        <p className="text-xs uppercase text-muted-foreground font-bold tracking-wider">Valor de adquisición</p>
                    </div>
                    <p className="text-2xl font-bold text-foreground">{fmt(totalValue)}</p>
                    <p className="text-xs text-muted-foreground mt-1">{assets.length} activo{assets.length !== 1 ? "s" : ""} registrado{assets.length !== 1 ? "s" : ""}</p>
                </div>
                <div className="bg-card border border-border rounded-2xl p-6">
                    <div className="flex items-center gap-3 mb-3">
                        <div className="w-10 h-10 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center">
                            <TrendingDown className="w-5 h-5 text-rose-400" />
                        </div>
                        <p className="text-xs uppercase text-muted-foreground font-bold tracking-wider">Amortización acumulada</p>
                    </div>
                    <p className="text-2xl font-bold text-rose-400">-{fmt(totalDepreciation)}</p>
                    <p className="text-xs text-muted-foreground mt-1">Método lineal desde fecha de compra</p>
                </div>
                <div className="bg-primary/20 border border-primary/20 rounded-2xl p-6">
                    <div className="flex items-center gap-3 mb-3">
                        <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
                            <Building2 className="w-5 h-5 text-emerald-400" />
                        </div>
                        <p className="text-xs uppercase text-primary/70 font-bold tracking-wider">Valor neto contable</p>
                    </div>
                    <p className="text-2xl font-bold text-emerald-400">{fmt(netBookValue)}</p>
                    <p className="text-xs text-primary/50 mt-1">Valor adquisición menos amortizaciones</p>
                </div>
            </div>

            {/* Table */}
            <div className="bg-card border border-border rounded-2xl overflow-hidden shadow-2xl">
                <div className="grid grid-cols-12 gap-4 px-6 py-3 border-b border-border text-xs font-medium text-muted-foreground uppercase tracking-wide bg-muted">
                    <div className="col-span-3">Activo</div>
                    <div className="col-span-1">Cuenta</div>
                    <div className="col-span-2 text-right">Valor adq.</div>
                    <div className="col-span-2 text-right">Amort. acum.</div>
                    <div className="col-span-2 text-right">Valor neto</div>
                    <div className="col-span-1 text-right">€/mes</div>
                    <div className="col-span-1 text-right"></div>
                </div>

                {loading ? (
                    <div className="py-16 flex items-center justify-center gap-2 text-muted-foreground">
                        <Loader2 className="w-4 h-4 animate-spin" /> Cargando activos…
                    </div>
                ) : assets.length === 0 ? (
                    <div className="py-16 flex flex-col items-center text-center">
                        <Archive className="w-10 h-10 text-muted-foreground mb-3" />
                        <p className="text-muted-foreground font-medium">Sin activos registrados</p>
                        <p className="text-muted-foreground text-sm mt-1 mb-4">Añade ordenadores, vehículos o instalaciones para ver su amortización.</p>
                        <button onClick={openCreate} className="text-sm text-primary hover:text-primary transition">
                            + Añadir primer activo
                        </button>
                    </div>
                ) : (
                    <div className="divide-y divide-border">
                        {assets.map(asset => {
                            const dep = calcDepreciation(asset);
                            const net = Number(asset.purchase_value) - dep;
                            const monthly = (Number(asset.purchase_value) - Number(asset.residual_value)) / (Number(asset.useful_life_years) * 12);
                            const cat = CATEGORIES.find(c => c.value === asset.category) || CATEGORIES[4];
                            const Icon = cat.icon;
                            return (
                                <div key={asset.id} className="grid grid-cols-12 gap-4 px-6 py-4 items-center hover:bg-white/[0.01] transition">
                                    <div className="col-span-3 flex items-center gap-3 min-w-0">
                                        <div className={`w-8 h-8 rounded-lg border flex items-center justify-center flex-shrink-0 ${cat.color}`}>
                                            <Icon className="w-4 h-4" />
                                        </div>
                                        <div className="min-w-0">
                                            <p className="text-sm font-medium text-foreground truncate">{asset.name}</p>
                                            <p className="text-xs text-muted-foreground">
                                                {new Date(asset.purchase_date).toLocaleDateString("es-ES", { day: "2-digit", month: "short", year: "numeric" })}
                                                {" · "}{asset.useful_life_years}a
                                            </p>
                                        </div>
                                    </div>
                                    <div className="col-span-1">
                                        <span className="text-xs font-mono bg-muted border border-border text-muted-foreground px-1.5 py-0.5 rounded">
                                            {asset.account_code || "—"}
                                        </span>
                                    </div>
                                    <div className="col-span-2 text-right text-sm text-foreground font-mono">{fmt(Number(asset.purchase_value))}</div>
                                    <div className="col-span-2 text-right text-sm text-rose-400 font-mono">-{fmt(dep)}</div>
                                    <div className="col-span-2 text-right text-sm font-semibold text-emerald-400 font-mono">{fmt(net)}</div>
                                    <div className="col-span-1 text-right text-xs text-muted-foreground font-mono">{fmt(monthly)}</div>
                                    <div className="col-span-1 text-right">
                                        <div className="flex items-center justify-end gap-1">
                                            <button onClick={() => openEdit(asset)}
                                                className="p-1.5 text-muted-foreground hover:text-primary hover:bg-primary/10 rounded-lg transition-colors">
                                                <Pencil className="w-3.5 h-3.5" />
                                            </button>
                                            <button onClick={() => handleDelete(asset.id, asset.name)} disabled={deletingId === asset.id}
                                                className="p-1.5 text-muted-foreground hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors disabled:opacity-50">
                                                {deletingId === asset.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Trash2 className="w-3.5 h-3.5" />}
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>

            {/* Modal crear/editar */}
            {showModal && (
                <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                    <div className="bg-card border border-border rounded-2xl w-full max-w-2xl shadow-2xl max-h-[90vh] flex flex-col">
                        <div className="p-5 border-b border-border flex justify-between items-center bg-muted flex-shrink-0">
                            <h2 className="text-lg font-medium text-foreground flex items-center gap-2">
                                <Archive className="w-4 h-4 text-primary" />
                                {editingId ? "Editar Activo" : "Nuevo Activo Fijo"}
                            </h2>
                            <button onClick={() => setShowModal(false)} className="text-muted-foreground hover:text-foreground">
                                <X className="w-5 h-5" />
                            </button>
                        </div>
                        <form onSubmit={handleSubmit} className="p-6 space-y-4 overflow-y-auto">
                            <div className="grid grid-cols-2 gap-4">
                                <div className="col-span-2">
                                    <label className="block text-sm text-muted-foreground mb-1.5">Nombre del activo *</label>
                                    <input required type="text" value={form.name} onChange={e => f("name", e.target.value)}
                                        placeholder="Ej: MacBook Pro M3, Furgoneta de reparto"
                                        className="w-full bg-background border border-border rounded-lg px-4 py-2 text-foreground focus:outline-none focus:border-primary" />
                                </div>
                                <div>
                                    <label className="block text-sm text-muted-foreground mb-1.5">Categoría</label>
                                    <select value={form.category} onChange={e => f("category", e.target.value)}
                                        className="w-full bg-background border border-border rounded-lg px-3 py-2 text-foreground focus:outline-none focus:border-primary">
                                        {CATEGORIES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-sm text-muted-foreground mb-1.5">Cuenta PGC</label>
                                    <select value={form.account_code} onChange={e => f("account_code", e.target.value)}
                                        className="w-full bg-background border border-border rounded-lg px-3 py-2 text-foreground focus:outline-none focus:border-primary">
                                        {ACCOUNT_CODES.map(c => <option key={c.code} value={c.code}>{c.label}</option>)}
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-sm text-muted-foreground mb-1.5">Fecha de compra *</label>
                                    <input required type="date" value={form.purchase_date} onChange={e => f("purchase_date", e.target.value)}
                                        className="w-full bg-background border border-border rounded-lg px-4 py-2 text-foreground focus:outline-none focus:border-primary" />
                                </div>
                                <div>
                                    <label className="block text-sm text-muted-foreground mb-1.5">Valor de adquisición (€) *</label>
                                    <input required type="number" min="0" step="0.01" value={form.purchase_value} onChange={e => f("purchase_value", e.target.value)}
                                        placeholder="0.00"
                                        className="w-full bg-background border border-border rounded-lg px-4 py-2 text-foreground focus:outline-none focus:border-primary" />
                                </div>
                                <div>
                                    <label className="block text-sm text-muted-foreground mb-1.5">Vida útil (años) *</label>
                                    <input required type="number" min="1" max="100" step="0.5" value={form.useful_life_years} onChange={e => f("useful_life_years", e.target.value)}
                                        className="w-full bg-background border border-border rounded-lg px-4 py-2 text-foreground focus:outline-none focus:border-primary" />
                                </div>
                                <div>
                                    <label className="block text-sm text-muted-foreground mb-1.5">Valor residual (€)</label>
                                    <input type="number" min="0" step="0.01" value={form.residual_value} onChange={e => f("residual_value", e.target.value)}
                                        className="w-full bg-background border border-border rounded-lg px-4 py-2 text-foreground focus:outline-none focus:border-primary" />
                                </div>
                                <div>
                                    <label className="block text-sm text-muted-foreground mb-1.5">Nº Factura / Referencia</label>
                                    <input type="text" value={form.reference_invoice} onChange={e => f("reference_invoice", e.target.value)}
                                        placeholder="Opcional"
                                        className="w-full bg-background border border-border rounded-lg px-4 py-2 text-foreground focus:outline-none focus:border-primary" />
                                </div>
                                <div className="col-span-2">
                                    <label className="block text-sm text-muted-foreground mb-1.5">Descripción / Notas</label>
                                    <textarea value={form.notes} onChange={e => f("notes", e.target.value)}
                                        className="w-full bg-background border border-border rounded-lg px-4 py-2 text-foreground focus:outline-none focus:border-primary resize-none h-16" />
                                </div>
                            </div>

                            {form.purchase_value && form.useful_life_years && (
                                <div className="bg-primary/5 border border-primary/20 rounded-xl p-3 text-xs text-muted-foreground">
                                    <span className="text-primary font-medium">Cuota mensual estimada: </span>
                                    {fmt((parseFloat(form.purchase_value) - (parseFloat(form.residual_value) || 0)) / (parseFloat(form.useful_life_years) * 12))}
                                    {" · "}Vida útil: {form.useful_life_years} años
                                </div>
                            )}

                            <div className="pt-2 flex justify-end gap-3">
                                <button type="button" onClick={() => setShowModal(false)}
                                    className="px-5 py-2.5 text-foreground hover:text-foreground transition-colors font-medium border border-border rounded-lg">
                                    Cancelar
                                </button>
                                <button type="submit" disabled={saving || !form.name || !form.purchase_value}
                                    className="inline-flex items-center gap-2 bg-primary hover:bg-primary text-foreground px-6 py-2.5 rounded-lg font-medium transition-colors shadow-lg shadow-primary/20 disabled:opacity-50">
                                    {saving && <Loader2 className="w-4 h-4 animate-spin" />}
                                    {editingId ? "Guardar cambios" : "Añadir activo"}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
