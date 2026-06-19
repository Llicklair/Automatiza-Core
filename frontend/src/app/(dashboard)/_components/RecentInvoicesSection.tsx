"use client";

import { FileText, ArrowRight } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { InvBadge } from "./DashboardBadges";
import type { Invoice } from "@/lib/api";

interface RecentInvoicesSectionProps {
    loading: boolean;
    invoices: Invoice[];
}

export function RecentInvoicesSection({ loading, invoices }: RecentInvoicesSectionProps) {
    const t = useTranslations("dashboard");
    return (
        <div className="bg-card border border-border rounded-2xl overflow-hidden flex flex-col h-full">
            <div className="px-6 py-5 border-b border-border flex items-center justify-between bg-card">
                <h2 className="text-base font-semibold text-foreground flex items-center gap-2">
                    <FileText className="w-4 h-4 text-muted-foreground" /> {t("recentInvoices.title")}
                </h2>
                <Link href="/ventas/facturas" className="text-xs font-medium text-primary hover:text-primary transition-colors flex items-center gap-1 bg-primary/10 px-3 py-1.5 rounded-lg hover:bg-primary/20">
                    {t("recentInvoices.viewAll")} <ArrowRight className="w-3 h-3" />
                </Link>
            </div>
            <div className="flex-1 p-0">
                {loading ? (
                    <div className="p-12 text-center text-muted-foreground text-sm">{t("recentInvoices.loading")}</div>
                ) : invoices.length === 0 ? (
                    <div className="p-16 text-center text-muted-foreground flex flex-col items-center">
                        <FileText className="w-12 h-12 text-muted-foreground mb-3" />
                        <p className="text-sm text-muted-foreground">{t("recentInvoices.empty")}</p>
                        <Link href="/ventas/facturas/nueva" className="mt-4 text-xs bg-accent/50 hover:bg-accent text-foreground px-4 py-2 rounded-lg transition-colors border border-border">
                            {t("recentInvoices.createFirst")}
                        </Link>
                    </div>
                ) : (
                    <table className="w-full text-left border-collapse">
                        <thead>
                            <tr className="border-b border-border text-xs text-muted-foreground font-medium uppercase tracking-wider bg-muted/50">
                                <th className="py-3 pl-6">{t("recentInvoices.colContact")}</th>
                                <th className="py-3 text-center">{t("recentInvoices.colStatus")}</th>
                                <th className="py-3 text-right">{t("recentInvoices.colDate")}</th>
                                <th className="py-3 text-right pr-6">{t("recentInvoices.colAmount")}</th>
                            </tr>
                        </thead>
                        <tbody className="text-sm divide-y divide-white/5">
                            {invoices.map((inv) => (
                                <tr key={inv.id} className="hover:bg-accent/50 transition-colors group">
                                    <td className="py-4 pl-6">
                                        <div className="font-medium text-foreground">{inv.client?.name || t("recentInvoices.various")}</div>
                                        <div className="text-xs text-muted-foreground">{inv.invoice_number || t("recentInvoices.draft")}</div>
                                    </td>
                                    <td className="py-4 text-center"><InvBadge status={inv.status} /></td>
                                    <td className="py-4 text-right text-muted-foreground text-xs">
                                        {inv.date ? new Date(inv.date).toLocaleDateString('es-ES') : '-'}
                                    </td>
                                    <td className="py-4 pr-6 text-right font-semibold text-foreground">
                                        {Number(inv.amount_total).toLocaleString('es-ES', { minimumFractionDigits: 2 })}€
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>
        </div>
    );
}
