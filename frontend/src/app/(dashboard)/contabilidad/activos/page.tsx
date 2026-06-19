"use client";

import { Monitor, Building2, Car, Package, Loader2, Plus, Pencil, Trash2, TrendingDown, Wallet, Archive } from "lucide-react";
import { useTranslations } from "next-intl";
import { useActivos, calcDepreciation } from "./_hooks/useActivos";
import { AssetModal } from "./_components/AssetModal";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/ui/button";

const fmt = (n: number) => n.toLocaleString("es-ES", { style: "currency", currency: "EUR" });

const CATEGORIES = (t: (k: string) => string) => [
    { value: "equipment", label: t("activos.categoryEquipment"), icon: Monitor, color: "text-blue-400 bg-blue-500/10 border-blue-500/20" },
    { value: "furniture", label: t("activos.categoryFurniture"), icon: Building2, color: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20" },
    { value: "vehicle", label: t("activos.categoryVehicle"), icon: Car, color: "text-amber-400 bg-amber-500/10 border-amber-500/20" },
    { value: "intangible", label: t("activos.categoryIntangible"), icon: Package, color: "text-purple-400 bg-purple-500/10 border-purple-500/20" },
    { value: "other", label: t("activos.categoryOther"), icon: Archive, color: "text-muted-foreground bg-muted border-border" },
];

export default function ActivosFijosPage() {
    const t = useTranslations("contabilidad");
    const {
        assets, loading, showModal, setShowModal,
        editingId, form, saving, deletingId,
        openCreate, openEdit, handleSubmit, handleDelete, setField,
        totalValue, totalDepreciation, netBookValue,
    } = useActivos();
    const categories = CATEGORIES(t);

    return (
        <div className="p-8 max-w-[1400px] mx-auto space-y-6">
            <PageHeader
                title={t("activos.title")}
                description={t("activos.description")}
                icon={Archive}
                actions={
                    <Button onClick={openCreate}>
                        <Plus className="w-4 h-4 mr-2" /> {t("activos.addAsset")}
                    </Button>
                }
            />

            {/* KPIs */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-card border border-border rounded-2xl p-6">
                    <div className="flex items-center gap-3 mb-3">
                        <div className="w-10 h-10 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center">
                            <Wallet className="w-5 h-5 text-primary" />
                        </div>
                        <p className="text-xs uppercase text-muted-foreground font-bold tracking-wider">{t("activos.acquisitionValue")}</p>
                    </div>
                    <p className="text-2xl font-bold text-foreground">{fmt(totalValue)}</p>
                    <p className="text-xs text-muted-foreground mt-1">{t("activos.assetsRegistered", { count: assets.length })}</p>
                </div>
                <div className="bg-card border border-border rounded-2xl p-6">
                    <div className="flex items-center gap-3 mb-3">
                        <div className="w-10 h-10 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center">
                            <TrendingDown className="w-5 h-5 text-rose-400" />
                        </div>
                        <p className="text-xs uppercase text-muted-foreground font-bold tracking-wider">{t("activos.accumulatedDepreciation")}</p>
                    </div>
                    <p className="text-2xl font-bold text-rose-400">-{fmt(totalDepreciation)}</p>
                    <p className="text-xs text-muted-foreground mt-1">{t("activos.linearMethodSincePurchase")}</p>
                </div>
                <div className="bg-primary/20 border border-primary/20 rounded-2xl p-6">
                    <div className="flex items-center gap-3 mb-3">
                        <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
                            <Building2 className="w-5 h-5 text-emerald-400" />
                        </div>
                        <p className="text-xs uppercase text-primary/70 font-bold tracking-wider">{t("activos.netBookValue")}</p>
                    </div>
                    <p className="text-2xl font-bold text-emerald-400">{fmt(netBookValue)}</p>
                    <p className="text-xs text-primary/50 mt-1">{t("activos.netBookValueHint")}</p>
                </div>
            </div>

            {/* Table */}
            <div className="bg-card border border-border rounded-2xl overflow-hidden shadow-2xl">
                <div className="grid grid-cols-12 gap-4 px-6 py-3 border-b border-border text-xs font-medium text-muted-foreground uppercase tracking-wide bg-muted">
                    <div className="col-span-3">{t("activos.thAsset")}</div>
                    <div className="col-span-1">{t("activos.thAccount")}</div>
                    <div className="col-span-2 text-right">{t("activos.thAcqValue")}</div>
                    <div className="col-span-2 text-right">{t("activos.thAccumDep")}</div>
                    <div className="col-span-2 text-right">{t("activos.thNetValue")}</div>
                    <div className="col-span-1 text-right">{t("activos.thPerMonth")}</div>
                    <div className="col-span-1 text-right"></div>
                </div>

                {loading ? (
                    <div className="py-16 flex items-center justify-center gap-2 text-muted-foreground">
                        <Loader2 className="w-4 h-4 animate-spin" /> {t("activos.loading")}
                    </div>
                ) : assets.length === 0 ? (
                    <div className="py-16 flex flex-col items-center text-center">
                        <Archive className="w-10 h-10 text-muted-foreground mb-3" />
                        <p className="text-muted-foreground font-medium">{t("activos.emptyTitle")}</p>
                        <p className="text-muted-foreground text-sm mt-1 mb-4">{t("activos.emptyDescription")}</p>
                        <Button variant="ghost" size="sm" onClick={openCreate} className="text-primary">
                            {t("activos.addFirstAsset")}
                        </Button>
                    </div>
                ) : (
                    <div className="divide-y divide-border">
                        {assets.map(asset => {
                            const dep = calcDepreciation(asset);
                            const net = Number(asset.purchase_value) - dep;
                            const monthly = (Number(asset.purchase_value) - Number(asset.residual_value)) / (Number(asset.useful_life_years) * 12);
                            const cat = categories.find(c => c.value === asset.category) || categories[4];
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
                                            <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-primary hover:bg-primary/10" onClick={() => openEdit(asset)} aria-label={t("activos.editAsset")}>
                                                <Pencil className="w-3.5 h-3.5" aria-hidden="true" />
                                            </Button>
                                            <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-red-400 hover:bg-red-500/10" onClick={() => handleDelete(asset.id, asset.name)} disabled={deletingId === asset.id} aria-label={t("activos.deleteAsset")}>
                                                {deletingId === asset.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" aria-hidden="true" /> : <Trash2 className="w-3.5 h-3.5" aria-hidden="true" />}
                                            </Button>
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
