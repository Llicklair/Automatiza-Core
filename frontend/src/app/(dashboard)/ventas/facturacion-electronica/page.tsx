"use client";

import { useCallback, useEffect, useState } from "react";
import { Download, FileX2, Loader2, Send, CheckCircle2, Clock, FileCode2 } from "lucide-react";
import { api } from "@/lib/api";
import type { Invoice } from "@/lib/api";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/ui/button";
import { KpiCard } from "@/components/shared/KpiCard";
import { useToastStore } from "@/stores/toast";

const fmt = (n: number) =>
    new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" }).format(n);
const fmtDate = (d: string) =>
    new Date(d).toLocaleDateString("es-ES", { day: "2-digit", month: "short", year: "numeric" });

const VERIFACTU_BADGE: Record<string, { label: string; cls: string }> = {
    sent: { label: "Enviada", cls: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" },
    error: { label: "Error", cls: "bg-red-500/10 text-red-400 border-red-500/20" },
};

export default function FacturacionElectronicaPage() {
    const toast = useToastStore();
    const [invoices, setInvoices] = useState<Invoice[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [downloadingId, setDownloadingId] = useState<string | null>(null);
    const [sendingId, setSendingId] = useState<string | null>(null);

    const load = useCallback(async () => {
        setIsLoading(true);
        try {
            const all = await api.erp.invoices.list({ limit: 200 });
            setInvoices(all.filter((i) => i.invoice_type === "issued" && i.status !== "draft"));
        } catch {
            toast.error("Error al cargar facturas");
        } finally {
            setIsLoading(false);
        }
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    useEffect(() => { load(); }, [load]);

    const handleDownload = async (inv: Invoice) => {
        setDownloadingId(inv.id);
        try {
            await api.erp.invoices.downloadFacturae(inv.id, inv.invoice_number);
        } catch {
            toast.error("Error al generar FacturaE XML");
        } finally {
            setDownloadingId(null);
        }
    };

    const handleSendVerifactu = async (inv: Invoice) => {
        setSendingId(inv.id);
        try {
            const res = await api.erp.invoices.sendVerifactu(inv.id);
            toast.success(res.message);
            await load();
        } catch {
            toast.error("Error al enviar a Verifactu");
        } finally {
            setSendingId(null);
        }
    };

    const sent = invoices.filter((i) => i.verifactu_status === "sent").length;
    const pending = invoices.filter((i) => !i.verifactu_status).length;

    return (
        <div className="p-6 space-y-6">
            <PageHeader
                title="Facturación electrónica"
                description="Genera FacturaE 3.2.2 y envía facturas a Verifactu (AEAT)"
                icon={FileCode2}
            />

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <KpiCard title="Facturas emitidas" value={invoices.length} icon={FileCode2} />
                <KpiCard title="Enviadas a Verifactu" value={sent} icon={CheckCircle2} />
                <KpiCard title="Pendientes de envío" value={pending} icon={Clock} />
                <KpiCard title="Total facturado" value={fmt(invoices.reduce((s, i) => s + i.amount_total, 0))} icon={FileCode2} />
            </div>

            {isLoading ? (
                <div className="flex items-center justify-center h-48 text-muted-foreground text-sm gap-2">
                    <Loader2 className="w-4 h-4 animate-spin" /> Cargando facturas…
                </div>
            ) : invoices.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-48 gap-2 text-muted-foreground rounded-xl border border-border bg-card">
                    <FileX2 className="w-8 h-8 opacity-30" />
                    <p className="text-sm">No hay facturas emitidas</p>
                </div>
            ) : (
                <div className="rounded-xl border border-border bg-card overflow-hidden">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="border-b border-border text-muted-foreground text-xs uppercase tracking-wide">
                                <th className="px-4 py-3 text-left">Nº Factura</th>
                                <th className="px-4 py-3 text-left">Cliente</th>
                                <th className="px-4 py-3 text-left">Fecha</th>
                                <th className="px-4 py-3 text-right">Importe</th>
                                <th className="px-4 py-3 text-center">Estado ERP</th>
                                <th className="px-4 py-3 text-center">Verifactu</th>
                                <th className="px-4 py-3 text-right">Acciones</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-border">
                            {invoices.map((inv) => {
                                const badge = inv.verifactu_status
                                    ? VERIFACTU_BADGE[inv.verifactu_status]
                                    : null;
                                const busy = downloadingId === inv.id || sendingId === inv.id;
                                return (
                                    <tr key={inv.id} className="hover:bg-muted/30 transition-colors">
                                        <td className="px-4 py-3 font-mono font-medium text-foreground">
                                            {inv.invoice_number ?? "S/N"}
                                        </td>
                                        <td className="px-4 py-3 text-foreground">
                                            {inv.client?.name ?? "—"}
                                        </td>
                                        <td className="px-4 py-3 text-muted-foreground">
                                            {fmtDate(inv.date)}
                                        </td>
                                        <td className="px-4 py-3 text-right font-semibold tabular-nums">
                                            {fmt(inv.amount_total)}
                                        </td>
                                        <td className="px-4 py-3 text-center">
                                            <span className="inline-block px-2 py-0.5 rounded-full text-xs border capitalize
                                                bg-muted/40 text-muted-foreground border-border">
                                                {inv.status}
                                            </span>
                                        </td>
                                        <td className="px-4 py-3 text-center">
                                            {badge ? (
                                                <span className={`inline-block px-2 py-0.5 rounded-full text-xs border ${badge.cls}`}>
                                                    {badge.label}
                                                </span>
                                            ) : (
                                                <span className="text-xs text-muted-foreground italic">Pendiente</span>
                                            )}
                                        </td>
                                        <td className="px-4 py-3">
                                            <div className="flex items-center gap-2 justify-end">
                                                <Button
                                                    size="sm"
                                                    variant="outline"
                                                    disabled={busy}
                                                    onClick={() => handleDownload(inv)}
                                                    title="Descargar XML FacturaE 3.2.2"
                                                >
                                                    {downloadingId === inv.id
                                                        ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                                        : <><Download className="mr-1 h-3.5 w-3.5" />XML</>}
                                                </Button>
                                                {!inv.verifactu_status && (
                                                    <Button
                                                        size="sm"
                                                        disabled={busy}
                                                        onClick={() => handleSendVerifactu(inv)}
                                                        title="Enviar a Verifactu (AEAT)"
                                                    >
                                                        {sendingId === inv.id
                                                            ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                                            : <><Send className="mr-1 h-3.5 w-3.5" />Verifactu</>}
                                                    </Button>
                                                )}
                                            </div>
                                        </td>
                                    </tr>
                                );
            })}
                        </tbody>
                    </table>
                </div>
            )}

            <p className="text-xs text-muted-foreground">
                FacturaE 3.2.2 — formato estándar AEAT para B2G y B2B. Verifactu funciona en modo simulación hasta integrar certificado digital.
            </p>
        </div>
    );
}
