"use client";

import { useTranslations } from "next-intl";
import Link from "next/link";
import { Client, Invoice } from "@/lib/api";
import { useToastStore } from "@/stores/toast";
import { api } from "@/lib/api";
import { StatusBadge, KpiCard } from "@/components/shared";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
    Plus, Building2, Mail, MapPin, X,
    FileText, Phone, Loader2, Download, ExternalLink,
} from "lucide-react";

// ── Helpers ───────────────────────────────────────────────────────────────────

async function downloadInvoicePdf(invoiceId: string, invoiceNumber: string | null, errorMsg: string) {
    try {
        await api.erp.invoices.downloadPdf(invoiceId, invoiceNumber);
    } catch {
        useToastStore.getState().show(errorMsg, "error");
    }
}

function getInitials(name: string) {
    return name
        .split(/\s+/)
        .slice(0, 2)
        .map((w) => w[0])
        .join("")
        .toUpperCase();
}

// ── Types ─────────────────────────────────────────────────────────────────────

interface ClienteDrawerProps {
    selectedClient: Client | null;
    clientInvoices: Invoice[];
    loadingInvoices: boolean;
    deleting: boolean;
    clientTypeMap: Record<string, { label: string; variant: "info" | "warning" | "default" | "success" }>;
    onClose: () => void;
    onEdit: (client: Client) => void;
    onDelete: (client: Client) => void;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function ClienteDrawer({
    selectedClient,
    clientInvoices,
    loadingInvoices,
    deleting,
    clientTypeMap,
    onClose,
    onEdit,
    onDelete,
}: ClienteDrawerProps) {
    const t = useTranslations("clientes");
    const tc = useTranslations("common");

    const totalFacturado = clientInvoices.reduce((s, i) => s + Number(i.amount_total), 0);

    return (
        <>
            {/* Backdrop */}
            {selectedClient && (
                <div
                    className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 transition-opacity"
                    onClick={onClose}
                />
            )}

            {/* Drawer */}
            <div className={`fixed top-0 right-0 h-full w-full max-w-[480px] bg-card border-l border-border shadow-2xl z-50 transform transition-transform duration-300 ease-in-out flex flex-col ${selectedClient ? "translate-x-0" : "translate-x-full"}`}>
                {selectedClient && (
                    <>
                        {/* Header */}
                        <div className="px-6 py-5 border-b border-border bg-muted sticky top-0 z-10">
                            <div className="flex items-start justify-between gap-3">
                                <div className="flex items-center gap-3 min-w-0">
                                    <Avatar className="h-12 w-12 rounded-xl">
                                        <AvatarFallback className="rounded-xl bg-primary/10 text-primary text-sm font-bold">
                                            {selectedClient.client_type === "company" || selectedClient.client_type === "supplier"
                                                ? <Building2 className="h-6 w-6" />
                                                : getInitials(selectedClient.name)
                                            }
                                        </AvatarFallback>
                                    </Avatar>
                                    <div className="min-w-0">
                                        <h2 className="text-lg font-bold text-foreground leading-tight truncate">{selectedClient.name}</h2>
                                        <div className="flex items-center gap-2 mt-1 flex-wrap">
                                            {selectedClient.nif && (
                                                <span className="text-xs font-mono text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded">
                                                    {selectedClient.nif}
                                                </span>
                                            )}
                                            {(() => {
                                                const typeInfo = clientTypeMap[selectedClient.client_type] ?? { label: selectedClient.client_type, variant: "default" as const };
                                                return <StatusBadge status={selectedClient.client_type} label={typeInfo.label} />;
                                            })()}
                                        </div>
                                    </div>
                                </div>
                                <Button variant="ghost" size="icon" onClick={onClose} className="shrink-0" aria-label={t("closeClientCard")}>
                                    <X className="h-5 w-5" aria-hidden="true" />
                                </Button>
                            </div>
                        </div>

                        <div className="flex-1 overflow-y-auto">
                            {/* Datos de contacto */}
                            <div className="px-6 py-5 border-b border-border">
                                <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">{t("contactInfo")}</h3>
                                <dl className="space-y-2.5">
                                    {selectedClient.email && (
                                        <div className="flex items-center gap-3">
                                            <Mail className="h-4 w-4 text-muted-foreground shrink-0" />
                                            <span className="text-sm text-foreground">{selectedClient.email}</span>
                                        </div>
                                    )}
                                    {selectedClient.phone && (
                                        <div className="flex items-center gap-3">
                                            <Phone className="h-4 w-4 text-muted-foreground shrink-0" />
                                            <span className="text-sm text-foreground">{selectedClient.phone}</span>
                                        </div>
                                    )}
                                    {selectedClient.address && (
                                        <div className="flex items-start gap-3">
                                            <MapPin className="h-4 w-4 text-muted-foreground shrink-0 mt-0.5" />
                                            <span className="text-sm text-foreground">{selectedClient.address}</span>
                                        </div>
                                    )}
                                    {(selectedClient.city || selectedClient.postal_code) && (
                                        <div className="flex items-center gap-3 pl-7">
                                            <span className="text-sm text-muted-foreground">
                                                {[selectedClient.postal_code, selectedClient.city].filter(Boolean).join(" · ")}
                                            </span>
                                        </div>
                                    )}
                                    {!selectedClient.email && !selectedClient.phone && !selectedClient.address && !selectedClient.city && (
                                        <p className="text-sm text-muted-foreground italic">{t("noContactData")}</p>
                                    )}
                                </dl>
                            </div>

                            {/* Metricas rapidas */}
                            <div className="px-6 py-4 border-b border-border grid grid-cols-3 gap-3">
                                <KpiCard title={t("invoicesKpi")} value={clientInvoices.length} icon={FileText} />
                                <KpiCard
                                    title={t("billedKpi")}
                                    value={`${totalFacturado.toLocaleString("es-ES", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}€`}
                                />
                                <KpiCard
                                    title={t("createdColumn")}
                                    value={new Date(selectedClient.created_at).toLocaleDateString("es-ES", { day: "2-digit", month: "short", year: "numeric" })}
                                />
                            </div>

                            {/* Historial de facturas */}
                            <div className="px-6 py-5">
                                <div className="flex items-center justify-between mb-4">
                                    <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                                        <FileText className="h-3.5 w-3.5" /> {t("invoiceHistory")}
                                    </h3>
                                    <Button variant="outline" size="sm" asChild>
                                        <Link href={`/ventas/facturas/nueva?client_id=${selectedClient.id}`}>
                                            <Plus className="h-3 w-3 mr-1" /> {t("newInvoice")}
                                        </Link>
                                    </Button>
                                </div>

                                {loadingInvoices ? (
                                    <div className="flex items-center justify-center gap-2 py-8 text-muted-foreground text-sm">
                                        <Loader2 className="h-4 w-4 animate-spin" /> {tc("loading")}
                                    </div>
                                ) : clientInvoices.length === 0 ? (
                                    <EmptyState
                                        icon={FileText}
                                        title={t("noInvoices")}
                                        size="sm"
                                    />
                                ) : (
                                    <div className="space-y-2">
                                        {clientInvoices.map((inv) => (
                                            <div key={inv.id} className="bg-muted rounded-xl border border-border hover:border-primary/30 transition p-4 flex items-center gap-3">
                                                <div className="flex-1 min-w-0">
                                                    <div className="flex items-center gap-2 mb-1">
                                                        <span className="text-sm font-medium text-foreground truncate">
                                                            {inv.invoice_number || t("draft")}
                                                        </span>
                                                        <StatusBadge status={inv.status} />
                                                    </div>
                                                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                                        <span>{new Date(inv.date).toLocaleDateString("es-ES", { day: "2-digit", month: "short", year: "numeric" })}</span>
                                                        {inv.lines && inv.lines.length > 0 && (
                                                            <span>· {inv.lines[0].description?.slice(0, 40)}{(inv.lines[0].description?.length ?? 0) > 40 ? "..." : ""}</span>
                                                        )}
                                                    </div>
                                                </div>
                                                <div className="text-right shrink-0">
                                                    <p className="text-sm font-semibold text-foreground tabular-nums">
                                                        {Number(inv.amount_total).toLocaleString("es-ES", { minimumFractionDigits: 2 })}€
                                                    </p>
                                                    <p className="text-[10px] text-muted-foreground">
                                                        {t("base")} {Number(inv.amount_base).toLocaleString("es-ES", { minimumFractionDigits: 2 })}€
                                                    </p>
                                                </div>
                                                <Button
                                                    variant="ghost"
                                                    size="icon"
                                                    onClick={() => downloadInvoicePdf(inv.id, inv.invoice_number, t("errorDownloadPdf"))}
                                                    title={t("downloadPdf")}
                                                    className="shrink-0"
                                                 aria-label={t("downloadPdf")}>
                                                    <Download className="h-4 w-4" aria-hidden="true" />
                                                </Button>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* Footer */}
                        <div className="px-6 py-4 border-t border-border bg-background space-y-2">
                            <div className="flex gap-2">
                                <Button
                                    variant="outline"
                                    className="flex-1"
                                    onClick={() => onEdit(selectedClient)}
                                >
                                    <FileText className="h-4 w-4 mr-2" />
                                    {t("editClient")}
                                </Button>
                                <Button
                                    variant="destructive"
                                    onClick={() => onDelete(selectedClient)}
                                    disabled={deleting}
                                >
                                    {deleting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <X className="h-4 w-4 mr-2" />}
                                    {tc("delete")}
                                </Button>
                            </div>
                            <Button variant="outline" className="w-full" asChild>
                                <Link href={`/clientes/${selectedClient.id}`}>
                                    <ExternalLink className="h-4 w-4 mr-2" />
                                    {t("viewFullHistory")}
                                </Link>
                            </Button>
                            <Button variant="ghost" className="w-full" asChild>
                                <Link href="/ventas/facturas">
                                    <ExternalLink className="h-4 w-4 mr-2" />
                                    {t("viewAllInvoices")}
                                </Link>
                            </Button>
                        </div>
                    </>
                )}
            </div>
        </>
    );
}
