"use client";

import {
    WalletCards, CheckCircle2, Bot, Loader2, Sparkles,
    AlertCircle, X, Calculator, Wallet, ShieldCheck, Receipt,
} from "lucide-react";
import { KpiCard } from "@/components/shared/KpiCard";
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
        <div className="min-h-screen bg-background text-foreground p-8">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-8">
                <div>
                    <h1 className="text-3xl font-light text-foreground flex items-center gap-3">
                        <div className="p-2 bg-emerald-500/10 rounded-xl">
                            <WalletCards className="w-8 h-8 text-emerald-400" />
                        </div>
                        Emisión de Nóminas
                    </h1>
                    <div className="flex items-center gap-2 mt-2 ml-14">
                        <p className="text-muted-foreground text-sm">Revisa, aprueba y descarga las pre-nóminas generadas por la IA.</p>
                        <span className="flex items-center gap-1 px-2 py-0.5 bg-primary/10 text-primary border border-primary/20 rounded-full text-xs font-medium">
                            <Bot className="w-3 h-3" /> IA-First
                        </span>
                    </div>
                </div>
                <div className="flex flex-wrap gap-3">
                    <button type="button" onClick={openAutoModal}
                        className="flex items-center gap-2 bg-muted hover:bg-accent border border-border text-foreground px-5 py-2.5 rounded-full font-medium transition-colors">
                        <Calculator className="w-4 h-4 text-emerald-400" /> Calcular automática
                    </button>
                    <button onClick={handleGeneratePayrolls} disabled={generatingPayrolls}
                        className="flex items-center gap-2 bg-primary hover:bg-primary disabled:opacity-60 text-foreground shadow-lg shadow-primary/20 px-5 py-2.5 rounded-full font-medium transition-colors">
                        {generatingPayrolls ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                        {generatingPayrolls ? "Generando..." : "Generar con IA"}
                    </button>
                    {drafts > 0 && (
                        <button
                            onClick={async () => { for (const p of payrolls.filter(p => p.status === "draft")) await handleApprove(p); }}
                            className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-foreground shadow-lg shadow-emerald-500/20 px-5 py-2.5 rounded-full font-medium transition-colors">
                            <CheckCircle2 className="w-4 h-4" /> Aprobar todos ({drafts})
                        </button>
                    )}
                </div>
            </div>

            {/* KPIs */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-2">
                <KpiCard title="Coste nóminas (mes)" value={fmt(kpis.costeNominas)} icon={Wallet} />
                <KpiCard title="Total SS (mes)"       value={fmt(kpis.totalSS)}      icon={ShieldCheck} />
                <KpiCard title="Total IRPF (mes)"     value={fmt(kpis.totalIRPF)}    icon={Receipt} />
            </div>

            {/* Filters + Table */}
            <div className="bg-card border border-border rounded-2xl shadow-2xl flex flex-col overflow-hidden">
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

            {toast && (
                <div className={`fixed bottom-6 right-6 z-50 flex items-center gap-3 px-5 py-3 rounded-2xl shadow-2xl text-sm font-medium max-w-sm
                    ${toast.type === "ok" ? "bg-emerald-500/10 border border-emerald-500/20 text-emerald-400" : "bg-red-500/10 border border-red-500/20 text-red-400"}`}>
                    {toast.type === "ok" ? <CheckCircle2 className="w-5 h-5 flex-shrink-0" /> : <AlertCircle className="w-5 h-5 flex-shrink-0" />}
                    <span className="flex-1">{toast.msg}</span>
                    <button onClick={() => setToast(null)} className="opacity-60 hover:opacity-100"><X className="w-4 h-4" /></button>
                </div>
            )}
        </div>
    );
}
