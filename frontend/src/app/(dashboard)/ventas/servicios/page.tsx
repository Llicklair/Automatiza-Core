"use client";

import { Plus, Search, ShieldCheck, HeartHandshake, Loader2, Pencil, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { useServicios, fmt } from "./_hooks/useServicios";
import { ServiceModal } from "./_components/ServiceModal";

export default function ServicesPage() {
    const t = useTranslations("ventas");
    const tc = useTranslations("common");
    const {
        services, isLoading, search, setSearch,
        showModal, setShowModal,
        editingId, form, setForm,
        isSubmitting, deletingId,
        openCreate, openEdit, handleSubmit, handleDelete,
        filtered,
    } = useServicios();

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

            {showModal && (
                <ServiceModal
                    editingId={editingId}
                    form={form}
                    setForm={setForm}
                    isSubmitting={isSubmitting}
                    onClose={() => setShowModal(false)}
                    onSubmit={handleSubmit}
                />
            )}
        </div>
    );
}
