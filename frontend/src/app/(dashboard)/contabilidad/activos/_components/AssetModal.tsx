"use client";

import { Archive, X, Loader2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { type FormState, emptyForm } from "../_hooks/useActivos";

const fmt = (n: number) => n.toLocaleString("es-ES", { style: "currency", currency: "EUR" });

const buildCategories = (t: (k: string) => string) => [
    { value: "equipment", label: t("activos.categoryEquipment") },
    { value: "furniture", label: t("activos.categoryFurniture") },
    { value: "vehicle", label: t("activos.categoryVehicle") },
    { value: "intangible", label: t("activos.categoryIntangible") },
    { value: "other", label: t("activos.categoryOther") },
];

const buildAccountCodes = (t: (k: string) => string) => [
    { code: "210", label: `210 — ${t("assetModal.acc210")}` },
    { code: "211", label: `211 — ${t("assetModal.acc211")}` },
    { code: "212", label: `212 — ${t("assetModal.acc212")}` },
    { code: "213", label: `213 — ${t("assetModal.acc213")}` },
    { code: "214", label: `214 — ${t("assetModal.acc214")}` },
    { code: "215", label: `215 — ${t("assetModal.acc215")}` },
    { code: "216", label: `216 — ${t("assetModal.acc216")}` },
    { code: "217", label: `217 — ${t("assetModal.acc217")}` },
    { code: "218", label: `218 — ${t("assetModal.acc218")}` },
    { code: "219", label: `219 — ${t("assetModal.acc219")}` },
    { code: "200", label: `200 — ${t("assetModal.acc200")}` },
    { code: "201", label: `201 — ${t("assetModal.acc201")}` },
    { code: "203", label: `203 — ${t("assetModal.acc203")}` },
    { code: "205", label: `205 — ${t("assetModal.acc205")}` },
    { code: "206", label: `206 — ${t("assetModal.acc206")}` },
];

interface Props {
    editingId: string | null;
    form: FormState;
    saving: boolean;
    onClose: () => void;
    onSubmit: (e: React.FormEvent) => void;
    setField: (field: keyof FormState, val: string) => void;
}

export function AssetModal({ editingId, form, saving, onClose, onSubmit, setField }: Props) {
    const t = useTranslations("contabilidad");
    const categories = buildCategories(t);
    const accountCodes = buildAccountCodes(t);
    return (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-card border border-border rounded-2xl w-full max-w-2xl shadow-2xl max-h-[90vh] flex flex-col">
                <div className="p-5 border-b border-border flex justify-between items-center bg-muted flex-shrink-0">
                    <h2 className="text-lg font-medium text-foreground flex items-center gap-2">
                        <Archive className="w-4 h-4 text-primary" />
                        {editingId ? t("assetModal.editTitle") : t("assetModal.createTitle")}
                    </h2>
                    <button onClick={onClose} className="text-muted-foreground hover:text-foreground" aria-label={t("assetModal.closeAria")}>
                        <X className="w-5 h-5" aria-hidden="true" />
                    </button>
                </div>
                <form onSubmit={onSubmit} className="p-6 space-y-4 overflow-y-auto">
                    <div className="grid grid-cols-2 gap-4">
                        <div className="col-span-2">
                            <label className="block text-sm text-muted-foreground mb-1.5">{t("assetModal.labelName")}</label>
                            <input required type="text" value={form.name} onChange={e => setField("name", e.target.value)}
                                placeholder={t("assetModal.namePlaceholder")}
                                className="w-full bg-background border border-border rounded-lg px-4 py-2 text-foreground focus:outline-none focus:border-primary" />
                        </div>
                        <div>
                            <label className="block text-sm text-muted-foreground mb-1.5">{t("assetModal.labelCategory")}</label>
                            <select value={form.category} onChange={e => setField("category", e.target.value)}
                                className="w-full bg-background border border-border rounded-lg px-3 py-2 text-foreground focus:outline-none focus:border-primary">
                                {categories.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
                            </select>
                        </div>
                        <div>
                            <label className="block text-sm text-muted-foreground mb-1.5">{t("assetModal.labelAccount")}</label>
                            <select value={form.account_code} onChange={e => setField("account_code", e.target.value)}
                                className="w-full bg-background border border-border rounded-lg px-3 py-2 text-foreground focus:outline-none focus:border-primary">
                                {accountCodes.map(c => <option key={c.code} value={c.code}>{c.label}</option>)}
                            </select>
                        </div>
                        <div>
                            <label className="block text-sm text-muted-foreground mb-1.5">{t("assetModal.labelPurchaseDate")}</label>
                            <input required type="date" value={form.purchase_date} onChange={e => setField("purchase_date", e.target.value)}
                                className="w-full bg-background border border-border rounded-lg px-4 py-2 text-foreground focus:outline-none focus:border-primary" />
                        </div>
                        <div>
                            <label className="block text-sm text-muted-foreground mb-1.5">{t("assetModal.labelPurchaseValue")}</label>
                            <input required type="number" min="0" step="0.01" value={form.purchase_value} onChange={e => setField("purchase_value", e.target.value)}
                                placeholder="0.00"
                                className="w-full bg-background border border-border rounded-lg px-4 py-2 text-foreground focus:outline-none focus:border-primary" />
                        </div>
                        <div>
                            <label className="block text-sm text-muted-foreground mb-1.5">{t("assetModal.labelUsefulLife")}</label>
                            <input required type="number" min="1" max="100" step="0.5" value={form.useful_life_years} onChange={e => setField("useful_life_years", e.target.value)}
                                className="w-full bg-background border border-border rounded-lg px-4 py-2 text-foreground focus:outline-none focus:border-primary" />
                        </div>
                        <div>
                            <label className="block text-sm text-muted-foreground mb-1.5">{t("assetModal.labelResidualValue")}</label>
                            <input type="number" min="0" step="0.01" value={form.residual_value} onChange={e => setField("residual_value", e.target.value)}
                                className="w-full bg-background border border-border rounded-lg px-4 py-2 text-foreground focus:outline-none focus:border-primary" />
                        </div>
                        <div>
                            <label className="block text-sm text-muted-foreground mb-1.5">{t("assetModal.labelReference")}</label>
                            <input type="text" value={form.reference_invoice} onChange={e => setField("reference_invoice", e.target.value)}
                                placeholder={t("assetModal.optionalPlaceholder")}
                                className="w-full bg-background border border-border rounded-lg px-4 py-2 text-foreground focus:outline-none focus:border-primary" />
                        </div>
                        <div className="col-span-2">
                            <label className="block text-sm text-muted-foreground mb-1.5">{t("assetModal.labelNotes")}</label>
                            <textarea value={form.notes} onChange={e => setField("notes", e.target.value)}
                                className="w-full bg-background border border-border rounded-lg px-4 py-2 text-foreground focus:outline-none focus:border-primary resize-none h-16" />
                        </div>
                    </div>

                    {form.purchase_value && form.useful_life_years && (
                        <div className="bg-primary/5 border border-primary/20 rounded-xl p-3 text-xs text-muted-foreground">
                            <span className="text-primary font-medium">{t("assetModal.monthlyEstimate")}</span>
                            {fmt((parseFloat(form.purchase_value) - (parseFloat(form.residual_value) || 0)) / (parseFloat(form.useful_life_years) * 12))}
                            {" · "}{t("assetModal.usefulLifeInfo", { years: form.useful_life_years })}
                        </div>
                    )}

                    <div className="pt-2 flex justify-end gap-3">
                        <button type="button" onClick={onClose}
                            className="px-5 py-2.5 text-foreground hover:text-foreground transition-colors font-medium border border-border rounded-lg">
                            {t("assetModal.cancel")}
                        </button>
                        <button type="submit" disabled={saving || !form.name || !form.purchase_value}
                            className="inline-flex items-center gap-2 bg-primary hover:bg-primary text-foreground px-6 py-2.5 rounded-lg font-medium transition-colors shadow-lg shadow-primary/20 disabled:opacity-50">
                            {saving && <Loader2 className="w-4 h-4 animate-spin" />}
                            {editingId ? t("assetModal.save") : t("assetModal.add")}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
