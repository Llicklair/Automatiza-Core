"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { Database, Trash2, Loader2, Sparkles } from "lucide-react";
import { onboarding, type DemoStatus } from "@/lib/api/onboarding";

/**
 * Tarjeta "Datos de ejemplo" del onboarding: siembra/borra una pyme demo
 * (clientes/productos/facturas) para que el producto se vea vivo en el trial.
 * Los datos demo salen en listados/analítica pero NUNCA en lo fiscal y son
 * borrables de golpe (ver backend services/onboarding/seed.py).
 */
export function DemoDataCard() {
    const t = useTranslations("primerosPasos.demoData");
    const [status, setStatus] = useState<DemoStatus | null>(null);
    const [busy, setBusy] = useState(false);
    const [confirming, setConfirming] = useState(false);
    const [msg, setMsg] = useState<string | null>(null);
    const [err, setErr] = useState(false);

    useEffect(() => {
        onboarding.demoStatus().then(setStatus).catch(() => { });
    }, []);

    const seeded = status?.seeded ?? false;

    const load = async () => {
        setBusy(true); setErr(false); setMsg(null);
        try {
            const r = await onboarding.seedDemo();
            setStatus({ seeded: true, counts: { clients: r.clients, products: r.products, invoices: r.invoices } });
            setMsg(r.already_seeded
                ? t("alreadyLoaded")
                : t("loaded", { clients: r.clients, products: r.products, invoices: r.invoices }));
        } catch {
            setErr(true); setMsg(t("error"));
        } finally {
            setBusy(false);
        }
    };

    const clear = async () => {
        setConfirming(false);
        setBusy(true); setErr(false); setMsg(null);
        try {
            await onboarding.clearDemo();
            setStatus({ seeded: false, counts: { clients: 0, products: 0, invoices: 0 } });
            setMsg(t("cleared"));
        } catch {
            setErr(true); setMsg(t("error"));
        } finally {
            setBusy(false);
        }
    };

    return (
        <div className="mb-8 bg-card border border-amber-500/30 rounded-2xl p-5">
            <div className="flex items-center gap-2 mb-2">
                <Sparkles className="w-4 h-4 text-amber-400" />
                <span className="text-xs font-semibold text-amber-400 uppercase tracking-wider">{t("label")}</span>
                {seeded && (
                    <span className="text-[10px] text-amber-300 bg-amber-500/10 border border-amber-500/30 px-2 py-0.5 rounded-full font-medium">
                        {t("badge")}
                    </span>
                )}
            </div>
            <h3 className="font-semibold text-sm text-foreground mb-1">{t("title")}</h3>
            <p className="text-xs text-muted-foreground mb-4">{t("description")}</p>

            <div className="flex items-center gap-3 flex-wrap">
                <button
                    onClick={load}
                    disabled={busy || seeded}
                    className="inline-flex items-center gap-2 bg-amber-500/15 border border-amber-500/40 text-amber-300 hover:bg-amber-500/25 disabled:opacity-50 disabled:cursor-not-allowed px-4 py-2 rounded-xl text-sm font-medium transition-colors"
                >
                    {busy && !seeded ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Database className="w-3.5 h-3.5" />}
                    {busy && !seeded ? t("loading") : t("load")}
                </button>

                {seeded && !confirming && (
                    <button
                        onClick={() => setConfirming(true)}
                        disabled={busy}
                        className="inline-flex items-center gap-2 bg-muted border border-border text-muted-foreground hover:bg-accent disabled:opacity-50 px-4 py-2 rounded-xl text-sm font-medium transition-colors"
                    >
                        {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Trash2 className="w-3.5 h-3.5" />}
                        {busy ? t("clearing") : t("clear")}
                    </button>
                )}

                {seeded && confirming && (
                    <div className="inline-flex items-center gap-2">
                        <span className="text-xs text-muted-foreground">{t("confirmClear")}</span>
                        <button
                            onClick={clear}
                            className="inline-flex items-center gap-1.5 bg-rose-500/15 border border-rose-500/40 text-rose-300 hover:bg-rose-500/25 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors"
                        >
                            <Trash2 className="w-3.5 h-3.5" />
                            {t("confirmYes")}
                        </button>
                        <button
                            onClick={() => setConfirming(false)}
                            className="px-3 py-1.5 rounded-lg text-xs font-medium border border-border text-muted-foreground hover:bg-accent transition-colors"
                        >
                            {t("cancel")}
                        </button>
                    </div>
                )}
            </div>

            {msg && (
                <p className={`text-xs mt-3 ${err ? "text-rose-400" : "text-emerald-400"}`}>{msg}</p>
            )}
        </div>
    );
}
