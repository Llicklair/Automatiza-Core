"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import {
    ScanLine, AlertTriangle, FileSpreadsheet, FileText, FolderUp, Sparkles, Receipt,
} from "lucide-react";
import { useEscaner, getElectronAPI } from "./_hooks/useEscaner";
import LanToggle from "./_components/LanToggle";
import DropZone from "./_components/DropZone";
import SelectedFilesList from "./_components/SelectedFilesList";
import ScanResults from "./_components/ScanResults";
import { ExcelImportPanel } from "./_components/ExcelImportPanel";
import { FacturasImportPanel } from "./_components/FacturasImportPanel";
import { PageContainer } from "@/components/shared/PageContainer";

type Mode = "auto" | "facturas" | "excel" | "documento";

const isExcel = (f: File) => /\.(xlsx|xls|csv)$/i.test(f.name);

const MODES: { key: Mode; label: string; icon: typeof Sparkles }[] = [
    { key: "auto", label: "Automático", icon: Sparkles },
    { key: "facturas", label: "Factura", icon: FileText },
    { key: "excel", label: "Excel", icon: FileSpreadsheet },
    { key: "documento", label: "Documento", icon: FolderUp },
];

export default function EscanerPage() {
    const esc = useEscaner();

    // Modo inicial: ?mode= (intake unificado) o ?tab= (retro-compat de enlaces antiguos).
    const searchParams = useSearchParams();
    const q = searchParams.get("mode") ?? searchParams.get("tab");
    const [mode, setMode] = useState<Mode>(
        q === "facturas" || q === "excel" || q === "documento" ? (q as Mode) : "auto"
    );

    // Archivos enrutados a un panel especializado (carry desde el auto-detect, sin re-subir).
    const [routedFiles, setRoutedFiles] = useState<File[]>([]);
    // Archivos no-excel soltados (para poder pasarlos a Facturas si la IA detecta facturas).
    const [docFiles, setDocFiles] = useState<File[]>([]);

    // Auto-detección: decide a dónde van los archivos según el modo.
    function route(files: FileList | null) {
        if (!files || !files.length) return;
        const arr = Array.from(files);

        if (mode === "excel") { setRoutedFiles(arr.filter(isExcel)); return; }
        if (mode === "facturas") { setRoutedFiles(arr); return; }
        if (mode === "documento") { setDocFiles((p) => [...p, ...arr]); esc.handleFiles(files); return; }

        // mode === "auto"
        const excel = arr.filter(isExcel);
        const other = arr.filter((f) => !isExcel(f));
        if (excel.length && !other.length) {
            setMode("excel");
            setRoutedFiles(excel);
            return;
        }
        // PDFs / imágenes / otros → escaneo + clasificación con IA
        setDocFiles((p) => [...p, ...other]);
        esc.handleFiles(files);
    }

    const switchMode = (m: Mode) => { setMode(m); setRoutedFiles([]); };

    const showScan = mode === "auto" || mode === "documento";
    // Tras clasificar, ¿la IA detectó facturas de compra? → sugerir procesarlas al ERP.
    const invoiceHits = esc.results.filter((r) => /factura|compra|invoice/i.test(r.auto_category));

    return (
        <PageContainer width="4xl">
            {/* Header */}
            <div>
                <div className="flex items-center gap-3 mb-1">
                    <ScanLine className="w-7 h-7 text-primary" />
                    <h1 className="text-2xl font-bold text-foreground">Escáner e importación</h1>
                </div>
                <p className="text-sm text-muted-foreground mt-1">
                    Arrastra cualquier archivo —factura, documento o excel— y lo detectamos por ti.
                    También puedes elegir el modo a mano.
                </p>
            </div>

            {/* Selector de modo: una entrada, varias opciones */}
            <div className="flex flex-wrap items-center gap-1.5">
                {MODES.map((m) => {
                    const Icon = m.icon;
                    const active = mode === m.key;
                    return (
                        <button
                            key={m.key}
                            onClick={() => switchMode(m.key)}
                            className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium border transition-colors ${
                                active
                                    ? "border-primary bg-primary/10 text-foreground"
                                    : "border-border text-muted-foreground hover:text-foreground hover:border-primary/40"
                            }`}>
                            <Icon className="w-4 h-4" /> {m.label}
                        </button>
                    );
                })}
            </div>

            {showScan ? (
                <div className="space-y-6">
                    {getElectronAPI()?.getNetworkStatus && esc.netStatus && (
                        <LanToggle netStatus={esc.netStatus} netToggling={esc.netToggling} onToggle={esc.handleLanToggle} />
                    )}

                    <DropZone dragOver={esc.dragOver} setDragOver={esc.setDragOver}
                        onFiles={route} fileInputRef={esc.fileInputRef} />

                    <SelectedFilesList files={esc.selectedFiles} scanning={esc.scanning}
                        onRemove={esc.removeFile} onScan={esc.handleScan} />

                    {esc.error && (
                        <div className="rounded-lg border border-red-500/20 bg-red-500/5 px-4 py-3 text-sm text-red-400 flex items-center gap-2">
                            <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                            {esc.error}
                        </div>
                    )}

                    {invoiceHits.length > 0 && (
                        <button
                            onClick={() => { setRoutedFiles(docFiles); setMode("facturas"); }}
                            className="w-full flex items-center gap-2 rounded-lg border border-primary/30 bg-primary/5 px-4 py-3 text-sm text-foreground hover:bg-primary/10 transition-colors text-left">
                            <Receipt className="w-4 h-4 text-primary flex-shrink-0" />
                            <span>
                                Detecté {invoiceHits.length} factura{invoiceHits.length !== 1 ? "s" : ""} de compra.{" "}
                                <span className="font-medium text-primary">Procesarlas al ERP →</span>{" "}
                                <span className="text-muted-foreground">(crea factura + asiento + stock)</span>
                            </span>
                        </button>
                    )}

                    <ScanResults results={esc.results} grouped={esc.grouped} docStatuses={esc.docStatuses} />
                </div>
            ) : mode === "facturas" ? (
                <FacturasImportPanel initialFiles={routedFiles} />
            ) : (
                <ExcelImportPanel initialFiles={routedFiles} />
            )}
        </PageContainer>
    );
}
