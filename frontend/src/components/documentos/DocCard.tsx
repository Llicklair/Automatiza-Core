"use client";

import { useState } from "react";
import { FileText, Loader2, X, Download, Trash2 } from "lucide-react";
import { api, type Document as DocType } from "@/lib/api";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";
import { fileIcon, formatSize, STATUS_STYLE } from "./shared";

interface DocCardProps {
    doc: DocType;
    onReload: () => void;
}

export default function DocCard({ doc, onReload }: DocCardProps) {
    const toast = useToastStore();
    const [open, setOpen] = useState(false);
    const [pdfOpen, setPdfOpen] = useState(false);
    const [pdfUrl, setPdfUrl] = useState("");
    const [cancelling, setCancelling] = useState(false);
    const Icon = fileIcon(doc.file_type);
    const st = STATUS_STYLE[doc.status] ?? STATUS_STYLE.uploaded;
    const hasParsed = Boolean(doc.parsed_content);
    const canCancel = doc.status === "processing" || doc.status === "uploaded";
    const isPdf = doc.file_type === "application/pdf" || doc.file_name?.toLowerCase().endsWith(".pdf");

    async function handleDownload(e: React.MouseEvent) {
        e.stopPropagation();
        try {
            await api.documents.download(doc.id, doc.file_name);
        } catch {
            toast.error("No se pudo descargar el archivo");
        }
    }

    async function handleCancel(e: React.MouseEvent) {
        e.stopPropagation();
        if (!await showConfirm({ message: "Cancelar el procesamiento de este documento?", confirmLabel: "Cancelar", confirmVariant: "danger" })) return;
        setCancelling(true);
        try {
            await api.documents.delete(doc.id);
            onReload();
        } finally {
            setCancelling(false);
        }
    }

    async function handleDelete(e: React.MouseEvent) {
        e.stopPropagation();
        if (!await showConfirm({ message: "Eliminar este documento? Esta accion no se puede deshacer.", confirmLabel: "Eliminar", confirmVariant: "danger" })) return;
        try {
            await api.documents.delete(doc.id);
            toast.success("Documento eliminado");
            onReload();
        } catch (err: any) {
            toast.error(err?.message || "Error al eliminar documento");
        }
    }

    return (
        <>
            <div
                className="bg-card border border-border hover:border-indigo-500/30 rounded-2xl flex flex-col group cursor-pointer transition-all hover:bg-muted"
                onClick={async () => {
                    if (isPdf) {
                        try {
                            const blob = await api.documents.previewBlob(doc.id);
                            setPdfUrl(URL.createObjectURL(blob));
                            setPdfOpen(true);
                        } catch {
                            toast.error("No se pudo previsualizar el PDF");
                        }
                    } else if (hasParsed) {
                        setOpen(true);
                    }
                }}
            >
                {/* Header / Preview */}
                <div className="h-32 bg-card rounded-t-2xl flex items-center justify-center p-4 relative overflow-hidden border-b border-border">
                    <div className="absolute inset-0 bg-gradient-to-b from-transparent to-card opacity-50 z-0"></div>
                    <Icon className={`w-12 h-12 relative z-10 transition-transform group-hover:scale-110 ${isPdf ? "text-indigo-400" : "text-muted-foreground"}`} />

                    <div className="absolute top-3 right-3 z-20 flex flex-col gap-2">
                        <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${st.color} shadow-sm backdrop-blur-md`}>
                            {doc.status === "processing" && <Loader2 className="w-3 h-3 inline-block mr-1 animate-spin" />}
                            {st.label}
                        </span>
                    </div>
                </div>

                {/* Info */}
                <div className="p-4 flex-1 flex flex-col">
                    <h4 className="text-sm font-semibold text-foreground truncate mb-1" title={doc.file_name}>{doc.file_name}</h4>
                    <div className="flex items-center justify-between text-xs text-muted-foreground mt-auto">
                        <span>{formatSize(doc.file_size)}</span>
                        <span>{new Date(doc.created_at).toLocaleDateString("es-ES", { day: "2-digit", month: "short" })}</span>
                    </div>
                </div>

                {/* Footer / Actions */}
                <div className="px-4 py-3 border-t border-border flex justify-between items-center opacity-70 group-hover:opacity-100 transition-opacity bg-white/[0.01]">
                    <div className="text-[10px] text-muted-foreground font-mono truncate mr-2">
                        {doc.id.substring(0, 8)}...
                    </div>
                    <div className="flex gap-1">
                        {canCancel && (
                            <button
                                onClick={handleCancel}
                                disabled={cancelling}
                                title="Cancelar"
                                className="p-1.5 rounded-md hover:bg-red-500/10 text-muted-foreground hover:text-red-400 transition"
                            >
                                {cancelling ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <X className="w-3.5 h-3.5" />}
                            </button>
                        )}
                        <button
                            onClick={handleDownload}
                            title="Descargar"
                            className="p-1.5 rounded-md hover:bg-indigo-500/10 text-muted-foreground hover:text-indigo-400 transition"
                        >
                            <Download className="w-3.5 h-3.5" />
                        </button>
                        <button
                            onClick={handleDelete}
                            title="Eliminar documento"
                            className="p-1.5 rounded-md hover:bg-red-500/10 text-muted-foreground hover:text-red-400 transition"
                        >
                            <Trash2 className="w-3.5 h-3.5" />
                        </button>
                    </div>
                </div>
            </div>

            {/* Modal for parsed content */}
            {open && hasParsed && !isPdf && (
                <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={() => setOpen(false)}>
                    <div className="bg-card border border-border rounded-2xl w-full max-w-2xl max-h-[80vh] flex flex-col shadow-2xl" onClick={e => e.stopPropagation()}>
                        <div className="px-6 py-4 border-b border-border flex justify-between items-center">
                            <h3 className="font-semibold text-foreground flex items-center gap-2"><FileText className="w-5 h-5 text-indigo-400" /> {doc.file_name}</h3>
                            <button onClick={() => setOpen(false)} className="text-muted-foreground hover:text-foreground transition"><X className="w-5 h-5" /></button>
                        </div>
                        <div className="p-6 overflow-auto">
                            <pre className="text-xs text-foreground font-mono whitespace-pre-wrap">{doc.parsed_content}</pre>
                        </div>
                        <div className="px-6 py-4 border-t border-border bg-card flex justify-end">
                            <button
                                onClick={handleDownload}
                                className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-foreground px-4 py-2 rounded-lg text-sm transition"
                            >
                                <Download className="w-4 h-4" /> Descargar Archivo Fisico
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Modal for PDF preview */}
            {pdfOpen && pdfUrl && (
                <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={() => { setPdfOpen(false); URL.revokeObjectURL(pdfUrl); setPdfUrl(""); }}>
                    <div className="bg-card border border-border rounded-2xl w-full max-w-4xl h-[85vh] flex flex-col shadow-2xl" onClick={e => e.stopPropagation()}>
                        <div className="px-6 py-4 border-b border-border flex justify-between items-center">
                            <h3 className="font-semibold text-foreground flex items-center gap-2"><FileText className="w-5 h-5 text-indigo-400" /> {doc.file_name}</h3>
                            <button onClick={() => { setPdfOpen(false); URL.revokeObjectURL(pdfUrl); setPdfUrl(""); }} className="text-muted-foreground hover:text-foreground transition"><X className="w-5 h-5" /></button>
                        </div>
                        <div className="flex-1 overflow-hidden">
                            <iframe src={pdfUrl} className="w-full h-full border-0" title={doc.file_name} />
                        </div>
                        <div className="px-6 py-3 border-t border-border bg-card flex justify-end">
                            <button
                                onClick={handleDownload}
                                className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-foreground px-4 py-2 rounded-lg text-sm transition"
                            >
                                <Download className="w-4 h-4" /> Descargar
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}
