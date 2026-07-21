"use client";

import { useTranslations } from "next-intl";
import {
    ArrowLeft, User, Mail, MapPin, Hash, FileText, CheckCircle2,
    Clock, XCircle, Loader2, Plus, ExternalLink, Activity, CreditCard
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { useClienteDetalle } from "./_hooks/useClienteDetalle";
import { PageContainer } from "@/components/shared/PageContainer";
import { api } from "@/lib/api";
import { useToastStore } from "@/stores/toast";

const fmt = (n: number) => n.toLocaleString("es-ES", { style: "currency", currency: "EUR" });

const STATUS_ICONS: Record<string, React.ReactNode> = {
    paid: <CheckCircle2 className="w-4 h-4 text-emerald-400" />,
    pending: <Clock className="w-4 h-4 text-amber-400" />,
    cancelled: <XCircle className="w-4 h-4 text-rose-400" />,
    draft: <FileText className="w-4 h-4 text-muted-foreground" />,
};

const STATUS_LABELS: Record<string, { color: string; bg: string; border: string }> = {
    paid: { color: "text-emerald-400", bg: "bg-emerald-500/10", border: "border-emerald-500/20" },
    pending: { color: "text-amber-400", bg: "bg-amber-500/10", border: "border-amber-500/20" },
    cancelled: { color: "text-rose-400", bg: "bg-rose-500/10", border: "border-rose-500/20" },
    draft: { color: "text-muted-foreground", bg: "bg-muted", border: "border-border" },
};

export default function ClientDetailPage() {
    const t = useTranslations("clientes");
    const toast = useToastStore();
    const [printingCard, setPrintingCard] = useState(false);
    const handlePrintCard = async () => {
        if (!client) return;
        setPrintingCard(true);
        try {
            await api.erp.clients.loyaltyCardPdf(client.id);
        } catch {
            toast.error(t("printCardError"));
        } finally {
            setPrintingCard(false);
        }
    };
    const {
        router,
        client,
        invoices,
        loading,
        totalFacturado,
        totalCobrado,
        pendiente,
        timeline,
    } = useClienteDetalle(t);

    if (loading) {
        return (
            <div className="flex items-center justify-center py-32 text-muted-foreground gap-2">
                <Loader2 className="w-5 h-5 animate-spin" /> {t("loadingContact")}
            </div>
        );
    }

    if (!client) {
        return (
            <PageContainer width="4xl" className="text-center">
                <p className="text-muted-foreground">{t("contactNotFound")}</p>
                <button onClick={() => router.back()} className="mt-4 text-primary hover:text-primary transition-colors text-sm">
                    {t("goBack")}
                </button>
            </PageContainer>
        );
    }

    return (
        <PageContainer width="5xl" className="space-y-8">
            {/* Back */}
            <button onClick={() => router.back()} className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors text-sm">
                <ArrowLeft className="w-4 h-4" /> {t("backToContacts")}
            </button>

            {/* Header */}
            <div className="bg-card border border-border rounded-2xl p-8 flex items-start gap-6">
                <div className="w-16 h-16 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center flex-shrink-0">
                    <User className="w-8 h-8 text-primary" />
                </div>
                <div className="flex-1">
                    <div className="flex items-start justify-between">
                        <div>
                            <h1 className="text-2xl font-bold text-foreground">{client.name}</h1>
                            <div className="flex flex-wrap items-center gap-4 mt-2">
                                {client.nif && (
                                    <span className="flex items-center gap-1.5 text-sm text-muted-foreground">
                                        <Hash className="w-3.5 h-3.5 text-muted-foreground" /> {client.nif}
                                    </span>
                                )}
                                {client.email && (
                                    <span className="flex items-center gap-1.5 text-sm text-muted-foreground">
                                        <Mail className="w-3.5 h-3.5 text-muted-foreground" /> {client.email}
                                    </span>
                                )}
                                {(client.city || client.address) && (
                                    <span className="flex items-center gap-1.5 text-sm text-muted-foreground">
                                        <MapPin className="w-3.5 h-3.5 text-muted-foreground" /> {client.city || client.address}
                                    </span>
                                )}
                            </div>
                        </div>
                        <div className="flex items-center gap-2">
                            <button
                                onClick={handlePrintCard}
                                disabled={printingCard}
                                className="flex items-center gap-2 border border-border hover:bg-muted/60 text-foreground text-sm px-4 py-2 rounded-xl transition-colors disabled:opacity-50"
                            >
                                {printingCard ? <Loader2 className="w-4 h-4 animate-spin" /> : <CreditCard className="w-4 h-4" />} {t("printCard")}
                            </button>
                            <Link
                                href={`/crm/actividades?client=${client.id}`}
                                className="flex items-center gap-2 border border-border hover:bg-muted/60 text-foreground text-sm px-4 py-2 rounded-xl transition-colors"
                            >
                                <Activity className="w-4 h-4" /> {t("crmActivities")}
                            </Link>
                            <Link
                                href={`/ventas/facturas/nueva?client=${client.id}`}
                                className="flex items-center gap-2 bg-primary hover:bg-primary text-foreground text-sm px-4 py-2 rounded-xl transition-colors"
                            >
                                <Plus className="w-4 h-4" /> {t("newInvoice")}
                            </Link>
                        </div>
                    </div>
                </div>
            </div>

            {/* KPIs */}
            <div className="grid grid-cols-3 gap-4">
                <div className="bg-card border border-border rounded-2xl p-5">
                    <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">{t("totalInvoiced")}</p>
                    <p className="text-xl font-bold text-foreground">{fmt(totalFacturado)}</p>
                    <p className="text-xs text-muted-foreground mt-1">{t("invoiceCount", { count: invoices.length })}</p>
                </div>
                <div className="bg-card border border-border rounded-2xl p-5">
                    <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">{t("collected")}</p>
                    <p className="text-xl font-bold text-emerald-400">{fmt(totalCobrado)}</p>
                    <p className="text-xs text-muted-foreground mt-1">{t("paidInvoiceCount", { count: invoices.filter(i => i.status === "paid").length })}</p>
                </div>
                <div className={`rounded-2xl p-5 border ${pendiente > 0 ? "bg-amber-500/10 border-amber-500/20" : "bg-card border-border"}`}>
                    <p className={`text-xs uppercase tracking-wider mb-1 ${pendiente > 0 ? "text-amber-400" : "text-muted-foreground"}`}>{t("pendingCollection")}</p>
                    <p className={`text-xl font-bold ${pendiente > 0 ? "text-amber-400" : "text-foreground"}`}>{fmt(pendiente)}</p>
                    <p className="text-xs text-muted-foreground mt-1">{t("invoiceCount", { count: invoices.filter(i => i.status === "pending").length })}</p>
                </div>
            </div>

            {/* Timeline */}
            <div>
                <h2 className="text-base font-bold text-foreground mb-4">{t("activityHistory")}</h2>
                {timeline.length === 0 ? (
                    <div className="bg-card border border-border rounded-2xl p-12 text-center">
                        <FileText className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
                        <p className="text-muted-foreground text-sm">{t("noActivityYet")}</p>
                    </div>
                ) : (
                    <div className="relative">
                        {/* Vertical line */}
                        <div className="absolute left-6 top-0 bottom-0 w-px bg-border" />

                        <div className="space-y-4 pl-16">
                            {timeline.map((event, i) => {
                                const st = STATUS_LABELS[event.status];
                                return (
                                    <div key={i} className="relative">
                                        {/* Dot */}
                                        <div className="absolute -left-10 top-3 w-8 h-8 rounded-full bg-card border border-border flex items-center justify-center">
                                            {STATUS_ICONS[event.status]}
                                        </div>
                                        {/* Card */}
                                        <div className="bg-card border border-border rounded-xl p-4 hover:border-border transition-colors">
                                            <div className="flex items-center justify-between">
                                                <div className="flex items-center gap-3">
                                                    <div>
                                                        <p className="text-sm font-medium text-foreground">{event.title}</p>
                                                        <p className="text-xs text-muted-foreground mt-0.5">
                                                            {new Date(event.date).toLocaleDateString("es-ES", { day: "numeric", month: "long", year: "numeric" })}
                                                        </p>
                                                    </div>
                                                    <span className={`text-xs px-2 py-0.5 rounded-full ${st?.bg} ${st?.border} border ${st?.color}`}>
                                                        {event.subtitle}
                                                    </span>
                                                </div>
                                                <div className="flex items-center gap-3">
                                                    <span className="text-sm font-bold text-foreground font-mono">{fmt(event.amount)}</span>
                                                    <Link
                                                        href={`/ventas/facturas/${event.id}`}
                                                        className="p-1.5 rounded-lg hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
                                                    >
                                                        <ExternalLink className="w-3.5 h-3.5" />
                                                    </Link>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                )}
            </div>
        </PageContainer>
    );
}
