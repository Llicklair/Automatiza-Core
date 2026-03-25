"use client";

import { useRef, useState } from "react";
import { Database, X, Table2, Loader2, CheckCircle2, FolderOpen } from "lucide-react";

export type ImportResult = {
    document_id: string;
    file_name: string;
    rows_detected: number;
    columns: string[];
    category: string;
    task_id: string | null;
    message: string;
};

interface ImportDbModalProps {
    importing: boolean;
    importResults: ImportResult[];
    importFiles: File[];
    setImportFiles: React.Dispatch<React.SetStateAction<File[]>>;
    onImport: () => void;
    onClose: () => void;
}

export default function ImportDbModal({
    importing, importResults, importFiles, setImportFiles, onImport, onClose,
}: ImportDbModalProps) {
    const importFileRef = useRef<HTMLInputElement>(null);
    const [importDragOver, setImportDragOver] = useState(false);

    function handleImportFiles(files: FileList | null) {
        if (!files) return;
        setImportFiles(prev => [...prev, ...Array.from(files)]);
    }

    return (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-[#111113] border border-[#27272a] rounded-2xl shadow-2xl w-full max-w-2xl overflow-hidden flex flex-col max-h-[85vh]">
                <div className="px-6 py-4 border-b border-[#27272a] flex items-center justify-between bg-zinc-900/50">
                    <h2 className="text-xl font-bold text-white flex items-center gap-2">
                        <Database className="w-5 h-5 text-emerald-400" /> Importar Base de Datos
                    </h2>
                    <button
                        onClick={onClose}
                        className="p-2 rounded-lg hover:bg-white/5 text-zinc-400 hover:text-white transition-colors"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                <div className="p-6 space-y-5 overflow-y-auto">
                    <p className="text-sm text-zinc-400">
                        Sube archivos <span className="text-white font-medium">CSV, Excel (.xlsx), JSON u ODS</span>.
                        La IA analizara las columnas, detectara que tipo de datos contienen y los diseminara
                        en las entidades correctas (clientes, facturas, empleados, etc.).
                    </p>

                    <div
                        onDragOver={e => { e.preventDefault(); setImportDragOver(true); }}
                        onDragLeave={() => setImportDragOver(false)}
                        onDrop={e => { e.preventDefault(); setImportDragOver(false); handleImportFiles(e.dataTransfer.files); }}
                        onClick={() => importFileRef.current?.click()}
                        className={`rounded-xl border-2 border-dashed p-8 text-center transition-all cursor-pointer ${
                            importDragOver
                                ? "border-emerald-500 bg-emerald-500/10 scale-[1.01]"
                                : "border-[#27272a] bg-zinc-900 hover:border-zinc-500"
                        }`}
                    >
                        <div className="flex justify-center mb-3">
                            <div className="w-12 h-12 rounded-full bg-emerald-500/10 flex items-center justify-center">
                                <Table2 className={`w-6 h-6 ${importDragOver ? "text-emerald-400" : "text-emerald-500"}`} />
                            </div>
                        </div>
                        <h3 className="text-base font-medium text-white mb-1">Arrastra archivos de datos o haz clic</h3>
                        <p className="text-xs text-zinc-500">CSV, XLSX, JSON, ODS</p>
                        <input
                            ref={importFileRef}
                            type="file"
                            className="hidden"
                            multiple
                            accept=".csv,.xlsx,.xls,.json,.ods"
                            onChange={e => handleImportFiles(e.target.files)}
                        />
                    </div>

                    {importFiles.length > 0 && (
                        <div className="space-y-2">
                            <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-wide">Archivos ({importFiles.length})</h3>
                            <div className="rounded-lg border border-[#27272a] divide-y divide-[#27272a]">
                                {importFiles.map((f, i) => (
                                    <div key={i} className="flex items-center justify-between px-4 py-2">
                                        <div className="flex items-center gap-2 min-w-0">
                                            <Table2 className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                                            <span className="text-sm text-white truncate">{f.name}</span>
                                            <span className="text-xs text-zinc-600">{(f.size / 1024).toFixed(0)} KB</span>
                                        </div>
                                        <button
                                            onClick={() => setImportFiles(prev => prev.filter((_, j) => j !== i))}
                                            className="p-1 rounded hover:bg-red-500/10 text-zinc-600 hover:text-red-400 transition"
                                        >
                                            <X className="w-3.5 h-3.5" />
                                        </button>
                                    </div>
                                ))}
                            </div>
                            <button
                                onClick={onImport}
                                disabled={importing}
                                className="w-full flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white py-3 rounded-xl font-semibold transition-all"
                            >
                                {importing ? (
                                    <><Loader2 className="w-4 h-4 animate-spin" /> Importando y analizando...</>
                                ) : (
                                    <><Database className="w-4 h-4" /> Importar {importFiles.length} archivo{importFiles.length > 1 ? "s" : ""}</>
                                )}
                            </button>
                        </div>
                    )}

                    {importResults.length > 0 && (
                        <div className="space-y-3">
                            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                                <CheckCircle2 className="w-4 h-4 text-emerald-400" /> Resultados
                            </h3>
                            {importResults.map((r, i) => (
                                <div key={i} className="rounded-xl border border-[#27272a] bg-zinc-900/50 p-4 space-y-2">
                                    <div className="flex items-center justify-between">
                                        <span className="text-sm font-medium text-white">{r.file_name}</span>
                                        <span className="text-xs text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full flex items-center gap-1">
                                            <FolderOpen className="w-3 h-3" /> {r.category}
                                        </span>
                                    </div>
                                    <div className="text-xs text-zinc-400">
                                        <span className="text-white font-medium">{r.rows_detected}</span> filas detectadas
                                    </div>
                                    {r.columns.length > 0 && (
                                        <div className="flex flex-wrap gap-1.5">
                                            {r.columns.slice(0, 12).map((col, j) => (
                                                <span key={j} className="text-[10px] bg-zinc-800 text-zinc-400 px-2 py-0.5 rounded-md border border-[#27272a]">{col}</span>
                                            ))}
                                            {r.columns.length > 12 && <span className="text-[10px] text-zinc-600">+{r.columns.length - 12} mas</span>}
                                        </div>
                                    )}
                                    <p className="text-xs text-zinc-500">{r.message}</p>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
