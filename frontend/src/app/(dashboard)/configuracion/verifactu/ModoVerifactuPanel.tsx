/**
 * FAC.MODE — Settings del modo de remisión Verifactu.
 *
 * Dos modos según RD 1007/2023:
 *   - voluntary    — VERI*FACTU: cada factura se envía a AEAT al emitirse
 *   - no_remission — SIF puro: cadena hash local, sin envío automático
 *
 * Hasta DEC.14 (alta colaborador social) y PRES.0 (cert representación)
 * completados, voluntary no funciona en producción — la UI lo señala.
 */
"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { CheckCircle2, Info, Loader2, ShieldAlert } from "lucide-react";
import { api } from "@/lib/api";
import type { VerifactuConfig, VerifactuMode } from "@/lib/api/verifactuConfig";
import { useToastStore } from "@/stores/toast";

export function ModoVerifactuPanel() {
    const t = useTranslations("configuracion");
    const [data, setData] = useState<VerifactuConfig | null>(null);
    const [loading, setLoading] = useState(true);
    const [busy, setBusy] = useState(false);
    const toast = useToastStore();

    const load = useCallback(async () => {
        setLoading(true);
        try {
            const res = await api.verifactuConfig.get();
            setData(res);
        } catch (e: any) {
            toast.show(`${t("verifactu.errorPrefix")}: ${e.message}`, "error");
        } finally {
            setLoading(false);
        }
    }, [toast, t]);

    useEffect(() => {
        load();
    }, [load]);

    async function setMode(mode: VerifactuMode) {
        setBusy(true);
        try {
            const res = await api.verifactuConfig.set(mode);
            setData(res);
            toast.show(
                mode === "voluntary"
                    ? t("verifactu.modeVerifactuActivated")
                    : t("verifactu.modeNoRemissionActivated"),
                "success",
            );
        } catch (e: any) {
            toast.show(`${t("verifactu.errorPrefix")}: ${e.message}`, "error");
        } finally {
            setBusy(false);
        }
    }

    if (loading || !data) {
        return (
            <div className="p-8 flex items-center gap-3 text-muted-foreground">
                <Loader2 className="w-4 h-4 animate-spin" /> {t("verifactu.loading")}
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <header>
                <h1 className="text-2xl font-semibold text-foreground tracking-tight">
                    {t("verifactu.modeTitle")}
                </h1>
                <p className="mt-1 text-sm text-muted-foreground">
                    {t("verifactu.modeIntro")}
                </p>
            </header>

            <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-4 flex items-start gap-3">
                <ShieldAlert
                    className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5"
                    aria-hidden="true"
                />
                <p className="text-xs text-muted-foreground leading-relaxed">
                    {t.rich("verifactu.modeWarning", {
                        strong: (chunks) => <strong>{chunks}</strong>,
                    })}
                </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <ModeCard
                    selected={data.mode === "no_remission"}
                    label={t("verifactu.noRemissionLabel")}
                    description={t("verifactu.noRemissionDesc")}
                    bullets={[
                        t("verifactu.noRemissionBullet1"),
                        t("verifactu.noRemissionBullet2"),
                        t("verifactu.noRemissionBullet3"),
                    ]}
                    onSelect={() => setMode("no_remission")}
                    busy={busy}
                />
                <ModeCard
                    selected={data.mode === "voluntary"}
                    label={t("verifactu.voluntaryLabel")}
                    description={t("verifactu.voluntaryDesc")}
                    bullets={[
                        t("verifactu.voluntaryBullet1"),
                        t("verifactu.voluntaryBullet2"),
                        t("verifactu.voluntaryBullet3"),
                    ]}
                    onSelect={() => setMode("voluntary")}
                    busy={busy}
                    highlight
                />
            </div>

            <p className="text-xs text-muted-foreground">
                {t("verifactu.lastChange")}: {new Date(data.updated_at).toLocaleString("es-ES")}
                {data.is_default && ` · ${t("verifactu.defaultValue")}`}
            </p>
        </div>
    );
}

function ModeCard({
    selected,
    label,
    description,
    bullets,
    onSelect,
    busy,
    highlight,
}: {
    selected: boolean;
    label: string;
    description: string;
    bullets: string[];
    onSelect: () => void;
    busy: boolean;
    highlight?: boolean;
}) {
    const t = useTranslations("configuracion");
    return (
        <article
            className={`rounded-lg border p-5 transition-colors ${selected
                ? "border-primary bg-primary/5 ring-1 ring-primary/30"
                : "border-border bg-card hover:border-primary/50"
                }`}
        >
            <div className="flex items-center justify-between mb-1.5">
                <h2 className="text-sm font-semibold text-foreground">{label}</h2>
                {selected && (
                    <CheckCircle2
                        className="w-4 h-4 text-primary"
                        aria-label={t("verifactu.modeActiveAria")}
                    />
                )}
                {highlight && !selected && (
                    <span
                        className="text-[10px] uppercase tracking-wider text-primary border border-primary/30 rounded px-1.5 py-0.5"
                        aria-hidden="true"
                    >
                        {t("verifactu.recommended")}
                    </span>
                )}
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed mb-3">
                {description}
            </p>
            <ul className="space-y-1 mb-4">
                {bullets.map((b) => (
                    <li
                        key={b}
                        className="flex items-start gap-2 text-xs text-foreground"
                    >
                        <Info
                            className="w-3 h-3 text-primary flex-shrink-0 mt-0.5"
                            aria-hidden="true"
                        />
                        {b}
                    </li>
                ))}
            </ul>
            <button
                type="button"
                onClick={onSelect}
                disabled={busy || selected}
                aria-pressed={selected}
                className={`w-full px-3 py-2 rounded-md text-sm font-medium transition-colors disabled:cursor-default ${selected
                    ? "bg-primary/15 text-primary"
                    : "bg-primary text-foreground hover:bg-primary/90"
                    }`}
            >
                {selected ? t("verifactu.active") : t("verifactu.activateMode")}
            </button>
        </article>
    );
}
