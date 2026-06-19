"use client";

import { useTranslations } from "next-intl";
import { X, Loader2 } from "lucide-react";

type FormState = { name: string; nif: string; email: string; address: string; city: string; postal_code: string };

interface Props {
    editingId: string | null;
    form: FormState;
    setForm: React.Dispatch<React.SetStateAction<FormState>>;
    saving: boolean;
    onClose: () => void;
    onSubmit: (e: React.FormEvent) => void;
}

export function ProveedorModal({ editingId, form, setForm, saving, onClose, onSubmit }: Props) {
    const t = useTranslations("compras.proveedores.modal");
    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
            <div className="bg-card border border-border rounded-2xl p-8 w-full max-w-lg shadow-2xl">
                <div className="flex items-center justify-between mb-6">
                    <h2 className="text-lg font-bold text-foreground">{editingId ? t("editTitle") : t("newTitle")}</h2>
                    <button onClick={onClose} className="text-muted-foreground hover:text-foreground transition-colors" aria-label={t("close")}>
                        <X className="w-5 h-5" aria-hidden="true" />
                    </button>
                </div>
                <form onSubmit={onSubmit} className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                        <div className="col-span-2">
                            <label className="block text-xs text-muted-foreground mb-1.5 font-medium">{t("name")}</label>
                            <input
                                type="text" required value={form.name}
                                onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                                className="w-full bg-card border border-border text-foreground text-sm rounded-xl px-3 py-2.5 focus:outline-none focus:border-primary transition-colors"
                                placeholder={t("namePlaceholder")}
                            />
                        </div>
                        <div>
                            <label className="block text-xs text-muted-foreground mb-1.5 font-medium">{t("nif")}</label>
                            <input
                                type="text" value={form.nif}
                                onChange={e => setForm(f => ({ ...f, nif: e.target.value }))}
                                className="w-full bg-card border border-border text-foreground text-sm rounded-xl px-3 py-2.5 focus:outline-none focus:border-primary transition-colors"
                                placeholder={t("nifPlaceholder")}
                            />
                        </div>
                        <div>
                            <label className="block text-xs text-muted-foreground mb-1.5 font-medium">{t("email")}</label>
                            <input
                                type="email" value={form.email}
                                onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                                className="w-full bg-card border border-border text-foreground text-sm rounded-xl px-3 py-2.5 focus:outline-none focus:border-primary transition-colors"
                                placeholder={t("emailPlaceholder")}
                            />
                        </div>
                        <div className="col-span-2">
                            <label className="block text-xs text-muted-foreground mb-1.5 font-medium">{t("address")}</label>
                            <input
                                type="text" value={form.address}
                                onChange={e => setForm(f => ({ ...f, address: e.target.value }))}
                                className="w-full bg-card border border-border text-foreground text-sm rounded-xl px-3 py-2.5 focus:outline-none focus:border-primary transition-colors"
                                placeholder={t("addressPlaceholder")}
                            />
                        </div>
                        <div>
                            <label className="block text-xs text-muted-foreground mb-1.5 font-medium">{t("city")}</label>
                            <input
                                type="text" value={form.city}
                                onChange={e => setForm(f => ({ ...f, city: e.target.value }))}
                                className="w-full bg-card border border-border text-foreground text-sm rounded-xl px-3 py-2.5 focus:outline-none focus:border-primary transition-colors"
                                placeholder={t("cityPlaceholder")}
                            />
                        </div>
                        <div>
                            <label className="block text-xs text-muted-foreground mb-1.5 font-medium">{t("postalCode")}</label>
                            <input
                                type="text" value={form.postal_code}
                                onChange={e => setForm(f => ({ ...f, postal_code: e.target.value }))}
                                className="w-full bg-card border border-border text-foreground text-sm rounded-xl px-3 py-2.5 focus:outline-none focus:border-primary transition-colors"
                                placeholder={t("postalCodePlaceholder")}
                            />
                        </div>
                    </div>
                    <div className="flex gap-3 pt-2">
                        <button type="button" onClick={onClose} className="flex-1 py-2.5 rounded-xl border border-border text-muted-foreground text-sm hover:bg-accent/50 transition-colors">
                            {t("cancel")}
                        </button>
                        <button type="submit" disabled={saving} className="flex-1 py-2.5 rounded-xl bg-primary hover:bg-primary text-foreground text-sm font-medium transition-colors disabled:opacity-50 flex items-center justify-center gap-2">
                            {saving && <Loader2 className="w-4 h-4 animate-spin" />}
                            {editingId ? t("save") : t("create")}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
