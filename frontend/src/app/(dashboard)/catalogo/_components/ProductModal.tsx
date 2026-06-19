"use client";

import { Package, DollarSign, Loader2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { X } from "lucide-react";

type FormState = {
    name: string; sku: string; barcode: string; description: string;
    category: string; location: string; unit: string;
    price: string; cost_price: string; tax_percentage: string;
    item_type: string; is_active: boolean;
};

interface Props {
    editingId: string | null;
    form: FormState;
    onChange: (f: FormState) => void;
    onSubmit: (e: React.FormEvent) => void;
    onClose: () => void;
    isSubmitting: boolean;
}

export function ProductModal({ editingId, form, onChange, onSubmit, onClose, isSubmitting }: Props) {
    const t = useTranslations("catalogo");
    const tc = useTranslations("common");
    return (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-card border border-border rounded-2xl w-full max-w-xl overflow-hidden shadow-2xl">
                <div className="p-5 border-b border-border flex justify-between items-center bg-muted">
                    <h2 className="text-lg font-medium text-foreground flex items-center gap-2">
                        <Package className="w-4 h-4 text-primary" />
                        {editingId ? t("modal.editTitle") : t("modal.newTitle")}
                    </h2>
                    <Button variant="ghost" size="icon" className="h-8 w-8" onClick={onClose} aria-label={t("modal.closeAria")}>
                        <X className="h-5 w-5" aria-hidden="true" />
                    </Button>
                </div>

                <form onSubmit={onSubmit} className="p-6 space-y-5">
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm text-muted-foreground mb-1.5">{t("fields.nameRequired")}</label>
                            <input
                                type="text"
                                required
                                value={form.name}
                                onChange={e => onChange({ ...form, name: e.target.value })}
                                className="w-full bg-background border border-border rounded-lg px-4 py-2 text-foreground focus:outline-none focus:border-primary transition-colors"
                            />
                        </div>
                        <div>
                            <label className="block text-sm text-muted-foreground mb-1.5">{t("fields.sku")}</label>
                            <input
                                type="text"
                                value={form.sku}
                                onChange={e => onChange({ ...form, sku: e.target.value })}
                                placeholder={t("fields.skuPlaceholder")}
                                className="w-full bg-background border border-border rounded-lg px-4 py-2 text-foreground focus:outline-none focus:border-primary font-mono text-sm transition-colors"
                            />
                        </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm text-muted-foreground mb-1.5">{t("fields.barcode")}</label>
                            <input
                                type="text"
                                value={form.barcode}
                                onChange={e => onChange({ ...form, barcode: e.target.value })}
                                placeholder={t("fields.barcodePlaceholder")}
                                className="w-full bg-background border border-border rounded-lg px-4 py-2 text-foreground focus:outline-none focus:border-primary font-mono text-sm transition-colors"
                            />
                        </div>
                        <div>
                            <label className="block text-sm text-muted-foreground mb-1.5">{t("fields.category")}</label>
                            <input
                                type="text"
                                value={form.category}
                                onChange={e => onChange({ ...form, category: e.target.value })}
                                placeholder={t("fields.categoryPlaceholder")}
                                className="w-full bg-background border border-border rounded-lg px-4 py-2 text-foreground focus:outline-none focus:border-primary transition-colors"
                            />
                        </div>
                    </div>
                    <div>
                        <label className="block text-sm text-muted-foreground mb-1.5">{t("fields.location")}</label>
                        <input
                            type="text"
                            value={form.location}
                            onChange={e => onChange({ ...form, location: e.target.value })}
                            placeholder={t("fields.locationPlaceholder")}
                            className="w-full bg-background border border-border rounded-lg px-4 py-2 text-foreground focus:outline-none focus:border-primary transition-colors"
                        />
                    </div>
                    <div>
                        <label className="block text-sm text-muted-foreground mb-1.5">{t("fields.description")}</label>
                        <textarea
                            value={form.description}
                            onChange={e => onChange({ ...form, description: e.target.value })}
                            className="w-full bg-background border border-border rounded-lg px-4 py-2 text-foreground focus:outline-none focus:border-primary resize-none h-20 transition-colors"
                        />
                    </div>
                    <div className="grid grid-cols-3 gap-4 border-t border-border pt-4">
                        <div>
                            <label className="block text-sm text-muted-foreground mb-1.5">{t("fields.nature")}</label>
                            <select
                                value={form.item_type}
                                onChange={e => onChange({ ...form, item_type: e.target.value })}
                                className="w-full bg-background border border-border rounded-lg px-3 py-2 text-foreground focus:outline-none focus:border-primary transition-colors"
                            >
                                <option value="product">{t("nature.product")}</option>
                                <option value="service">{t("nature.service")}</option>
                            </select>
                        </div>
                        <div>
                            <label className="block text-sm text-muted-foreground mb-1.5">{t("fields.unit")}</label>
                            <select
                                value={form.unit}
                                onChange={e => onChange({ ...form, unit: e.target.value })}
                                className="w-full bg-background border border-border rounded-lg px-3 py-2 text-foreground focus:outline-none focus:border-primary transition-colors"
                            >
                                <option value="ud">ud</option>
                                <option value="kg">kg</option>
                                <option value="g">g</option>
                                <option value="l">l</option>
                                <option value="ml">ml</option>
                                <option value="m">m</option>
                                <option value="m2">m²</option>
                                <option value="h">h</option>
                            </select>
                        </div>
                        <div>
                            <label className="block text-sm text-muted-foreground mb-1.5">{t("fields.vat")}</label>
                            <select
                                value={form.tax_percentage}
                                onChange={e => onChange({ ...form, tax_percentage: e.target.value })}
                                className="w-full bg-background border border-border rounded-lg px-3 py-2 text-foreground focus:outline-none focus:border-primary transition-colors"
                            >
                                <option value="21">{t("vat.standard")}</option>
                                <option value="10">{t("vat.reduced")}</option>
                                <option value="4">{t("vat.superReduced")}</option>
                                <option value="0">{t("vat.exempt")}</option>
                            </select>
                        </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm text-muted-foreground mb-1.5">{t("fields.salePriceRequired")}</label>
                            <div className="relative">
                                <DollarSign className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
                                <input
                                    type="number"
                                    required
                                    min="0"
                                    step="0.01"
                                    value={form.price}
                                    onChange={e => onChange({ ...form, price: e.target.value })}
                                    className="w-full bg-background border border-border rounded-lg pl-9 pr-3 py-2 text-foreground focus:outline-none focus:border-primary transition-colors"
                                />
                            </div>
                        </div>
                        <div>
                            <label className="block text-sm text-muted-foreground mb-1.5">{t("fields.costPrice")}</label>
                            <div className="relative">
                                <DollarSign className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
                                <input
                                    type="number"
                                    min="0"
                                    step="0.01"
                                    value={form.cost_price}
                                    onChange={e => onChange({ ...form, cost_price: e.target.value })}
                                    placeholder={t("fields.costPricePlaceholder")}
                                    className="w-full bg-background border border-border rounded-lg pl-9 pr-3 py-2 text-foreground focus:outline-none focus:border-primary transition-colors"
                                />
                            </div>
                        </div>
                    </div>
                    <div className="flex items-center gap-2 pt-2">
                        <input
                            id="catalog-product-active"
                            type="checkbox"
                            checked={form.is_active}
                            onChange={e => onChange({ ...form, is_active: e.target.checked })}
                            className="h-4 w-4 rounded border-border accent-primary"
                        />
                        <label htmlFor="catalog-product-active" className="text-sm text-foreground cursor-pointer">
                            {t("fields.active")} <span className="text-xs text-muted-foreground">{t("fields.activeHint")}</span>
                        </label>
                    </div>
                    <div className="pt-4 flex justify-end gap-3">
                        <Button type="button" variant="outline" onClick={onClose}>
                            {tc("cancel")}
                        </Button>
                        <Button type="submit" disabled={isSubmitting || !form.name || !form.price}>
                            {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            {editingId ? t("modal.saveChanges") : t("modal.create")}
                        </Button>
                    </div>
                </form>
            </div>
        </div>
    );
}
