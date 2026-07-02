"use client";

import { useTranslations } from "next-intl";
import {
    WalletCards, CheckCircle2, Bot, Loader2, Sparkles,
    Calculator, Wallet, ShieldCheck, Receipt,
} from "lucide-react";
import { KpiCard } from "@/components/shared/KpiCard";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/ui/button";
import { usePayrolls } from "./_hooks/usePayrolls";
import { AutoPayrollModal } from "./_components/AutoPayrollModal";
import { PayrollFilters } from "./_components/PayrollFilters";
import { PayrollTable } from "./_components/PayrollTable";
import { PageContainer } from "@/components/shared/PageContainer";

export default function PayrollsPage() {
    const {
        filtered, isLoading, drafts, kpis, uniqueEmployees, fmt,
        generatingPayrolls, approvingId, downloadingId,
        search, setSearch, filterMonth, setFilterMonth, filterEmpId, setFilterEmpId,
        autoOpen, setAutoOpen, autoEmployees, autoEmpLoading,
        autoEmpId, setAutoEmpId, autoPreview, autoPreviewLoading, autoSubmitting,
        openAutoModal, handleAutoCreate, handleGeneratePayrolls, handleApprove, handleDownloadPdf,
        payrolls,
    } = usePayrolls();

    const t = useTranslations("rrhh");

    return (
        <PageContainer>
            <PageHeader
                title={t("nominas.title")}
                description={
                    <span className="flex items-center gap-2">
                        {t("nominas.description")}
                        <span className="flex items-center gap-1 px-2 py-0.5 bg-primary/10 text-primary border border-primary/20 rounded-full text-xs font-medium">
                            <Bot className="w-3 h-3" /> {t("nominas.aiFirst")}
                        </span>
                    </span>
                }
                icon={WalletCards}
                actions={
                    <div className="flex flex-wrap gap-2">
                        <Button variant="outline" onClick={openAutoModal} title={t("nominas.autoCalculateHint")}>
                            <Calculator className="w-4 h-4 mr-2 text-emerald-400" /> {t("nominas.autoCalculate")}
                        </Button>
                        <Button onClick={handleGeneratePayrolls} disabled={generatingPayrolls} title={t("nominas.generateWithAiHint")}>
                            {generatingPayrolls
                                ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> {t("nominas.generating")}</>
                                : <><Sparkles className="w-4 h-4 mr-2" /> {t("nominas.generateWithAi")}</>
                            }
                        </Button>
                        {drafts > 0 && (
                            <Button
                                variant="secondary"
                                className="bg-emerald-600/20 text-emerald-400 hover:bg-emerald-600/30 border border-emerald-500/20"
                                onClick={async () => {
                                    for (const p of payrolls.filter(p => p.status === "draft")) {
                                        await handleApprove(p);
                                    }
                                }}
                            >
                                <CheckCircle2 className="w-4 h-4 mr-2" /> {t("nominas.approveAll", { n: drafts })}
                            </Button>
                        )}
                    </div>
                }
            />

            {/* KPIs */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <KpiCard title={t("nominas.kpi.monthlyCost")} value={fmt(kpis.costeNominas)} icon={Wallet} />
                <KpiCard title={t("nominas.kpi.totalSs")}     value={fmt(kpis.totalSS)}      icon={ShieldCheck} />
                <KpiCard title={t("nominas.kpi.totalIrpf")}   value={fmt(kpis.totalIRPF)}    icon={Receipt} />
            </div>

            {/* Filters + Table */}
            <div className="bg-card border border-border rounded-2xl shadow-lg overflow-hidden">
                <PayrollFilters
                    search={search} setSearch={setSearch}
                    filterMonth={filterMonth} setFilterMonth={setFilterMonth}
                    filterEmpId={filterEmpId} setFilterEmpId={setFilterEmpId}
                    uniqueEmployees={uniqueEmployees} drafts={drafts}
                />
                <PayrollTable
                    filtered={filtered} isLoading={isLoading} fmt={fmt}
                    downloadingId={downloadingId} approvingId={approvingId}
                    handleDownloadPdf={handleDownloadPdf} handleApprove={handleApprove}
                />
            </div>

            {autoOpen && (
                <AutoPayrollModal
                    autoEmployees={autoEmployees} autoEmpLoading={autoEmpLoading}
                    autoEmpId={autoEmpId} setAutoEmpId={setAutoEmpId}
                    autoPreview={autoPreview} autoPreviewLoading={autoPreviewLoading}
                    autoSubmitting={autoSubmitting} fmt={fmt}
                    onClose={() => setAutoOpen(false)}
                    onSubmit={() => void handleAutoCreate()}
                />
            )}
        </PageContainer>
    );
}
