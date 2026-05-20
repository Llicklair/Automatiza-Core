"use client";

import { useEffect, useState } from "react";
import {
    FileDown, Lock, Unlock, AlertTriangle, BookOpen, Library, BookText, Loader2,
} from "lucide-react";
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
            toast.success("PDF descargado");
        } catch (e) {
            toast.error(e instanceof Error ? e.message : "Error descargando PDF");
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
            toast.success(`Periodo ${quarter}T ${year} cerrado. Los asientos del trimestre quedan bloqueados.`);
            setShowCloseModal(false);
            setCloseNotes("");
            loadPeriods();
        } catch (e) {
            toast.error(e instanceof Error ? e.message : "Error al cerrar periodo");
        } finally {
            setBusy(null);
        }
    };

    const handleReopen = async () => {
        if (!reopenModal) return;
        if (!reopenReason.trim()) {
            toast.error("Se requiere un motivo para reabrir");
            return;
        }
        setBusy("reopen");
        try {
            await api.accounting.periods.reopen(reopenModal.id, reopenReason.trim());
            toast.success(`Periodo ${reopenModal.label} reabierto.`);
            setReopenModal(null);
            setReopenReason("");
            loadPeriods();
        } catch (e) {
            toast.error(e instanceof Error ? e.message : "Error al reabrir");
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
                        <h3 className="text-sm font-semibold text-foreground">Libros oficiales y cierre de periodo</h3>
                        <p className="text-xs text-muted-foreground mt-0.5">
                            Genera el Libro Diario, Libro Mayor y Cuentas Anuales del trimestre. Cierra el periodo para congelar asientos.
                        </p>
                    </div>
                </div>
                {isClosed && (
                    <span className="inline-flex items-center gap-1.5 text-xs font-medium text-amber-500 bg-amber-500/10 border border-amber-500/30 px-2.5 py-1 rounded-full">
                        <Lock className="w-3.5 h-3.5" /> {quarter}T {year} cerrado
                    </span>
                )}
            </div>

            <div className="flex items-center gap-2 flex-wrap">
                <select
                    value={quarter}
                    onChange={(e) => setQuarter(Number(e.target.value))}
                    className="h-9 px-2 rounded-md border border-border bg-card text-sm"
                >
                    {[1, 2, 3, 4].map((q) => <option key={q} value={q}>{q}T</option>)}
                </select>
                <select
                    value={year}
                    onChange={(e) => setYear(Number(e.target.value))}
                    className="h-9 px-2 rounded-md border border-border bg-card text-sm"
                >
                    {[year - 1, year, year + 1].map((y) => <option key={y} value={y}>{y}</option>)}
                </select>
                <span className="text-xs text-muted-foreground">
                    Rango: <span className="font-mono">{range.start}</span> → <span className="font-mono">{range.end}</span>
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
                    Libro Diario PDF
                </Button>
                <Button
                    variant="outline"
                    onClick={() => handleDownload("mayor")}
                    disabled={busy !== null}
                    className="justify-start"
                >
                    {busy === "mayor" ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <BookText className="w-4 h-4 mr-2" />}
                    Libro Mayor PDF
                </Button>
                <Button
                    variant="outline"
                    onClick={() => handleDownload("anuales")}
                    disabled={busy !== null}
                    className="justify-start"
                >
                    {busy === "anuales" ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <FileDown className="w-4 h-4 mr-2" />}
                    Cuentas Anuales PDF
                </Button>
            </div>

            <div className="flex items-center justify-between gap-3 pt-2 border-t border-border">
                {isClosed ? (
                    <>
                        <p className="text-xs text-muted-foreground">
                            <Lock className="w-3 h-3 inline mr-1" />
                            Cerrado el {currentPeriod?.closed_at ? new Date(currentPeriod.closed_at).toLocaleDateString("es-ES") : "—"}
                        </p>
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setReopenModal({ id: currentPeriod!.id, label: `${quarter}T ${year}` })}
                            className="text-amber-500 hover:text-amber-400"
                        >
                            <Unlock className="w-3.5 h-3.5 mr-1" /> Reabrir
                        </Button>
                    </>
                ) : (
                    <>
                        <p className="text-xs text-muted-foreground">
                            Tras cerrar, los asientos del trimestre quedan bloqueados.
                        </p>
                        <Button
                            onClick={() => setShowCloseModal(true)}
                            disabled={busy !== null}
                            size="sm"
                        >
                            <Lock className="w-3.5 h-3.5 mr-1" /> Cerrar {quarter}T {year}
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
                            <Lock className="w-4 h-4 text-amber-500" /> Cerrar {quarter}T {year}
                        </h3>
                        <p className="text-sm text-muted-foreground mt-2">
                            Después del cierre no se podrán crear ni borrar asientos del rango {range.start} → {range.end}. Solo se podrá reabrir con motivo justificado.
                        </p>
                        <label className="block text-xs font-medium text-muted-foreground mt-4 mb-1">Notas (opcional)</label>
                        <textarea
                            value={closeNotes}
                            onChange={(e) => setCloseNotes(e.target.value)}
                            placeholder="Ej: Cierre tras presentar Modelo 303 — saldo a ingresar 1.550€"
                            className="w-full h-20 rounded-md border border-border bg-card text-sm p-2"
                        />
                        <div className="flex justify-end gap-2 mt-4">
                            <Button variant="outline" onClick={() => setShowCloseModal(false)} disabled={busy === "close"}>
                                Cancelar
                            </Button>
                            <Button onClick={handleClosePeriod} disabled={busy === "close"}>
                                {busy === "close" ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Lock className="w-4 h-4 mr-2" />}
                                Cerrar periodo
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
                            <AlertTriangle className="w-4 h-4 text-amber-500" /> Reabrir {reopenModal.label}
                        </h3>
                        <p className="text-sm text-muted-foreground mt-2">
                            Reabrir un periodo cerrado queda registrado. Indica el motivo (asiento olvidado, corrección, etc.).
                        </p>
                        <label className="block text-xs font-medium text-muted-foreground mt-4 mb-1">Motivo (obligatorio)</label>
                        <input
                            value={reopenReason}
                            onChange={(e) => setReopenReason(e.target.value)}
                            placeholder="Ej: Factura omitida del proveedor X recibida tarde"
                            className="w-full h-9 rounded-md border border-border bg-card text-sm px-3"
                        />
                        <div className="flex justify-end gap-2 mt-4">
                            <Button variant="outline" onClick={() => setReopenModal(null)} disabled={busy === "reopen"}>
                                Cancelar
                            </Button>
                            <Button onClick={handleReopen} disabled={busy === "reopen" || !reopenReason.trim()}>
                                {busy === "reopen" ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Unlock className="w-4 h-4 mr-2" />}
                                Reabrir
                            </Button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
