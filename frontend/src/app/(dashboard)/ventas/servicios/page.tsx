"use client";

import { Plus, Search, ShieldCheck, HeartHandshake, Loader2, Pencil, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { useServicios, fmt } from "./_hooks/useServicios";
import { ServiceModal } from "./_components/ServiceModal";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

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
        <div className="p-8 max-w-[1400px] mx-auto space-y-6">
            <PageHeader
                title={t("serviceDatabase")}
                description={t("serviceSubtitle")}
                icon={HeartHandshake}
                actions={
                    <Button onClick={openCreate}>
                        <Plus className="w-4 h-4 mr-2" /> {t("newService")}
                    </Button>
                }
            />

            <div className="bg-card border border-border rounded-2xl overflow-hidden shadow-2xl">
                <div className="p-4 border-b border-border flex justify-between items-center bg-muted/30">
                    <div className="relative">
                        <Search className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
                        <Input
                            placeholder={t("serviceSearchPlaceholder")}
                            value={search}
                            onChange={e => setSearch(e.target.value)}
                            className="pl-10 w-72"
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
                                <th className="px-6 py-4 font-medium text-right text-primary">{t("servicePvpVat")}</th>
                                <th className="px-6 py-4 font-medium text-right">{t("serviceActions")}</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-border">
                            {isLoading ? (
                                <tr>
                                    <td colSpan={5} className="px-6 py-12 text-center">
                                        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary mx-auto" />
                                    </td>
                                </tr>
                            ) : filtered.length === 0 ? (
                                <tr>
                                    <td colSpan={5} className="px-6 py-16 text-center">
                                        <ShieldCheck className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
                                        <p className="text-muted-foreground font-medium">
                                            {services.length === 0 ? t("serviceEmptyTitle") : tc("noResults")}
                                        </p>
                                        {services.length === 0 && (
                                            <p className="text-muted-foreground text-sm mt-1">{t("serviceEmptyDescription")}</p>
                                        )}
                                    </td>
                                </tr>
                            ) : filtered.map(srv => {
                                const pvp = srv.price * (1 + srv.tax_percentage / 100);
                                return (
                                    <tr key={srv.id} className="hover:bg-muted/30 transition-colors group">
                                        <td className="px-6 py-4 font-mono text-muted-foreground text-xs">{srv.sku || "----"}</td>
                                        <td className="px-6 py-4">
                                            <span className="font-medium text-foreground">{srv.name}</span>
                                            {srv.description && <span className="block text-xs text-muted-foreground truncate max-w-xs">{srv.description}</span>}
                                        </td>
                                        <td className="px-6 py-4 text-right text-foreground">
                                            {fmt(srv.price)}
                                            <span className="text-[10px] text-muted-foreground block">+{srv.tax_percentage}% {t("taxVat")}</span>
                                        </td>
                                        <td className="px-6 py-4 text-right font-semibold text-primary">{fmt(pvp)}</td>
                                        <td className="px-6 py-4 text-right">
                                            <div className="flex items-center justify-end gap-2">
                                                <Button
                                                    variant="ghost"
                                                    size="icon"
                                                    className="h-8 w-8 text-muted-foreground hover:text-primary hover:bg-primary/10"
                                                    onClick={() => openEdit(srv)}
                                                    title={tc("edit")}
                                                >
                                                    <Pencil className="w-4 h-4" />
                                                </Button>
                                                <Button
                                                    variant="ghost"
                                                    size="icon"
                                                    className="h-8 w-8 text-muted-foreground hover:text-red-400 hover:bg-red-500/10"
                                                    onClick={() => handleDelete(srv.id, srv.name)}
                                                    disabled={deletingId === srv.id}
                                                    title={tc("delete")}
                                                >
                                                    {deletingId === srv.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                                                </Button>
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
