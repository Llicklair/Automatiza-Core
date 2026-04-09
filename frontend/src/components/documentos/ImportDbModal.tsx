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
            <div className="bg-card border border-border rounded-2xl shadow-2xl w-full max-w-2xl overflow-hidden flex flex-col max-h-[85vh]">
                <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-card">
                    <h2 className="text-xl font-bold text-foreground flex items-center gap-2">
                        <Database className="w-5 h-5 text-emerald-400" /> Importar Base de Datos
                    </h2>
                    <button
                        onClick={onClose}
                        className="p-2 rounded-lg hover:bg-white/5 text-muted-foreground hover:text-foreground transition-colors"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                <div className="p-6 space-y-5 overflow-y-auto">
                    <p className="text-sm text-muted-foreground">
                        Sube archivos <span className="text-foreground font-medium">CSV, Excel (.xlsx), JSON u ODS</span>.
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
                                : "border-border bg-card hover:border-muted-foreground"
                        }`}
                    >
                        <div className="flex justify-center mb-3">
                            <div className="w-12 h-12 rounded-full bg-emerald-500/10 flex items-center justify-center">
                                <Table2 className={`w-6 h-6 ${importDragOver ? "text-emerald-400" : "text-emerald-500"}`} />
                            </div>
                        </div>
                        <h3 className="text-base font-medium text-foreground mb-1">Arrastra archivos de datos o haz clic</h3>
                        <p className="text-xs text-muted-foreground">CSV, XLSX, JSON, ODS</p>
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
                            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Archivos ({importFiles.length})</h3>
                            <div className="rounded-lg border border-border divide-y divide-border">
                                {importFiles.map((f, i) => (
                                    <div key={i} className="flex items-center justify-between px-4 py-2">
                                        <div className="flex items-center gap-2 min-w-0">
                                            <Table2 className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                                            <span className="text-sm text-foreground truncate">{f.name}</span>
                                            <span className="text-xs text-muted-foreground">{(f.size / 1024).toFixed(0)} KB</span>
                                        </div>
                                        <button
                                            onClick={() => setImportFiles(prev => prev.filter((_, j) => j !== i))}
                                            className="p-1 rounded hover:bg-red-500/10 text-muted-foreground hover:text-red-400 transition"
                                        >
                                            <X className="w-3.5 h-3.5" />
                                        </button>
                                    </div>
                                ))}
                            </div>
                            <button
                                onClick={onImport}
                                disabled={importing}
                                className="w-full flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-foreground py-3 rounded-xl font-semibold transition-all"
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
                            <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                                <CheckCircle2 className="w-4 h-4 text-emerald-400" /> Resultados
                            </h3>
                            {importResults.map((r, i) => (
                                <div key={i} className="rounded-xl border border-border bg-card p-4 space-y-2">
                                    <div className="flex items-center justify-between">
                                        <span className="text-sm font-medium text-foreground">{r.file_name}</span>
                                        <span className="text-xs text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full flex items-center gap-1">
                                            <FolderOpen className="w-3 h-3" /> {r.category}
                                        </span>
                                    </div>
                                    <div className="text-xs text-muted-foreground">
                                        <span className="text-foreground font-medium">{r.rows_detected}</span> filas detectadas
                                    </div>
                                    {r.columns.length > 0 && (
                                        <div className="flex flex-wrap gap-1.5">
                                            {r.columns.slice(0, 12).map((col, j) => (
                                                <span key={j} className="text-[10px] bg-muted text-muted-foreground px-2 py-0.5 rounded-md border border-border">{col}</span>
                                            ))}
                                            {r.columns.length > 12 && <span className="text-[10px] text-muted-foreground">+{r.columns.length - 12} mas</span>}
                                        </div>
                                    )}
                                    <p className="text-xs text-muted-foreground">{r.message}</p>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
