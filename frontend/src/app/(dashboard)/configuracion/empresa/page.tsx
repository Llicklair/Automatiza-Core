"use client";

import { useTranslations } from "next-intl";
import { Loader2, Save } from "lucide-react";
import { LogoSection } from "./_components/LogoSection";
import { useConfiguracionEmpresa } from "./_hooks/useConfiguracionEmpresa";
import { PageContainer } from "@/components/shared/PageContainer";

export default function EmpresaConfigPage() {
    const t = useTranslations("configuracion");
    const {
        name, setName,
        nif, setNif,
        address, setAddress,
        phone, setPhone,
        contactEmail, setContactEmail,
        loading, saving, error, success,
        handleSave,
    } = useConfiguracionEmpresa();

    return (
        <PageContainer width="3xl">
            <div>
                <h1 className="text-3xl font-bold text-foreground mb-1">{t("empresa.title")}</h1>
                <p className="text-muted-foreground text-sm mt-2">
                    {t("empresa.subtitle")}
                </p>
                <div className="mt-3 p-4 bg-primary/10 border border-primary/20 rounded-xl text-xs text-primary">
                    {t.rich("empresa.importantNote", {
                        strong: (chunks) => <strong>{chunks}</strong>,
                        i: (chunks) => <i>{chunks}</i>,
                    })}
                </div>
            </div>

            <div className="bg-card border border-border rounded-2xl p-6">
                {loading ? (
                    <div className="flex items-center justify-center gap-2 text-muted-foreground py-10">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        {t("empresa.loading")}
                    </div>
                ) : (
                    <form onSubmit={handleSave} className="space-y-5">
                        <div className="space-y-1.5">
                            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                                {t("empresa.nameLabel")}
                            </label>
                            <input
                                type="text"
                                required
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                className="w-full bg-muted border border-border rounded-xl px-4 py-2.5 text-sm text-foreground focus:border-primary/20 outline-none"
                                placeholder={t("empresa.namePlaceholder")}
                            />
                        </div>

                        <div className="space-y-1.5">
                            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                                {t("empresa.nifLabel")}
                            </label>
                            <input
                                type="text"
                                required
                                value={nif}
                                onChange={(e) => setNif(e.target.value.toUpperCase())}
                                className="w-full bg-muted border border-border rounded-xl px-4 py-2.5 text-sm text-foreground focus:border-primary/20 outline-none uppercase"
                                placeholder="B12345678"
                            />
                        </div>

                        <div className="space-y-1.5">
                            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                                {t("empresa.addressLabel")}
                            </label>
                            <input
                                type="text"
                                value={address}
                                onChange={(e) => setAddress(e.target.value)}
                                className="w-full bg-muted border border-border rounded-xl px-4 py-2.5 text-sm text-foreground focus:border-primary/20 outline-none"
                                placeholder={t("empresa.addressPlaceholder")}
                            />
                        </div>

                        <div className="space-y-1.5">
                            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                                {t("empresa.phoneLabel")}
                            </label>
                            <input
                                type="tel"
                                value={phone}
                                onChange={(e) => setPhone(e.target.value)}
                                className="w-full bg-muted border border-border rounded-xl px-4 py-2.5 text-sm text-foreground focus:border-primary/20 outline-none"
                                placeholder="+34 600 000 000"
                            />
                        </div>

                        <div className="space-y-1.5">
                            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                                {t("empresa.contactEmailLabel")}
                            </label>
                            <input
                                type="email"
                                value={contactEmail}
                                onChange={(e) => setContactEmail(e.target.value)}
                                className="w-full bg-muted border border-border rounded-xl px-4 py-2.5 text-sm text-foreground focus:border-primary/20 outline-none"
                                placeholder="facturacion@miempresa.com"
                            />
                        </div>

                        {error && (
                            <p className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-xl px-3 py-2">
                                {error}
                            </p>
                        )}
                        {success && (
                            <p className="text-sm text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded-xl px-3 py-2">
                                {success}
                            </p>
                        )}

                        <div className="pt-3 border-t border-border flex justify-end">
                            <button
                                type="submit"
                                disabled={saving}
                                className="inline-flex items-center gap-2 bg-primary hover:bg-primary disabled:opacity-50 text-foreground px-5 py-2.5 rounded-xl text-sm font-medium transition shadow-lg shadow-primary/20"
                            >
                                {saving ? (
                                    <>
                                        <Loader2 className="w-4 h-4 animate-spin" />
                                        {t("empresa.saving")}
                                    </>
                                ) : (
                                    <>
                                        <Save className="w-4 h-4" />
                                        {t("empresa.saveChanges")}
                                    </>
                                )}
                            </button>
                        </div>
                    </form>
                )}
            </div>

            <LogoSection />
        </PageContainer>
    );
}
