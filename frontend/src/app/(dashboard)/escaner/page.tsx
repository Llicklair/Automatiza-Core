"use client";

import { ScanLine, AlertTriangle } from "lucide-react";
import { useEscaner, getElectronAPI } from "./_hooks/useEscaner";
import LanToggle from "./_components/LanToggle";
import DropZone from "./_components/DropZone";
import SelectedFilesList from "./_components/SelectedFilesList";
import ScanResults from "./_components/ScanResults";

export default function EscanerPage() {
    const {
        scanning, results, error, dragOver, setDragOver,
        selectedFiles, docStatuses, fileInputRef,
        netStatus, netToggling, handleLanToggle,
        handleFiles, removeFile, handleScan, grouped,
    } = useEscaner();

    return (
        <div className="p-8 max-w-4xl mx-auto space-y-8">
            {/* Header */}
            <div>
                <div className="flex items-center gap-3 mb-1">
                    <ScanLine className="w-7 h-7 text-primary" />
                    <h1 className="text-2xl font-bold text-foreground">Escaner Inteligente</h1>
                </div>
                <p className="text-sm text-muted-foreground mt-1">
                    Sube cualquier archivo y la IA lo clasificara automaticamente en la carpeta correcta.
                </p>
            </div>

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
    );
}
