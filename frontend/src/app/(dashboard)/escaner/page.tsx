"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { ScanLine, AlertTriangle, FileSpreadsheet, FileText } from "lucide-react";
import { useEscaner, getElectronAPI } from "./_hooks/useEscaner";
import LanToggle from "./_components/LanToggle";
import DropZone from "./_components/DropZone";
import SelectedFilesList from "./_components/SelectedFilesList";
import ScanResults from "./_components/ScanResults";
import { ExcelImportPanel } from "./_components/ExcelImportPanel";
import { FacturasImportPanel } from "./_components/FacturasImportPanel";
import { PageContainer } from "@/components/shared/PageContainer";

type Tab = "escaner" | "facturas" | "excel";

export default function EscanerPage() {
    const {
        scanning, results, error, dragOver, setDragOver,
        selectedFiles, docStatuses, fileInputRef,
        netStatus, netToggling, handleLanToggle,
        handleFiles, removeFile, handleScan, grouped,
    } = useEscaner();

    const searchParams = useSearchParams();
    const initialTab = searchParams.get("tab");
    const [tab, setTab] = useState<Tab>(
        initialTab === "excel" ? "excel" : initialTab === "facturas" ? "facturas" : "escaner"
    );

    const tabs: { key: Tab; label: string; icon: typeof ScanLine }[] = [
        { key: "escaner", label: "Escáner", icon: ScanLine },
        { key: "facturas", label: "Facturas → ERP", icon: FileText },
        { key: "excel", label: "Importar Excel", icon: FileSpreadsheet },
    ];

    return (
        <PageContainer width="4xl">
            {/* Header */}
            <div>
                <div className="flex items-center gap-3 mb-1">
                    <ScanLine className="w-7 h-7 text-primary" />
                    <h1 className="text-2xl font-bold text-foreground">Escáner e importación</h1>
                </div>
                <p className="text-sm text-muted-foreground mt-1">
                    Sube cualquier archivo y la IA lo clasifica, o importa hojas de cálculo como datos.
                </p>
            </div>

            {/* Pestañas */}
            <div className="flex items-center gap-1 border-b border-border">
                {tabs.map(t => {
                    const Icon = t.icon;
                    const active = tab === t.key;
                    return (
                        <button
                            key={t.key}
                            onClick={() => setTab(t.key)}
                            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${
                                active
                                    ? "border-primary text-foreground"
                                    : "border-transparent text-muted-foreground hover:text-foreground"
                            }`}>
                            <Icon className="w-4 h-4" /> {t.label}
                        </button>
                    );
                })}
            </div>

            {tab === "escaner" ? (
                <div className="space-y-8">
                    {getElectronAPI()?.getNetworkStatus && netStatus && (
                        <LanToggle netStatus={netStatus} netToggling={netToggling} onToggle={handleLanToggle} />
                    )}

                    <DropZone dragOver={dragOver} setDragOver={setDragOver}
                        onFiles={handleFiles} fileInputRef={fileInputRef} />

                    <SelectedFilesList files={selectedFiles} scanning={scanning}
                        onRemove={removeFile} onScan={handleScan} />

                    {error && (
                        <div className="rounded-lg border border-red-500/20 bg-red-500/5 px-4 py-3 text-sm text-red-400 flex items-center gap-2">
                            <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                            {error}
                        </div>
                    )}

                    <ScanResults results={results} grouped={grouped} docStatuses={docStatuses} />
                </div>
            ) : tab === "facturas" ? (
                <FacturasImportPanel />
            ) : (
                <ExcelImportPanel />
            )}
        </PageContainer>
    );
}
