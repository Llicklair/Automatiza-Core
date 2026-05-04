"use client";

import { FileText, Plus, Euro, Clock, AlertTriangle } from "lucide-react";
import { Input } from "@/components/ui/input";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { DataTable } from "@/components/data-table";
import { PageHeader } from "@/components/shared/PageHeader";
import { KpiCard } from "@/components/shared/KpiCard";
import { EmptyState } from "@/components/shared/EmptyState";
import { Button } from "@/components/ui/button";
import { useFacturas } from "./_hooks/useFacturas";

export default function FacturasPage() {
    const t = useTranslations("ventas");
    const {
        loading, invoices, dateFrom, setDateFrom, dateTo, setDateTo,
        kpis, filteredInvoices, columns, statusFilterOptions,
    } = useFacturas();

    if (!loading && invoices.length === 0) {
        return (
            <div className="p-6 space-y-6">
                <PageHeader
                    title={t("title")}
                    description={t("description")}
                    icon={FileText}
                    actions={
                        <Button asChild>
                            <Link href="/ventas/facturas/nueva"><Plus className="mr-2 h-4 w-4" />{t("newInvoice")}</Link>
                        </Button>
                    }
                />
                <EmptyState
                    icon={FileText}
                    title={t("emptyTitle")}
                    description={t("emptyDescription")}
                    action={
                        <Button asChild>
                            <Link href="/ventas/facturas/nueva"><Plus className="mr-2 h-4 w-4" />{t("createInvoice")}</Link>
                        </Button>
                    }
                />
            </div>
        );
    }

    return (
        <div className="p-6 space-y-6">
            <PageHeader
                title={t("title")}
                description={t("description")}
                icon={FileText}
                actions={
                    <Button asChild>
                        <Link href="/ventas/facturas/nueva"><Plus className="mr-2 h-4 w-4" />{t("newInvoice")}</Link>
                    </Button>
                }
            />
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <KpiCard title={t("billedThisMonth")} value={`${kpis.facturadoMes.toLocaleString("es-ES", { minimumFractionDigits: 2 })}€`} icon={Euro} />
                <KpiCard title={t("pendingCollection")} value={`${kpis.pendienteCobro.toLocaleString("es-ES", { minimumFractionDigits: 2 })}€`} icon={Clock} />
                <KpiCard title={t("overdueInvoices")} value={kpis.vencidas} icon={AlertTriangle} />
                <KpiCard title={t("monthInvoices")} value={kpis.numFacturasMes} icon={FileText} />
            </div>
            <div className="flex flex-wrap items-end gap-4">
                <div>
                    <label className="block text-xs font-medium text-muted-foreground mb-1.5">{t("from")}</label>
                    <Input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)} />
                </div>
                <div>
                    <label className="block text-xs font-medium text-muted-foreground mb-1.5">{t("to")}</label>
                    <Input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)} />
                </div>
                {(dateFrom || dateTo) && (
                    <Button variant="ghost" size="sm" onClick={() => { setDateFrom(""); setDateTo(""); }}>
                        {t("clearDates")}
                    </Button>
                )}
            </div>
            <DataTable
                columns={columns}
                data={filteredInvoices}
                isLoading={loading}
                searchKey="invoice_number"
                searchPlaceholder={t("searchPlaceholder")}
                facetedFilters={[{ column: "status", title: t("status"), options: statusFilterOptions }]}
                emptyMessage={t("noInvoicesFound")}
            />
        </div>
    );
}
