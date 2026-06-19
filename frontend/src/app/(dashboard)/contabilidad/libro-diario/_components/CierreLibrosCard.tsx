"use client";

import { useEffect, useState } from "react";
import {
    FileDown, Lock, Unlock, AlertTriangle, BookOpen, Library, BookText, Loader2,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api";
import type { AccountingPeriod, AccountingPeriodKind } from "@/lib/api/accounting";
import { Button } from "@/components/ui/button";
import { useToastStore } from "@/stores/toast";

function quarterRange(year: number, quarter: number): { start: string; end: string } {
    const startMonth = (quarter - 1) * 3;
    const endMonth = startMonth + 2;
    const start = new Date(year, startMonth, 1);
    const end = new Date(year, endMonth + 1, 0);
    const fmt = (d: Date) => d.toISOString().slice(0, 10);
    return { start: fmt(start), end: fmt(end) };
}

function currentQuarter(): { quarter: number; year: number } {
    const d = new Date();
    return { quarter: Math.floor(d.getMonth() / 3) + 1, year: d.getFullYear() };
}

export function CierreLibrosCard() {
    const t = useTranslations("contabilidad");
    const toast = useToastStore();
    const init = currentQuarter();
    const [quarter, setQuarter] = useState(init.quarter);
    const [year, setYear] = useState(init.year);
    const [periods, setPeriods] = useState<AccountingPeriod[]>([]);
    const [busy, setBusy] = useState<string | null>(null);
    const [showCloseModal, setShowCloseModal] = useState(false);
    const [closeNotes, setCloseNotes] = useState("");
    const [reopenModal, setReopenModal] = useState<{ id: string; label: string } | null>(null);
    const [reopenReason, setReopenReason] = useState("");

    const range = quarterRange(year, quarter);
    const periodLabel = t("cierre.periodLabel", { quarter, year });

    const loadPeriods = async () => {
        try {
            const res = await api.accounting.periods.list();
            setPeriods(res.items);
        } catch {
            // silent
        }
    };

    useEffect(() => { loadPeriods(); }, []);

    const currentPeriod = periods.find(
        (p) => p.kind === "quarter" && p.year === year && p.period_index === quarter,
    );
    const isClosed = currentPeriod?.status === "closed";

    const handleDownload = async (kind: "diario" | "mayor" | "anuales") => {
        setBusy(kind);
        try {
            if (kind === "diario") await api.accounting.libroDiarioPdf(range.start, range.end);
            else if (kind === "mayor") await api.accounting.libroMayorPdf(range.start, range.end);
            else await api.accounting.cuentasAnualesPdf(range.start, range.end);
            toast.success(t("cierre.toastPdfDownloaded"));
        } catch (e) {
            toast.error(e instanceof Error ? e.message : t("cierre.toastPdfError"));
        } finally {
            setBusy(null);
        }
    };

    const handleClosePeriod = async () => {
        setBusy("close");
        try {
            await api.accounting.periods.close({
                year, kind: "quarter" as AccountingPeriodKind, period_index: quarter,
                notes: closeNotes || undefined,
            });
            toast.success(t("cierre.toastClosed", { period: periodLabel }));
            setShowCloseModal(false);
            setCloseNotes("");
            loadPeriods();
        } catch (e) {
            toast.error(e instanceof Error ? e.message : t("cierre.toastCloseError"));
        } finally {
            setBusy(null);
        }
    };

    const handleReopen = async () => {
        if (!reopenModal) return;
        if (!reopenReason.trim()) {
            toast.error(t("cierre.toastReasonRequired"));
            return;
        }
        setBusy("reopen");
        try {
            await api.accounting.periods.reopen(reopenModal.id, reopenReason.trim());
            toast.success(t("cierre.toastReopened", { label: reopenModal.label }));
            setReopenModal(null);
            setReopenReason("");
            loadPeriods();
        } catch (e) {
            toast.error(e instanceof Error ? e.message : t("cierre.toastReopenError"));
        } finally {
            setBusy(null);
        }
    };

    return (
        <div className="rounded-2xl border border-primary/20 bg-gradient-to-br from-primary/5 via-card to-card p-5 space-y-4">
            <div className="flex items-start justify-between gap-4 flex-wrap">
                <div className="flex items-start gap-3">
                    <div className="flex-shrink-0 w-11 h-11 rounded-xl bg-primary/15 text-primary flex items-center justify-center">
                        <Library className="w-5 h-5" />
                    </div>
                    <div>
                        <h3 className="text-sm font-semibold text-foreground">{t("cierre.title")}</h3>
                        <p className="text-xs text-muted-foreground mt-0.5">
                            {t("cierre.description")}
                        </p>
                    </div>
                </div>
                {isClosed && (
                    <span className="inline-flex items-center gap-1.5 text-xs font-medium text-amber-500 bg-amber-500/10 border border-amber-500/30 px-2.5 py-1 rounded-full">
                        <Lock className="w-3.5 h-3.5" /> {t("cierre.badgeClosed", { period: periodLabel })}
                    </span>
                )}
            </div>

            <div className="flex items-center gap-2 flex-wrap">
                <select
                    value={quarter}
                    onChange={(e) => setQuarter(Number(e.target.value))}
                    className="h-9 px-2 rounded-md border border-border bg-card text-sm"
                >
                    {[1, 2, 3, 4].map((q) => <option key={q} value={q}>{t("cierre.quarterOption", { q })}</option>)}
                </select>
                <select
                    value={year}
                    onChange={(e) => setYear(Number(e.target.value))}
                    className="h-9 px-2 rounded-md border border-border bg-card text-sm"
                >
                    {[year - 1, year, year + 1].map((y) => <option key={y} value={y}>{y}</option>)}
                </select>
                <span className="text-xs text-muted-foreground">
                    {t("cierre.rangeLabel")} <span className="font-mono">{range.start}</span> → <span className="font-mono">{range.end}</span>
                </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                <Button
                    variant="outline"
                    onClick={() => handleDownload("diario")}
                    disabled={busy !== null}
                    className="justify-start"
                >
                    {busy === "diario" ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <BookOpen className="w-4 h-4 mr-2" />}
                    {t("cierre.btnDiarioPdf")}
                </Button>
                <Button
                    variant="outline"
                    onClick={() => handleDownload("mayor")}
                    disabled={busy !== null}
                    className="justify-start"
                >
                    {busy === "mayor" ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <BookText className="w-4 h-4 mr-2" />}
                    {t("cierre.btnMayorPdf")}
                </Button>
                <Button
                    variant="outline"
                    onClick={() => handleDownload("anuales")}
                    disabled={busy !== null}
                    className="justify-start"
                >
                    {busy === "anuales" ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <FileDown className="w-4 h-4 mr-2" />}
                    {t("cierre.btnAnualesPdf")}
                </Button>
            </div>

            <div className="flex items-center justify-between gap-3 pt-2 border-t border-border">
                {isClosed ? (
                    <>
                        <p className="text-xs text-muted-foreground">
                            <Lock className="w-3 h-3 inline mr-1" />
                            {t("cierre.closedOn")} {currentPeriod?.closed_at ? new Date(currentPeriod.closed_at).toLocaleDateString("es-ES") : "—"}
                        </p>
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setReopenModal({ id: currentPeriod!.id, label: periodLabel })}
                            className="text-amber-500 hover:text-amber-400"
                        >
                            <Unlock className="w-3.5 h-3.5 mr-1" /> {t("cierre.reopen")}
                        </Button>
                    </>
                ) : (
                    <>
                        <p className="text-xs text-muted-foreground">
                            {t("cierre.closeHint")}
                        </p>
                        <Button
                            onClick={() => setShowCloseModal(true)}
                            disabled={busy !== null}
                            size="sm"
                        >
                            <Lock className="w-3.5 h-3.5 mr-1" /> {t("cierre.closeButton", { period: periodLabel })}
                        </Button>
                    </>
                )}
            </div>

            {/* Modal cerrar */}
            {showCloseModal && (
                <div
                    className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4"
                    onClick={() => setShowCloseModal(false)}
                >
                    <div
                        className="bg-background border border-border rounded-xl max-w-md w-full p-5"
                        onClick={(e) => e.stopPropagation()}
                    >
                        <h3 className="text-base font-semibold text-foreground flex items-center gap-2">
                            <Lock className="w-4 h-4 text-amber-500" /> {t("cierre.closeButton", { period: periodLabel })}
                        </h3>
                        <p className="text-sm text-muted-foreground mt-2">
                            {t("cierre.closeModalDesc", { start: range.start, end: range.end })}
                        </p>
                        <label className="block text-xs font-medium text-muted-foreground mt-4 mb-1">{t("cierre.notesLabel")}</label>
                        <textarea
                            value={closeNotes}
                            onChange={(e) => setCloseNotes(e.target.value)}
                            placeholder={t("cierre.notesPlaceholder")}
                            className="w-full h-20 rounded-md border border-border bg-card text-sm p-2"
                        />
                        <div className="flex justify-end gap-2 mt-4">
                            <Button variant="outline" onClick={() => setShowCloseModal(false)} disabled={busy === "close"}>
                                {t("cierre.cancel")}
                            </Button>
                            <Button onClick={handleClosePeriod} disabled={busy === "close"}>
                                {busy === "close" ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Lock className="w-4 h-4 mr-2" />}
                                {t("cierre.confirmClose")}
                            </Button>
                        </div>
                    </div>
                </div>
            )}

            {/* Modal reabrir */}
            {reopenModal && (
                <div
                    className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4"
                    onClick={() => setReopenModal(null)}
                >
                    <div
                        className="bg-background border border-border rounded-xl max-w-md w-full p-5"
                        onClick={(e) => e.stopPropagation()}
                    >
                        <h3 className="text-base font-semibold text-foreground flex items-center gap-2">
                            <AlertTriangle className="w-4 h-4 text-amber-500" /> {t("cierre.reopenTitle", { label: reopenModal.label })}
                        </h3>
                        <p className="text-sm text-muted-foreground mt-2">
                            {t("cierre.reopenModalDesc")}
                        </p>
                        <label className="block text-xs font-medium text-muted-foreground mt-4 mb-1">{t("cierre.reasonLabel")}</label>
                        <input
                            value={reopenReason}
                            onChange={(e) => setReopenReason(e.target.value)}
                            placeholder={t("cierre.reasonPlaceholder")}
                            className="w-full h-9 rounded-md border border-border bg-card text-sm px-3"
                        />
                        <div className="flex justify-end gap-2 mt-4">
                            <Button variant="outline" onClick={() => setReopenModal(null)} disabled={busy === "reopen"}>
                                {t("cierre.cancel")}
                            </Button>
                            <Button onClick={handleReopen} disabled={busy === "reopen" || !reopenReason.trim()}>
                                {busy === "reopen" ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Unlock className="w-4 h-4 mr-2" />}
                                {t("cierre.reopen")}
                            </Button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
