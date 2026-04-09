"use client";

import { useEffect, useState } from "react";
import { api, Product } from "@/lib/api";
import {
    Plus, Search, ShieldCheck, HeartHandshake, X, Loader2, Pencil, Trash2
} from "lucide-react";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";
import { logError } from "@/lib/logger";
import { useTranslations } from "next-intl";

type FormState = {
    name: string; sku: string; description: string;
    price: string; tax_percentage: string;
};

const emptyForm = (): FormState => ({
    name: "", sku: "", description: "", price: "", tax_percentage: "21"
});

const fmt = (val: number) =>
    new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" }).format(val);

export default function ServicesPage() {
    const toast = useToastStore();
    const t = useTranslations("ventas");
    const tc = useTranslations("common");
    const [services, setServices] = useState<Product[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [search, setSearch] = useState("");

    const [showModal, setShowModal] = useState(false);
    const [editingId, setEditingId] = useState<string | null>(null);
    const [form, setForm] = useState<FormState>(emptyForm());
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [deletingId, setDeletingId] = useState<string | null>(null);

    useEffect(() => { loadData(); }, []);

    const loadData = async () => {
        setIsLoading(true);
        try {
            const data = await api.erp.products.list({ limit: 200 });
            setServices(data.filter(p => p.item_type === "service"));
        } catch (error) {
            logError("ventas/servicios/page", error);
        } finally {
            setIsLoading(false);
        }
    };

    const openCreate = () => { setEditingId(null); setForm(emptyForm()); setShowModal(true); };
    const openEdit = (s: Product) => {
        setEditingId(s.id);
        setForm({ name: s.name, sku: s.sku || "", description: s.description || "", price: String(s.price), tax_percentage: String(s.tax_percentage) });
        setShowModal(true);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsSubmitting(true);
        const payload = {
            name: form.name, sku: form.sku || null, description: form.description || null,
            price: parseFloat(form.price) || 0,
            tax_percentage: parseFloat(form.tax_percentage),
            item_type: "service",
        };
        try {
            if (editingId) {
                const updated = await api.erp.products.update(editingId, payload);
                setServices(prev => prev.map(s => s.id === editingId ? updated : s));
            } else {
                const created = await api.erp.products.create(payload);
                setServices(prev => [created, ...prev]);
            }
            setShowModal(false);
        } catch (err: any) {
            toast.error(err?.message || t("serviceErrorSaving"));
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleDelete = async (id: string, name: string) => {
        if (!await showConfirm({ message: t("serviceDeleteConfirm", { name }), confirmLabel: tc("delete"), confirmVariant: "danger" })) return;
        setDeletingId(id);
        try {
            await api.erp.products.delete(id);
            setServices(prev => prev.filter(s => s.id !== id));
        } catch (err: any) {
            toast.error(err?.message || t("serviceErrorDeleting"));
        } finally {
            setDeletingId(null);
        }
    };

    const filtered = services.filter(s => {
        const q = search.toLowerCase();
        return s.name.toLowerCase().includes(q) || (s.sku || "").toLowerCase().includes(q) || (s.description || "").toLowerCase().includes(q);
    });

    return (
        <div className="min-h-screen bg-background text-foreground p-8">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-8">
                <div>
                    <h1 className="text-3xl font-light text-foreground flex items-center gap-3">
                        <div className="p-2 bg-purple-500/10 rounded-xl">
                            <HeartHandshake className="w-8 h-8 text-purple-400" />
                        </div>
                        {t("serviceDatabase")}
                    </h1>
                    <p className="text-muted-foreground mt-2 ml-14 text-sm max-w-2xl">
                        {t("serviceSubtitle")}
                    </p>
                </div>
                <button
                    onClick={openCreate}
                    className="flex items-center gap-2 bg-purple-600 hover:bg-purple-500 text-foreground shadow-lg shadow-purple-500/20 px-5 py-2.5 rounded-full font-medium transition-colors"
                >
                    <Plus className="w-4 h-4" />
                    {t("newService")}
                </button>
            </div>

            <div className="bg-card border border-border rounded-2xl overflow-hidden shadow-2xl">
                <div className="p-4 border-b border-border flex justify-between items-center bg-muted">
                    <div className="relative">
                        <Search className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
                        <input
                            type="text"
                            placeholder={t("serviceSearchPlaceholder")}
                            value={search}
                            onChange={e => setSearch(e.target.value)}
                            className="bg-background border border-border text-sm text-foreground rounded-lg pl-10 pr-4 py-2 focus:outline-none focus:border-purple-500 transition-colors w-72"
                        />
                    </div>
                </div>

                <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm whitespace-nowrap">
                        <thead className="bg-muted/50 text-muted-foreground border-b border-border">
                            <tr>
                                <th className="px-6 py-4 font-medium">{t("serviceRefId")}</th>
                                <th className="px-6 py-4 font-medium">{t("serviceOffered")}</th>
                                <th className="px-6 py-4 font-medium text-right">{t("servicePriceUnit")}</th>
                                <th className="px-6 py-4 font-medium text-right text-purple-400">{t("servicePvpVat")}</th>
                                <th className="px-6 py-4 font-medium text-right">{t("serviceActions")}</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-zinc-800/50">
                            {isLoading ? (
                                <tr><td colSpan={5} className="px-6 py-12 text-center">
                                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-purple-500 mx-auto" />
                                </td></tr>
                            ) : filtered.length === 0 ? (
                                <tr><td colSpan={5} className="px-6 py-16 text-center">
                                    <ShieldCheck className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
                                    <p className="text-muted-foreground font-medium">
                                        {services.length === 0 ? t("serviceEmptyTitle") : tc("noResults")}
                                    </p>
                                    {services.length === 0 && (
                                        <p className="text-muted-foreground text-sm mt-1">{t("serviceEmptyDescription")}</p>
                                    )}
                                </td></tr>
                            ) : filtered.map(srv => {
                                const pvp = srv.price * (1 + srv.tax_percentage / 100);
                                return (
                                    <tr key={srv.id} className="hover:bg-purple-500/[0.02] transition-colors group">
                                        <td className="px-6 py-4 font-mono text-muted-foreground text-xs">{srv.sku || "----"}</td>
                                        <td className="px-6 py-4">
                                            <span className="font-medium text-foreground">{srv.name}</span>
                                            {srv.description && <span className="block text-xs text-muted-foreground truncate max-w-xs">{srv.description}</span>}
                                        </td>
                                        <td className="px-6 py-4 text-right text-foreground">
                                            {fmt(srv.price)}
                                            <span className="text-[10px] text-muted-foreground block">+{srv.tax_percentage}% {t("taxVat")}</span>
                                        </td>
                                        <td className="px-6 py-4 text-right font-semibold text-purple-400">{fmt(pvp)}</td>
                                        <td className="px-6 py-4 text-right">
                                            <div className="flex items-center justify-end gap-2">
                                                <button
                                                    onClick={() => openEdit(srv)}
                                                    className="p-1.5 text-muted-foreground hover:text-purple-400 hover:bg-purple-500/10 rounded-lg transition-colors"
                                                    title={tc("edit")}
                                                >
                                                    <Pencil className="w-4 h-4" />
                                                </button>
                                                <button
                                                    onClick={() => handleDelete(srv.id, srv.name)}
                                                    disabled={deletingId === srv.id}
                                                    className="p-1.5 text-muted-foreground hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors disabled:opacity-50"
                                                    title={tc("delete")}
                                                >
                                                    {deletingId === srv.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Modal crear/editar */}
            {showModal && (
                <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                    <div className="bg-card border border-border rounded-2xl w-full max-w-xl overflow-hidden shadow-2xl">
                        <div className="p-5 border-b border-border flex justify-between items-center bg-muted">
                            <h2 className="text-lg font-medium text-foreground flex items-center gap-2">
                                <HeartHandshake className="w-4 h-4 text-purple-400" />
                                {editingId ? t("editService") : t("newService")}
                            </h2>
                            <button onClick={() => setShowModal(false)} className="text-muted-foreground hover:text-foreground">
                                <X className="w-5 h-5" />
                            </button>
                        </div>
                        <form onSubmit={handleSubmit} className="p-6 space-y-5">
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm text-muted-foreground mb-1.5">{t("name")} *</label>
                                    <input
                                        type="text"
                                        required
                                        value={form.name}
                                        onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                                        className="w-full bg-background border border-border rounded-lg px-4 py-2 text-foreground focus:outline-none focus:border-purple-500"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm text-muted-foreground mb-1.5">{t("serviceSkuRef")}</label>
                                    <input
                                        type="text"
                                        value={form.sku}
                                        onChange={e => setForm(f => ({ ...f, sku: e.target.value }))}
                                        placeholder={t("serviceOptional")}
                                        className="w-full bg-background border border-border rounded-lg px-4 py-2 text-foreground focus:outline-none focus:border-purple-500 font-mono text-sm"
                                    />
                                </div>
                            </div>
                            <div>
                                <label className="block text-sm text-muted-foreground mb-1.5">{t("descriptionLabel")}</label>
                                <textarea
                                    value={form.description}
                                    onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                                    className="w-full bg-background border border-border rounded-lg px-4 py-2 text-foreground focus:outline-none focus:border-purple-500 resize-none h-20"
                                />
                            </div>
                            <div className="grid grid-cols-2 gap-4 border-t border-border pt-4">
                                <div>
                                    <label className="block text-sm text-muted-foreground mb-1.5">{t("serviceBasePriceEur")} *</label>
                                    <input
                                        type="number"
                                        required
                                        min="0"
                                        step="0.01"
                                        value={form.price}
                                        onChange={e => setForm(f => ({ ...f, price: e.target.value }))}
                                        className="w-full bg-background border border-border rounded-lg px-4 py-2 text-foreground focus:outline-none focus:border-purple-500"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm text-muted-foreground mb-1.5">{t("serviceVatPercent")}</label>
                                    <select
                                        value={form.tax_percentage}
                                        onChange={e => setForm(f => ({ ...f, tax_percentage: e.target.value }))}
                                        className="w-full bg-background border border-border rounded-lg px-3 py-2 text-foreground focus:outline-none focus:border-purple-500"
                                    >
                                        <option value="21">21%</option>
                                        <option value="10">{t("serviceVatReduced")}</option>
                                        <option value="4">{t("serviceVatSuperReduced")}</option>
                                        <option value="0">{t("serviceVatExempt")}</option>
                                    </select>
                                </div>
                            </div>
                            <div className="pt-4 flex justify-end gap-3">
                                <button
                                    type="button"
                                    onClick={() => setShowModal(false)}
                                    className="px-5 py-2.5 text-foreground hover:text-foreground transition-colors font-medium border border-border rounded-lg"
                                >
                                    {tc("cancel")}
                                </button>
                                <button
                                    type="submit"
                                    disabled={isSubmitting || !form.name || !form.price}
                                    className="inline-flex items-center gap-2 bg-purple-600 hover:bg-purple-500 text-foreground px-6 py-2.5 rounded-lg font-medium transition-colors shadow-lg shadow-purple-500/20 disabled:opacity-50"
                                >
                                    {isSubmitting && <Loader2 className="w-4 h-4 animate-spin" />}
                                    {editingId ? tc("save") : t("createService")}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
