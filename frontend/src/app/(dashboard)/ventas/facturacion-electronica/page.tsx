"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { Download, FileX2, Loader2, Send, CheckCircle2, Clock, FileCode2 } from "lucide-react";
import { api } from "@/lib/api";
import type { Invoice } from "@/lib/api";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/ui/button";
import { KpiCard } from "@/components/shared/KpiCard";
import { useToastStore } from "@/stores/toast";
import { PageContainer } from "@/components/shared/PageContainer";

const fmt = (n: number) =>
    new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" }).format(n);
const fmtDate = (d: string) =>
    new Date(d).toLocaleDateString("es-ES", { day: "2-digit", month: "short", year: "numeric" });

const VERIFACTU_BADGE: Record<string, { labelKey: "badgeSent" | "badgeError"; cls: string }> = {
    sent: { labelKey: "badgeSent", cls: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" },
    error: { labelKey: "badgeError", cls: "bg-red-500/10 text-red-400 border-red-500/20" },
};

export default function FacturacionElectronicaPage() {
    const t = useTranslations("ventas");
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
            toast.error(t("eInvoicing.errorLoading"));
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
            toast.error(t("eInvoicing.errorXml"));
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
            toast.error(t("eInvoicing.errorVerifactu"));
        } finally {
            setSendingId(null);
        }
    };

    const sent = invoices.filter((i) => i.verifactu_status === "sent").length;
    const pending = invoices.filter((i) => !i.verifactu_status).length;

    return (
        <PageContainer width="full">
            <PageHeader
                title={t("eInvoicing.title")}
                description={t("eInvoicing.description")}
                icon={FileCode2}
            />

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <KpiCard title={t("eInvoicing.kpiIssued")} value={invoices.length} icon={FileCode2} />
                <KpiCard title={t("eInvoicing.kpiSent")} value={sent} icon={CheckCircle2} />
                <KpiCard title={t("eInvoicing.kpiPending")} value={pending} icon={Clock} />
                <KpiCard title={t("eInvoicing.kpiTotal")} value={fmt(invoices.reduce((s, i) => s + i.amount_total, 0))} icon={FileCode2} />
            </div>

            {isLoading ? (
                <div className="flex items-center justify-center h-48 text-muted-foreground text-sm gap-2">
                    <Loader2 className="w-4 h-4 animate-spin" /> {t("eInvoicing.loading")}
                </div>
            ) : invoices.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-48 gap-2 text-muted-foreground rounded-xl border border-border bg-card">
                    <FileX2 className="w-8 h-8 opacity-30" />
                    <p className="text-sm">{t("eInvoicing.empty")}</p>
                </div>
            ) : (
                <div className="rounded-xl border border-border bg-card overflow-hidden">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="border-b border-border text-muted-foreground text-xs uppercase tracking-wide">
                                <th className="px-4 py-3 text-left">{t("eInvoicing.colNumber")}</th>
                                <th className="px-4 py-3 text-left">{t("eInvoicing.colClient")}</th>
                                <th className="px-4 py-3 text-left">{t("eInvoicing.colDate")}</th>
                                <th className="px-4 py-3 text-right">{t("eInvoicing.colAmount")}</th>
                                <th className="px-4 py-3 text-center">{t("eInvoicing.colErpStatus")}</th>
                                <th className="px-4 py-3 text-center">{t("eInvoicing.colVerifactu")}</th>
                                <th className="px-4 py-3 text-right">{t("eInvoicing.colActions")}</th>
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
                                            {inv.invoice_number ?? t("eInvoicing.noNumber")}
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
                                                    {t(`eInvoicing.${badge.labelKey}`)}
                                                </span>
                                            ) : (
                                                <span className="text-xs text-muted-foreground italic">{t("eInvoicing.statusPending")}</span>
                                            )}
                                        </td>
                                        <td className="px-4 py-3">
                                            <div className="flex items-center gap-2 justify-end">
                                                <Button
                                                    size="sm"
                                                    variant="outline"
                                                    disabled={busy}
                                                    onClick={() => handleDownload(inv)}
                                                    title={t("eInvoicing.downloadXmlTitle")}
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
                                                        title={t("eInvoicing.sendVerifactuTitle")}
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
                {t("eInvoicing.footnote")}
            </p>
        </PageContainer>
    );
}
