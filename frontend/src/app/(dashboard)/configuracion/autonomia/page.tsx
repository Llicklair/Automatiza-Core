/**
 * SEC.AUT — Settings de autonomía por dominio.
 *
 * El admin elige cómo actúan los agentes en cada dominio:
 *   AUTO    — sin confirmación
 *   CONFIRM — prepara y espera clic humano
 *   MANUAL  — solo sugiere
 *
 * Defaults consensuados (banking_write=MANUAL, accounting=CONFIRM, etc.)
 * se muestran con badge "Default" mientras no se haya editado.
 */
"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { Loader2, RotateCcw, ShieldAlert } from "lucide-react";
import { api } from "@/lib/api";
import type { AutonomyMode, PolicyList } from "@/lib/api/autonomy";
import { useToastStore } from "@/stores/toast";
import { PageContainer } from "@/components/shared/PageContainer";

const buildDomainLabels = (t: (k: string) => string): Record<string, { name: string; hint: string }> => ({
    banking_read: { name: t("autonomia.domains.banking_read.name"), hint: t("autonomia.domains.banking_read.hint") },
    banking_write: { name: t("autonomia.domains.banking_write.name"), hint: t("autonomia.domains.banking_write.hint") },
    accounting: { name: t("autonomia.domains.accounting.name"), hint: t("autonomia.domains.accounting.hint") },
    billing: { name: t("autonomia.domains.billing.name"), hint: t("autonomia.domains.billing.hint") },
    crm: { name: t("autonomia.domains.crm.name"), hint: t("autonomia.domains.crm.hint") },
    hr: { name: t("autonomia.domains.hr.name"), hint: t("autonomia.domains.hr.hint") },
    documents: { name: t("autonomia.domains.documents.name"), hint: t("autonomia.domains.documents.hint") },
    email: { name: t("autonomia.domains.email.name"), hint: t("autonomia.domains.email.hint") },
    marketing: { name: t("autonomia.domains.marketing.name"), hint: t("autonomia.domains.marketing.hint") },
    recruitment: { name: t("autonomia.domains.recruitment.name"), hint: t("autonomia.domains.recruitment.hint") },
    rag: { name: t("autonomia.domains.rag.name"), hint: t("autonomia.domains.rag.hint") },
    validators: { name: t("autonomia.domains.validators.name"), hint: t("autonomia.domains.validators.hint") },
    uploads: { name: t("autonomia.domains.uploads.name"), hint: t("autonomia.domains.uploads.hint") },
});

const buildModeDescriptions = (t: (k: string) => string): Record<AutonomyMode, string> => ({
    AUTO: t("autonomia.modes.AUTO"),
    CONFIRM: t("autonomia.modes.CONFIRM"),
    MANUAL: t("autonomia.modes.MANUAL"),
});

const MODE_COLORS: Record<AutonomyMode, string> = {
    AUTO: "border-green-500/30 bg-green-500/5 text-green-500",
    CONFIRM: "border-amber-500/30 bg-amber-500/5 text-amber-500",
    MANUAL: "border-red-500/30 bg-red-500/5 text-red-500",
};

export default function AutonomyPage() {
    const t = useTranslations("configuracion");
    const DOMAIN_LABELS = buildDomainLabels(t);
    const MODE_DESCRIPTIONS = buildModeDescriptions(t);
    const [data, setData] = useState<PolicyList | null>(null);
    const [loading, setLoading] = useState(true);
    const [busy, setBusy] = useState<string | null>(null);
    const toast = useToastStore();

    const load = useCallback(async () => {
        setLoading(true);
        try {
            const res = await api.autonomy.list();
            setData(res);
        } catch (e: any) {
            toast.show(t("autonomia.error", { message: e.message }), "error");
        } finally {
            setLoading(false);
        }
    }, [toast, t]);

    useEffect(() => {
        load();
    }, [load]);

    async function changeMode(domain: string, mode: AutonomyMode) {
        setBusy(domain);
        try {
            await api.autonomy.set(domain, mode);
            await load();
        } catch (e: any) {
            toast.show(t("autonomia.error", { message: e.message }), "error");
        } finally {
            setBusy(null);
        }
    }

    async function resetDomain(domain: string) {
        setBusy(domain);
        try {
            await api.autonomy.reset(domain);
            await load();
        } catch (e: any) {
            toast.show(t("autonomia.error", { message: e.message }), "error");
        } finally {
            setBusy(null);
        }
    }

    if (loading || !data) {
        return (
            <div className="p-8 flex items-center gap-3 text-muted-foreground">
                <Loader2 className="w-4 h-4 animate-spin" /> {t("autonomia.loading")}
            </div>
        );
    }

    return (
        <PageContainer width="4xl">
            <header>
                <h1 className="text-2xl font-semibold text-foreground tracking-tight">
                    {t("autonomia.title")}
                </h1>
                <p className="mt-1 text-sm text-muted-foreground">
                    {t("autonomia.subtitle")}
                </p>
            </header>

            <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-4 flex items-start gap-3">
                <ShieldAlert className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" aria-hidden="true" />
                <p className="text-xs text-muted-foreground leading-relaxed">
                    {t.rich("autonomia.warning", { strong: (chunks) => <strong>{chunks}</strong> })}
                </p>
            </div>

            <ul className="space-y-2">
                {data.known_domains.map((domain) => {
                    const entry = data.policies[domain];
                    const meta = DOMAIN_LABELS[domain] ?? { name: domain, hint: "" };
                    const isBusy = busy === domain;
                    return (
                        <li
                            key={domain}
                            className="rounded-lg border border-border bg-card p-4 flex flex-col md:flex-row md:items-center gap-3"
                        >
                            <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2">
                                    <h2 className="text-sm font-medium text-foreground">{meta.name}</h2>
                                    {entry.is_default && (
                                        <span className="text-[10px] uppercase tracking-wider text-muted-foreground border border-border rounded px-1.5 py-0.5">
                                            {t("autonomia.defaultBadge")}
                                        </span>
                                    )}
                                </div>
                                {meta.hint && (
                                    <p className="mt-0.5 text-xs text-muted-foreground">{meta.hint}</p>
                                )}
                                <p className="mt-1 text-xs text-muted-foreground italic">
                                    {MODE_DESCRIPTIONS[entry.mode]}
                                </p>
                            </div>

                            <div className="flex items-center gap-1.5" role="group" aria-label={t("autonomia.modeGroupLabel", { name: meta.name })}>
                                {(["AUTO", "CONFIRM", "MANUAL"] as AutonomyMode[]).map((mode) => {
                                    const active = entry.mode === mode;
                                    return (
                                        <button
                                            key={mode}
                                            type="button"
                                            onClick={() => changeMode(domain, mode)}
                                            disabled={isBusy || active}
                                            aria-pressed={active}
                                            className={`px-2.5 py-1 rounded-md border text-xs font-medium transition-colors disabled:cursor-default ${active
                                                ? MODE_COLORS[mode]
                                                : "border-border text-muted-foreground hover:text-foreground hover:border-primary"
                                                }`}
                                        >
                                            {mode}
                                        </button>
                                    );
                                })}
                                {!entry.is_default && (
                                    <button
                                        type="button"
                                        onClick={() => resetDomain(domain)}
                                        disabled={isBusy}
                                        aria-label={t("autonomia.resetLabel", { name: meta.name })}
                                        className="ml-1 p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-background"
                                    >
                                        <RotateCcw className="w-3.5 h-3.5" />
                                    </button>
                                )}
                                {isBusy && <Loader2 className="w-3.5 h-3.5 animate-spin text-muted-foreground" aria-hidden="true" />}
                            </div>
                        </li>
                    );
                })}
            </ul>
        </PageContainer>
    );
}
