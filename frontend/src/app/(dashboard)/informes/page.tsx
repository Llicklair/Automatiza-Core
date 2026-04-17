"use client";

import { BarChart3, FileText, Download, Receipt, Trash2 } from "lucide-react";
import { useInformes } from "./_hooks/useInformes";
import { Section, TabBtn } from "./_components/InformesHelpers";
import { GestionTab } from "./_components/GestionTab";
import { FiscalTab } from "./_components/FiscalTab";

export default function InformesPage() {
    const {
        tab, setTab,
        month, setMonth, snap, loading, generating, error, genOk, isCurrentOrPast,
        loadSnapshot, handleGenerate,
        fiscalMode, setFiscalMode, fiscalMonth, setFiscalMonth,
        fiscalQuarter, setFiscalQuarter,
        fiscalSnap, fiscalLoading, fiscalGenerating, fiscalError, fiscalGenOk,
        loadFiscalSnapshot, handleGenerateFiscal,
        reports, handleDownload, handleDeleteReport,
    } = useInformes();

    return (
        <div className="p-6 max-w-6xl mx-auto space-y-6">

            {/* Header + Tabs */}
            <div className="flex items-center justify-between gap-4 flex-wrap">
                <div>
                    <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
                        <BarChart3 className="w-6 h-6 text-primary" />
                        Informes IA
                    </h1>
                    <p className="text-sm text-muted-foreground mt-0.5">Informes generados automáticamente por IA</p>
                </div>
                <div className="flex items-center gap-1 rounded-xl border border-border bg-card p-1">
                    <TabBtn active={tab === "gestion"} label="Gestión" icon={BarChart3} onClick={() => setTab("gestion")} />
                    <TabBtn active={tab === "fiscal"} label="Fiscal" icon={Receipt} onClick={() => setTab("fiscal")} />
                </div>
            </div>

            {tab === "gestion" && (
                <GestionTab
                    month={month} setMonth={setMonth}
                    snap={snap} loading={loading} generating={generating}
                    error={error} genOk={genOk} isCurrentOrPast={isCurrentOrPast}
                    loadSnapshot={loadSnapshot} handleGenerate={handleGenerate}
                />
            )}

            {tab === "fiscal" && (
                <FiscalTab
                    fiscalMode={fiscalMode} setFiscalMode={setFiscalMode}
                    fiscalMonth={fiscalMonth} setFiscalMonth={setFiscalMonth}
                    fiscalQuarter={fiscalQuarter} setFiscalQuarter={setFiscalQuarter}
                    fiscalSnap={fiscalSnap} fiscalLoading={fiscalLoading}
                    fiscalGenerating={fiscalGenerating} fiscalError={fiscalError}
                    fiscalGenOk={fiscalGenOk}
                    loadFiscalSnapshot={loadFiscalSnapshot}
                    handleGenerateFiscal={handleGenerateFiscal}
                />
            )}

            {/* Informes PDF generados (shared) */}
            {reports.length > 0 && (
                <Section title="Informes PDF generados" icon={FileText}>
                    <div className="space-y-2">
                        {reports.map(r => (
                            <div key={r.id} className="flex items-center justify-between py-2 border-b border-border last:border-0 gap-3">
                                <div className="flex items-center gap-3 min-w-0">
                                    <FileText className="w-4 h-4 text-muted-foreground shrink-0" />
                                    <div className="min-w-0">
                                        <p className="text-sm text-foreground truncate">{r.file_name}</p>
                                        <p className="text-xs text-muted-foreground">{new Date(r.created_at).toLocaleDateString("es-ES")} · {(r.file_size / 1024).toFixed(0)} KB</p>
                                    </div>
                                </div>
                                <div className="flex items-center gap-2 shrink-0">
                                    <button
                                        onClick={() => handleDownload(r.id, r.file_name)}
                                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border text-xs text-foreground hover:bg-accent/50 transition-colors"
                                    >
                                        <Download className="w-3.5 h-3.5" /> Descargar
                                    </button>
                                    <button
                                        onClick={() => handleDeleteReport(r.id)}
                                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-red-500/20 text-xs text-red-400 hover:bg-red-500/10 transition-colors"
                                    >
                                        <Trash2 className="w-3.5 h-3.5" />
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                </Section>
            )}
        </div>
    );
}
