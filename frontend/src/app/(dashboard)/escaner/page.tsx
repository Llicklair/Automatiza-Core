"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { api } from "@/lib/api";
import {
    ScanLine, Upload, Loader2, CheckCircle2, AlertTriangle,
    FileText, FileImage, Sheet, Mail, X, FolderOpen,
} from "lucide-react";

type ScanResult = {
    document: { id: string; file_name: string; file_type: string | null; file_size: number; status: string; category: string | null };
    auto_category: string;
    message: string;
};

const CATEGORY_INFO: Record<string, { label: string; icon: typeof FileText; color: string; bg: string }> = {
    facturas: { label: "Facturas", icon: FileText, color: "text-indigo-400", bg: "bg-indigo-500/10" },
    bancos: { label: "Bancos", icon: FileText, color: "text-blue-400", bg: "bg-blue-500/10" },
    nominas: { label: "Nóminas", icon: FileText, color: "text-emerald-400", bg: "bg-emerald-500/10" },
    fiscal: { label: "Asesor Fiscal", icon: AlertTriangle, color: "text-amber-400", bg: "bg-amber-500/10" },
    crm: { label: "CRM", icon: FileText, color: "text-rose-400", bg: "bg-rose-500/10" },
    excels: { label: "Excels", icon: Sheet, color: "text-green-400", bg: "bg-green-500/10" },
    informes: { label: "Informes", icon: Sheet, color: "text-purple-400", bg: "bg-purple-500/10" },
    correos: { label: "Correos", icon: Mail, color: "text-sky-400", bg: "bg-sky-500/10" },
    automatizaciones: { label: "Automatización", icon: Loader2, color: "text-orange-400", bg: "bg-orange-500/10" },
    rrhh: { label: "RRHH", icon: FileText, color: "text-zinc-400", bg: "bg-zinc-500/10" },
    otros: { label: "Otros", icon: FileImage, color: "text-zinc-500", bg: "bg-zinc-500/5" },
};

function formatSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function EscanerPage() {
    const [scanning, setScanning] = useState(false);
    const [results, setResults] = useState<ScanResult[]>([]);
    const [error, setError] = useState("");
    const [dragOver, setDragOver] = useState(false);
    const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
    const [docStatuses, setDocStatuses] = useState<Record<string, { status: string; category: string | null }>>({});
    const fileInputRef = useRef<HTMLInputElement>(null);

    // Polling: actualizar estado de documentos que están procesando
    useEffect(() => {
        if (results.length === 0) return;
        const processing = results.filter(r => {
            const st = docStatuses[r.document.id];
            return !st || st.status === "processing" || st.status === "uploaded";
        });
        if (processing.length === 0) return;

        const interval = setInterval(async () => {
            try {
                // Consultar todos los documentos para ver su estado actual
                const allDocs = await api.documents.list({});
                const statusMap: Record<string, { status: string; category: string | null }> = {};
                for (const doc of allDocs) {
                    statusMap[doc.id] = { status: doc.status, category: doc.category };
                }
                setDocStatuses(prev => ({ ...prev, ...statusMap }));
            } catch {
                // silenciar errores de polling
            }
        }, 4000);

        return () => clearInterval(interval);
    }, [results, docStatuses]);

    const handleFiles = useCallback((files: FileList | null) => {
        if (!files || files.length === 0) return;
        setSelectedFiles(prev => [...prev, ...Array.from(files)]);
        setError("");
    }, []);

    const removeFile = (index: number) => {
        setSelectedFiles(prev => prev.filter((_, i) => i !== index));
    };

    async function handleScan() {
        if (selectedFiles.length === 0) return;
        setScanning(true);
        setError("");
        setResults([]);

        try {
            const res = await api.documents.scan(selectedFiles);
            setResults(res);
            setSelectedFiles([]);
        } catch (e: any) {
            setError(e.message || "Error al escanear archivos");
        } finally {
            setScanning(false);
        }
    }

    // Agrupar resultados por categoría
    const grouped = results.reduce<Record<string, ScanResult[]>>((acc, r) => {
        const cat = r.auto_category;
        if (!acc[cat]) acc[cat] = [];
        acc[cat].push(r);
        return acc;
    }, {});

    return (
        <div className="p-8 max-w-4xl mx-auto space-y-8">
            {/* Header */}
            <div>
                <div className="flex items-center gap-3 mb-1">
                    <ScanLine className="w-7 h-7 text-indigo-400" />
                    <h1 className="text-2xl font-bold text-white">Escáner Inteligente</h1>
                </div>
                <p className="text-sm text-zinc-400 mt-1">
                    Sube cualquier archivo y la IA lo clasificará automáticamente en la carpeta correcta.
                </p>
            </div>

            {/* Drop Zone */}
            <div
                onDragOver={e => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onDrop={e => { e.preventDefault(); setDragOver(false); handleFiles(e.dataTransfer.files); }}
                onClick={() => fileInputRef.current?.click()}
                className={`rounded-2xl border-2 border-dashed p-12 text-center transition-all duration-300 cursor-pointer ${
                    dragOver
                        ? "border-indigo-500 bg-indigo-500/10 scale-[1.01]"
                        : "border-[#27272a] bg-[#111113] hover:border-zinc-600"
                }`}
            >
                <div className="flex justify-center mb-4">
                    <div className={`w-16 h-16 rounded-2xl flex items-center justify-center transition-colors ${
                        dragOver ? "bg-indigo-500/20" : "bg-zinc-800"
                    }`}>
                        <ScanLine className={`w-8 h-8 transition-colors ${dragOver ? "text-indigo-400" : "text-zinc-500"}`} />
                    </div>
                </div>
                <h3 className="text-lg font-semibold text-white mb-1">
                    Arrastra archivos aquí o haz clic para seleccionar
                </h3>
                <p className="text-sm text-zinc-500 max-w-md mx-auto">
                    PDFs, imágenes, hojas de cálculo, correos... cualquier formato.
                    La IA detectará el tipo y lo clasificará automáticamente.
                </p>
                <input
                    ref={fileInputRef}
                    type="file"
                    className="hidden"
                    multiple
                    accept=".pdf,.png,.jpg,.jpeg,.docx,.xlsx,.xls,.csv,.txt,.eml,.msg,.ods,.odt,.webp,.tiff,.tif,.bmp,.gif,.zip"
                    onChange={e => handleFiles(e.target.files)}
                />
            </div>

            {/* Selected Files */}
            {selectedFiles.length > 0 && (
                <div className="space-y-3">
                    <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wide">
                        Archivos seleccionados ({selectedFiles.length})
                    </h2>
                    <div className="rounded-xl border border-[#27272a] bg-[#111113] divide-y divide-[#27272a]">
                        {selectedFiles.map((file, i) => (
                            <div key={i} className="flex items-center justify-between px-5 py-3">
                                <div className="flex items-center gap-3 min-w-0">
                                    <FileText className="w-4 h-4 text-zinc-500 flex-shrink-0" />
                                    <span className="text-sm text-white truncate">{file.name}</span>
                                    <span className="text-xs text-zinc-600">{formatSize(file.size)}</span>
                                </div>
                                <button
                                    onClick={(e) => { e.stopPropagation(); removeFile(i); }}
                                    className="p-1 rounded hover:bg-red-500/10 text-zinc-600 hover:text-red-400 transition"
                                >
                                    <X className="w-4 h-4" />
                                </button>
                            </div>
                        ))}
                    </div>

                    <button
                        onClick={handleScan}
                        disabled={scanning}
                        className="w-full flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white py-3 rounded-xl font-semibold transition-all shadow-lg shadow-indigo-500/20"
                    >
                        {scanning ? (
                            <>
                                <Loader2 className="w-5 h-5 animate-spin" />
                                Escaneando y clasificando...
                            </>
                        ) : (
                            <>
                                <ScanLine className="w-5 h-5" />
                                Escanear {selectedFiles.length} archivo{selectedFiles.length > 1 ? "s" : ""}
                            </>
                        )}
                    </button>
                </div>
            )}

            {/* Error */}
            {error && (
                <div className="rounded-lg border border-red-500/20 bg-red-500/5 px-4 py-3 text-sm text-red-400 flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                    {error}
                </div>
            )}

            {/* Results */}
            {results.length > 0 && (
                <div className="space-y-4">
                    {(() => {
                        const done = results.filter(r => {
                            const st = docStatuses[r.document.id]?.status || r.document.status;
                            return st === "completed" || st === "processed" || st === "ready";
                        }).length;
                        const failed = results.filter(r => (docStatuses[r.document.id]?.status || r.document.status) === "failed").length;
                        const pending = results.length - done - failed;
                        return (
                            <>
                                <div className="flex items-center gap-3">
                                    {pending > 0 ? (
                                        <Loader2 className="w-5 h-5 text-amber-400 animate-spin" />
                                    ) : (
                                        <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                                    )}
                                    <h2 className="text-lg font-semibold text-white">
                                        {results.length} archivo{results.length > 1 ? "s" : ""}
                                    </h2>
                                    <div className="flex gap-2 text-xs">
                                        {done > 0 && <span className="text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full">{done} listos</span>}
                                        {pending > 0 && <span className="text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded-full">{pending} procesando</span>}
                                        {failed > 0 && <span className="text-red-400 bg-red-500/10 px-2 py-0.5 rounded-full">{failed} errores</span>}
                                    </div>
                                </div>
                                {/* Barra de progreso */}
                                <div className="w-full h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                                    <div
                                        className="h-full bg-gradient-to-r from-emerald-500 to-emerald-400 transition-all duration-500 rounded-full"
                                        style={{ width: `${((done + failed) / results.length) * 100}%` }}
                                    />
                                </div>
                            </>
                        );
                    })()}

                    {Object.entries(grouped).map(([cat, items]) => {
                        const info = CATEGORY_INFO[cat] || CATEGORY_INFO.otros;
                        const Icon = info.icon;
                        return (
                            <div key={cat} className="rounded-xl border border-[#27272a] bg-[#111113] overflow-hidden">
                                <div className="px-5 py-3 border-b border-[#27272a] flex items-center gap-3 bg-zinc-900/30">
                                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${info.bg}`}>
                                        <FolderOpen className={`w-4 h-4 ${info.color}`} />
                                    </div>
                                    <div>
                                        <h3 className={`text-sm font-semibold ${info.color}`}>{info.label}</h3>
                                        <p className="text-[10px] text-zinc-600">{items.length} archivo{items.length > 1 ? "s" : ""}</p>
                                    </div>
                                </div>
                                <div className="divide-y divide-[#27272a]">
                                    {items.map((r, i) => {
                                        const live = docStatuses[r.document.id];
                                        const st = live?.status || r.document.status;
                                        const finalCat = live?.category || r.auto_category;
                                        const reclassified = finalCat !== r.auto_category;
                                        const isDone = st === "completed" || st === "processed" || st === "ready";
                                        const isFailed = st === "failed";

                                        return (
                                            <div key={i} className="flex items-center justify-between px-5 py-3">
                                                <div className="flex items-center gap-3 min-w-0">
                                                    <Icon className={`w-4 h-4 ${info.color} flex-shrink-0`} />
                                                    <span className="text-sm text-white truncate">{r.document.file_name}</span>
                                                    <span className="text-xs text-zinc-600">{formatSize(r.document.file_size)}</span>
                                                    {reclassified && (
                                                        <span className="text-[10px] text-indigo-400 bg-indigo-500/10 px-1.5 py-0.5 rounded">
                                                            → {(CATEGORY_INFO[finalCat] || CATEGORY_INFO.otros).label}
                                                        </span>
                                                    )}
                                                </div>
                                                <div className="flex items-center gap-2">
                                                    {isDone ? (
                                                        <span className="text-[10px] text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full flex items-center gap-1">
                                                            <CheckCircle2 className="w-3 h-3" /> Clasificado
                                                        </span>
                                                    ) : isFailed ? (
                                                        <span className="text-[10px] text-red-400 bg-red-500/10 px-2 py-0.5 rounded-full flex items-center gap-1">
                                                            <AlertTriangle className="w-3 h-3" /> Error
                                                        </span>
                                                    ) : (
                                                        <span className="text-[10px] text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded-full">
                                                            <Loader2 className="w-3 h-3 inline-block mr-1 animate-spin" />
                                                            IA analizando
                                                        </span>
                                                    )}
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
