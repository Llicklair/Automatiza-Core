"use client";

import { Monitor, Building2, Car, Package, Loader2, Plus, Pencil, Trash2, TrendingDown, Wallet, Archive } from "lucide-react";
import { useActivos, calcDepreciation } from "./_hooks/useActivos";
import { AssetModal } from "./_components/AssetModal";

const fmt = (n: number) => n.toLocaleString("es-ES", { style: "currency", currency: "EUR" });

const CATEGORIES = [
    { value: "equipment", label: "Equipos informáticos", icon: Monitor, color: "text-blue-400 bg-blue-500/10 border-blue-500/20" },
    { value: "furniture", label: "Mobiliario e instalaciones", icon: Building2, color: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20" },
    { value: "vehicle", label: "Vehículos", icon: Car, color: "text-amber-400 bg-amber-500/10 border-amber-500/20" },
    { value: "intangible", label: "Inmovilizado intangible", icon: Package, color: "text-purple-400 bg-purple-500/10 border-purple-500/20" },
    { value: "other", label: "Otros activos", icon: Archive, color: "text-muted-foreground bg-muted border-border" },
];

export default function ActivosFijosPage() {
    const {
        assets, loading, showModal, setShowModal,
        editingId, form, saving, deletingId,
        openCreate, openEdit, handleSubmit, handleDelete, setField,
        totalValue, totalDepreciation, netBookValue,
    } = useActivos();

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

            {showModal && (
                <AssetModal
                    editingId={editingId}
                    form={form}
                    saving={saving}
                    onClose={() => setShowModal(false)}
                    onSubmit={handleSubmit}
                    setField={setField}
                />
            )}
        </div>
    );
}
