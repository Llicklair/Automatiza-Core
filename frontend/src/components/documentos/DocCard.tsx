"use client";

import { useState } from "react";
import { FileText, Loader2, X, Download, Trash2 } from "lucide-react";
import { api, type Document as DocType } from "@/lib/api";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";
import { fileIcon, formatSize, STATUS_STYLE, API_URL } from "./shared";

interface DocCardProps {
    doc: DocType;
    onReload: () => void;
}

export default function DocCard({ doc, onReload }: DocCardProps) {
    const toast = useToastStore();
    const [open, setOpen] = useState(false);
    const [cancelling, setCancelling] = useState(false);
    const Icon = fileIcon(doc.file_type);
    const st = STATUS_STYLE[doc.status] ?? STATUS_STYLE.uploaded;
    const hasParsed = Boolean(doc.parsed_content);
    const canCancel = doc.status === "processing" || doc.status === "uploaded";
    const isPdf = doc.file_type === "application/pdf" || doc.file_name?.toLowerCase().endsWith(".pdf");

    async function handleDownload(e: React.MouseEvent) {
        e.stopPropagation();
        try {
            const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : "";
            const res = await fetch(`${API_URL}/api/v1/documents/${doc.id}/download`, {
                headers: { Authorization: `Bearer ${token}` },
            });
            if (!res.ok) throw new Error("Error descargando");
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = doc.file_name;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        } catch (e) {
            toast.error("No se pudo descargar el archivo");
        }
    }

    async function handleCancel(e: React.MouseEvent) {
        e.stopPropagation();
        if (!await showConfirm({ message: "Cancelar el procesamiento de este documento?", confirmLabel: "Cancelar", confirmVariant: "danger" })) return;
        setCancelling(true);
        try {
            const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : "";
            await fetch(`${API_URL}/api/v1/documents/${doc.id}`, {
                method: "DELETE",
                headers: { Authorization: `Bearer ${token}` },
            });
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
                className="bg-[#111113] border border-[#27272a] hover:border-indigo-500/30 rounded-2xl flex flex-col group cursor-pointer transition-all hover:bg-[#151518]"
                onClick={() => { if (hasParsed && !isPdf) setOpen(true); }}
            >
                {/* Header / Preview */}
                <div className="h-32 bg-zinc-900/50 rounded-t-2xl flex items-center justify-center p-4 relative overflow-hidden border-b border-[#27272a]">
                    <div className="absolute inset-0 bg-gradient-to-b from-transparent to-[#111113] opacity-50 z-0"></div>
                    <Icon className={`w-12 h-12 relative z-10 transition-transform group-hover:scale-110 ${isPdf ? "text-indigo-400" : "text-zinc-600"}`} />

                    <div className="absolute top-3 right-3 z-20 flex flex-col gap-2">
                        <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${st.color} shadow-sm backdrop-blur-md`}>
                            {doc.status === "processing" && <Loader2 className="w-3 h-3 inline-block mr-1 animate-spin" />}
                            {st.label}
                        </span>
                    </div>
                </div>

                {/* Info */}
                <div className="p-4 flex-1 flex flex-col">
                    <h4 className="text-sm font-semibold text-white truncate mb-1" title={doc.file_name}>{doc.file_name}</h4>
                    <div className="flex items-center justify-between text-xs text-zinc-500 mt-auto">
                        <span>{formatSize(doc.file_size)}</span>
                        <span>{new Date(doc.created_at).toLocaleDateString("es-ES", { day: "2-digit", month: "short" })}</span>
                    </div>
                </div>

                {/* Footer / Actions */}
                <div className="px-4 py-3 border-t border-[#27272a] flex justify-between items-center opacity-70 group-hover:opacity-100 transition-opacity bg-white/[0.01]">
                    <div className="text-[10px] text-zinc-600 font-mono truncate mr-2">
                        {doc.id.substring(0, 8)}...
                    </div>
                    <div className="flex gap-1">
                        {canCancel && (
                            <button
                                onClick={handleCancel}
                                disabled={cancelling}
                                title="Cancelar"
                                className="p-1.5 rounded-md hover:bg-red-500/10 text-zinc-400 hover:text-red-400 transition"
                            >
                                {cancelling ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <X className="w-3.5 h-3.5" />}
                            </button>
                        )}
                        <button
                            onClick={handleDownload}
                            title="Descargar"
                            className="p-1.5 rounded-md hover:bg-indigo-500/10 text-zinc-400 hover:text-indigo-400 transition"
                        >
                            <Download className="w-3.5 h-3.5" />
                        </button>
                        <button
                            onClick={handleDelete}
                            title="Eliminar documento"
                            className="p-1.5 rounded-md hover:bg-red-500/10 text-zinc-400 hover:text-red-400 transition"
                        >
                            <Trash2 className="w-3.5 h-3.5" />
                        </button>
                    </div>
                </div>
            </div>

            {/* Modal for parsed content */}
            {open && hasParsed && !isPdf && (
                <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={() => setOpen(false)}>
                    <div className="bg-[#111113] border border-[#27272a] rounded-2xl w-full max-w-2xl max-h-[80vh] flex flex-col shadow-2xl" onClick={e => e.stopPropagation()}>
                        <div className="px-6 py-4 border-b border-[#27272a] flex justify-between items-center">
                            <h3 className="font-semibold text-white flex items-center gap-2"><FileText className="w-5 h-5 text-indigo-400" /> {doc.file_name}</h3>
                            <button onClick={() => setOpen(false)} className="text-zinc-400 hover:text-white transition"><X className="w-5 h-5" /></button>
                        </div>
                        <div className="p-6 overflow-auto">
                            <pre className="text-xs text-zinc-300 font-mono whitespace-pre-wrap">{doc.parsed_content}</pre>
                        </div>
                        <div className="px-6 py-4 border-t border-[#27272a] bg-zinc-900/30 flex justify-end">
                            <button
                                onClick={handleDownload}
                                className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg text-sm transition"
                            >
                                <Download className="w-4 h-4" /> Descargar Archivo Fisico
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}
