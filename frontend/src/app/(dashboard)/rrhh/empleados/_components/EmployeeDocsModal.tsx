"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { Employee, EmployeeDocument } from "@/lib/api/hr";
import { X, Upload, Download, Trash2, FileText, Loader2, Paperclip } from "lucide-react";

function formatSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function fileIcon(type: string | null) {
    if (!type) return "📄";
    if (type.includes("pdf")) return "📕";
    if (type.includes("image")) return "🖼️";
    if (type.includes("word") || type.includes("docx")) return "📝";
    if (type.includes("excel") || type.includes("spreadsheet")) return "📊";
    return "📄";
}

export function EmployeeDocsModal({ employee, onClose }: { employee: Employee; onClose: () => void }) {
    const [docs, setDocs] = useState<EmployeeDocument[]>([]);
    const [loading, setLoading] = useState(true);
    const [uploading, setUploading] = useState(false);
    const [deletingId, setDeletingId] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);
    const fileRef = useRef<HTMLInputElement>(null);

    const load = useCallback(async () => {
        try {
            setDocs(await api.hr.employees.documents.list(employee.id));
        } catch { }
        setLoading(false);
    }, [employee.id]);

    useEffect(() => { load(); }, [load]);

    const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;
        setUploading(true); setError(null);
        try {
            const doc = await api.hr.employees.documents.upload(employee.id, file);
            setDocs(prev => [doc, ...prev]);
        } catch (err: any) { setError(err.message ?? "Error al subir"); }
        finally { setUploading(false); if (fileRef.current) fileRef.current.value = ""; }
    };

    const handleDelete = async (docId: string) => {
        setDeletingId(docId);
        try {
            await api.hr.employees.documents.delete(employee.id, docId);
            setDocs(prev => prev.filter(d => d.id !== docId));
        } catch { }
        setDeletingId(null);
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
            <div className="bg-card border border-border rounded-2xl shadow-xl w-full max-w-lg flex flex-col max-h-[80vh]">
                {/* Header */}
                <div className="flex items-center justify-between px-5 py-4 border-b border-border shrink-0">
                    <div className="flex items-center gap-2">
                        <Paperclip className="w-4 h-4 text-violet-400" />
                        <div>
                            <p className="text-sm font-semibold text-foreground">Documentos — {employee.name}</p>
                            <p className="text-xs text-muted-foreground">{docs.length} archivo{docs.length !== 1 ? "s" : ""}</p>
                        </div>
                    </div>
                    <button onClick={onClose} className="p-1 hover:bg-muted rounded-lg">
                        <X className="w-4 h-4 text-muted-foreground" />
                    </button>
                </div>

                {/* Upload */}
                <div className="px-5 py-3 border-b border-border shrink-0">
                    <input ref={fileRef} type="file" onChange={handleUpload} className="hidden" id="emp-doc-upload" />
                    <label htmlFor="emp-doc-upload"
                        className={`flex items-center justify-center gap-2 w-full py-2.5 rounded-xl border-2 border-dashed cursor-pointer transition-colors text-sm font-medium ${uploading ? "opacity-50 cursor-not-allowed border-border text-muted-foreground" : "border-violet-500/30 text-violet-400 hover:bg-violet-500/5"}`}>
                        {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
                        {uploading ? "Subiendo…" : "Adjuntar documento"}
                    </label>
                    {error && <p className="text-xs text-red-400 mt-1.5">{error}</p>}
                </div>

                {/* List */}
                <div className="overflow-y-auto flex-1 px-5 py-3 space-y-2">
                    {loading ? (
                        <div className="flex justify-center py-8"><Loader2 className="w-5 h-5 animate-spin text-muted-foreground" /></div>
                    ) : docs.length === 0 ? (
                        <div className="text-center py-8">
                            <FileText className="w-8 h-8 text-muted-foreground mx-auto mb-2" />
                            <p className="text-sm text-muted-foreground">Sin documentos adjuntos</p>
                        </div>
                    ) : docs.map(doc => (
                        <div key={doc.id} className="flex items-center gap-3 p-3 rounded-xl border border-border hover:bg-accent/50 transition-colors">
                            <span className="text-xl shrink-0">{fileIcon(doc.file_type)}</span>
                            <div className="flex-1 min-w-0">
                                <p className="text-sm text-foreground truncate">{doc.file_name}</p>
                                <p className="text-xs text-muted-foreground">
                                    {formatSize(doc.file_size)} · {doc.created_at ? new Date(doc.created_at).toLocaleDateString("es-ES") : ""}
                                </p>
                            </div>
                            <div className="flex items-center gap-1 shrink-0">
                                <button
                                    onClick={() => api.hr.employees.documents.download(employee.id, doc.id, doc.file_name)}
                                    className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                                    title="Descargar">
                                    <Download className="w-3.5 h-3.5" />
                                </button>
                                <button
                                    onClick={() => handleDelete(doc.id)}
                                    disabled={deletingId === doc.id}
                                    className="p-1.5 rounded-lg text-red-400/60 hover:text-red-400 hover:bg-red-500/10 transition-colors disabled:opacity-40"
                                    title="Eliminar">
                                    {deletingId === doc.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Trash2 className="w-3.5 h-3.5" />}
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
