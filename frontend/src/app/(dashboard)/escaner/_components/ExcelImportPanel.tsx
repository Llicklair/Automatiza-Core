"use client";

import { useState, useEffect, useRef } from "react";
import { Upload, Loader2, AlertCircle, CheckCircle2, Download, Trash2, FileSpreadsheet, Database } from "lucide-react";
import { api } from "@/lib/api";
import type { Document } from "@/lib/api/documents";
import { ErpImportReview } from "./ErpImportReview";

export function ExcelImportPanel() {
    const [documents, setDocuments] = useState<Document[]>([]);
    const [loadingList, setLoadingList] = useState(true);
    const [uploading, setUploading] = useState(false);
    const [result, setResult] = useState<{ ok: boolean; message: string } | null>(null);
    const [integrating, setIntegrating] = useState<Document | null>(null);
    const fileRef = useRef<HTMLInputElement>(null);

    async function loadDocuments() {
        setLoadingList(true);
        try {
            const docs = await api.documents.list({ category: "excel" });
            setDocuments(docs);
        } catch {
            // silently ignore
        } finally {
            setLoadingList(false);
        }
    }

    useEffect(() => { loadDocuments(); }, []);

    async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
        const file = e.target.files?.[0];
        if (!file) return;
        setUploading(true);
        setResult(null);
        try {
            const imported = await api.documents.importDB([file]);
            const count = imported.length;
            setResult({ ok: true, message: `${count} hoja${count !== 1 ? "s" : ""} importada${count !== 1 ? "s" : ""} correctamente` });
            await loadDocuments();
        } catch (err: unknown) {
            setResult({ ok: false, message: err instanceof Error ? err.message : "Error al importar archivo" });
        } finally {
            setUploading(false);
            if (fileRef.current) fileRef.current.value = "";
        }
    }

    async function handleDelete(id: string, filename: string) {
        if (!confirm(`¿Eliminar "${filename}"?`)) return;
        try {
            await api.documents.delete(id);
            setDocuments(prev => prev.filter(d => d.id !== id));
        } catch (err: unknown) {
            setResult({ ok: false, message: err instanceof Error ? err.message : "Error al eliminar" });
        }
    }

    return (
        <div className="space-y-6">
            <p className="text-sm text-muted-foreground">
                Importa hojas de cálculo (.xlsx, .xls, .csv). Quedan disponibles para que la IA
                las analice y, con <strong>«Integrar en ERP»</strong>, puedes crear productos,
                clientes/proveedores o empleados directamente desde sus filas (con revisión previa).
            </p>

            {/* Upload area */}
            <label className={`flex flex-col items-center justify-center gap-3 border-2 border-dashed rounded-xl px-6 py-10 cursor-pointer transition-colors ${
                uploading ? "border-violet-500/50 bg-violet-500/5" : "border-border hover:border-violet-500/50 hover:bg-violet-500/5"
            }`}>
                {uploading
                    ? <Loader2 className="w-8 h-8 text-violet-400 animate-spin" />
                    : <Upload className="w-8 h-8 text-muted-foreground" />
                }
                <div className="text-center">
                    <p className="text-sm font-medium text-foreground">
                        {uploading ? "Importando..." : "Arrastra un archivo o haz clic para subir"}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">.xlsx, .xls, .csv</p>
                </div>
                <input
                    ref={fileRef}
                    type="file"
                    accept=".xlsx,.xls,.csv"
                    className="hidden"
                    disabled={uploading}
                    onChange={handleUpload}
                />
            </label>

            {/* Result banner */}
            {result && (
                <div className={`flex gap-2 text-sm rounded-lg px-4 py-3 border ${
                    result.ok
                        ? "bg-green-500/10 text-green-400 border-green-500/20"
                        : "bg-red-500/10 text-red-400 border-red-500/20"
                }`}>
                    {result.ok
                        ? <CheckCircle2 className="w-4 h-4 mt-0.5 shrink-0" />
                        : <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
                    }
                    <span>{result.message}</span>
                </div>
            )}

            {/* Panel de integración en el ERP */}
            {integrating && (
                <ErpImportReview
                    documentId={integrating.id}
                    fileName={integrating.file_name}
                    onClose={() => setIntegrating(null)}
                    onDone={(res) => {
                        setIntegrating(null);
                        const extra = res.skipped ? ` · ${res.skipped} omitidos` : "";
                        setResult({
                            ok: res.created > 0,
                            message: res.created > 0
                                ? `${res.created} ${res.target_label?.toLowerCase() || res.target} creados en el ERP${extra}`
                                : `No se creó ningún registro${extra}`,
                        });
                    }}
                />
            )}

            {/* Document list */}
            <div className="space-y-2">
                <h2 className="text-sm font-medium text-muted-foreground">Archivos importados</h2>
                {loadingList ? (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground py-4">
                        <Loader2 className="w-4 h-4 animate-spin" /> Cargando...
                    </div>
                ) : documents.length === 0 ? (
                    <p className="text-sm text-muted-foreground py-4">No hay archivos Excel importados todavía.</p>
                ) : (
                    <div className="divide-y divide-border border border-border rounded-lg overflow-hidden">
                        {documents.map(doc => (
                            <div key={doc.id} className="flex items-center gap-3 px-4 py-3 bg-card hover:bg-muted/30 transition-colors">
                                <FileSpreadsheet className="w-4 h-4 text-green-400 shrink-0" />
                                <span className="flex-1 text-sm text-foreground truncate">{doc.file_name}</span>
                                <span className="text-xs text-muted-foreground shrink-0">
                                    {new Date(doc.created_at).toLocaleDateString("es-ES")}
                                </span>
                                <div className="flex gap-1 shrink-0">
                                    <button
                                        onClick={() => { setIntegrating(doc); setResult(null); }}
                                        className="flex items-center gap-1 px-2 py-1 rounded text-xs text-primary hover:bg-primary/10 transition-colors"
                                        title="Crear registros en el ERP desde este archivo"
                                    >
                                        <Database className="w-3.5 h-3.5" /> Integrar en ERP
                                    </button>
                                    <button
                                        onClick={() => api.documents.download(doc.id, doc.file_name)}
                                        className="p-1.5 rounded hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
                                        title="Descargar"
                                    >
                                        <Download className="w-3.5 h-3.5" />
                                    </button>
                                    <button
                                        onClick={() => handleDelete(doc.id, doc.file_name)}
                                        className="p-1.5 rounded hover:bg-red-500/10 text-muted-foreground hover:text-red-400 transition-colors"
                                        title="Eliminar"
                                    >
                                        <Trash2 className="w-3.5 h-3.5" />
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
