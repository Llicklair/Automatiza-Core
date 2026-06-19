/**
 * I18N.SEL — Settings selector de idioma.
 *
 * Solo se ofrece español hasta que existan traducciones reales (I18N.TR).
 * Los demás idiomas están comentados en `hooks/useLocale.ts`.
 */
"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { CheckCircle2, Globe, Info } from "lucide-react";
import { useToastStore } from "@/stores/toast";
import {
    SUPPORTED_LOCALES,
    getStoredLocale,
    setStoredLocale,
    type AppLocale,
} from "@/hooks/useLocale";
import { PageHeader } from "@/components/shared/PageHeader";
import { PageContainer } from "@/components/shared/PageContainer";

export default function IdiomaPage() {
    const t = useTranslations("configuracion");
    const router = useRouter();
    const toast = useToastStore();
    const [active, setActive] = useState<AppLocale>("es");

    useEffect(() => {
        setActive(getStoredLocale());
    }, []);

    function choose(locale: AppLocale) {
        setStoredLocale(locale);
        setActive(locale);
        toast.show(t("idioma.updated"), "success");
        // Refresh para que `i18n/request.ts` server-side lea el nuevo cookie.
        setTimeout(() => router.refresh(), 250);
    }

    return (
        <PageContainer width="3xl">
            <PageHeader
                title={t("idioma.title")}
                description={t("idioma.description")}
            />

            <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-3 flex items-start gap-2">
                <Info className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" aria-hidden="true" />
                <p className="text-xs text-muted-foreground leading-relaxed">
                    <strong className="text-foreground">{t("idioma.bannerLanguages")}</strong>{" "}
                    {t("idioma.bannerRest")}
                </p>
            </div>

            <div
                role="radiogroup"
                aria-label={t("idioma.title")}
                className="space-y-2"
            >
                {SUPPORTED_LOCALES.map((opt) => {
                    const isActive = active === opt.code;
                    return (
                        <button
                            key={opt.code}
                            type="button"
                            role="radio"
                            aria-checked={isActive}
                            onClick={() => choose(opt.code)}
                            className={`w-full flex items-center justify-between p-4 rounded-lg border transition-colors text-left ${isActive
                                ? "border-primary bg-primary/5 ring-1 ring-primary/30"
                                : "border-border bg-card hover:border-primary/50"
                                }`}
                        >
                            <div className="flex items-center gap-3 min-w-0">
                                <Globe
                                    className={`w-4 h-4 flex-shrink-0 ${isActive ? "text-primary" : "text-muted-foreground"}`}
                                    aria-hidden="true"
                                />
                                <div className="min-w-0">
                                    <p className="text-sm font-medium text-foreground">
                                        {opt.native}
                                    </p>
                                    <p className="text-xs text-muted-foreground">
                                        {opt.label}
                                    </p>
                                </div>
                            </div>
                            {isActive && (
                                <CheckCircle2
                                    className="w-4 h-4 text-primary flex-shrink-0"
                                    aria-label={t("idioma.activeLanguage")}
                                />
                            )}
                        </button>
                    );
                })}
            </div>

            <p className="text-xs text-muted-foreground">
                {t("idioma.reloadNote")}
            </p>
        </PageContainer>
    );
}
