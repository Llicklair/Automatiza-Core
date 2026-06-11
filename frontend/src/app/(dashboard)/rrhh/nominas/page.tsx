"use client";

import {
    WalletCards, CheckCircle2, Bot, Loader2, Sparkles,
    AlertCircle, X, Calculator, Wallet, ShieldCheck, Receipt,
} from "lucide-react";
import { KpiCard } from "@/components/shared/KpiCard";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/ui/button";
import { usePayrolls } from "./_hooks/usePayrolls";
import { AutoPayrollModal } from "./_components/AutoPayrollModal";
import { PayrollFilters } from "./_components/PayrollFilters";
import { PayrollTable } from "./_components/PayrollTable";

export default function PayrollsPage() {
    const {
        filtered, isLoading, drafts, kpis, uniqueEmployees, fmt,
        generatingPayrolls, approvingId, downloadingId, toast, setToast,
        search, setSearch, filterMonth, setFilterMonth, filterEmpId, setFilterEmpId,
        autoOpen, setAutoOpen, autoEmployees, autoEmpLoading,
        autoEmpId, setAutoEmpId, autoPreview, autoPreviewLoading, autoSubmitting,
        openAutoModal, handleAutoCreate, handleGeneratePayrolls, handleApprove, handleDownloadPdf,
        payrolls,
    } = usePayrolls();

    return (
        <div className="p-8 max-w-[1400px] mx-auto space-y-6">
            <PageHeader
                title="Emisión de Nóminas"
                description={
                    <span className="flex items-center gap-2">
                        Revisa, aprueba y descarga las pre-nóminas generadas por la IA.
                        <span className="flex items-center gap-1 px-2 py-0.5 bg-primary/10 text-primary border border-primary/20 rounded-full text-xs font-medium">
                            <Bot className="w-3 h-3" /> IA-First
                        </span>
                    </span>
                }
                icon={WalletCards}
                actions={
                    <div className="flex flex-wrap gap-2">
                        <Button variant="outline" onClick={openAutoModal}>
                            <Calculator className="w-4 h-4 mr-2 text-emerald-400" /> Calcular automática
                        </Button>
                        <Button onClick={handleGeneratePayrolls} disabled={generatingPayrolls}>
                            {generatingPayrolls
                                ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Generando…</>
                                : <><Sparkles className="w-4 h-4 mr-2" /> Generar con IA</>
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
                                <CheckCircle2 className="w-4 h-4 mr-2" /> Aprobar todos ({drafts})
                            </Button>
                        )}
                    </div>
                }
            />

            {/* KPIs */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <KpiCard title="Coste nóminas (mes)" value={fmt(kpis.costeNominas)} icon={Wallet} />
                <KpiCard title="Total SS (mes)"       value={fmt(kpis.totalSS)}      icon={ShieldCheck} />
                <KpiCard title="Total IRPF (mes)"     value={fmt(kpis.totalIRPF)}    icon={Receipt} />
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

            {/* Inline toast (gestionado por usePayrolls) */}
            {toast && (
                <div className={`fixed bottom-6 right-6 z-50 flex items-center gap-3 px-5 py-3 rounded-2xl shadow-2xl text-sm font-medium max-w-sm border
                    ${toast.type === "ok"
                        ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
                        : "bg-red-500/10 border-red-500/20 text-red-400"
                    }`}>
                    {toast.type === "ok"
                        ? <CheckCircle2 className="w-5 h-5 shrink-0" />
                        : <AlertCircle className="w-5 h-5 shrink-0" />
                    }
                    <span className="flex-1">{toast.msg}</span>
                    <Button variant="ghost" size="icon" className="h-6 w-6 opacity-60 hover:opacity-100" onClick={() => setToast(null)} aria-label="Cerrar notificación">
                        <X className="w-4 h-4" aria-hidden="true" />
                    </Button>
                </div>
            )}
        </div>
    );
}
