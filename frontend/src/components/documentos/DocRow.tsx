"use client";

import { useState } from "react";
import { Loader2, CheckCircle2, ChevronLeft, X, Download, Trash2 } from "lucide-react";
import { api, type Document as DocType } from "@/lib/api";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";
import { fileIcon, formatSize, STATUS_STYLE, API_URL, authHeaders } from "./shared";

interface DocRowProps {
    doc: DocType;
    onReload: () => void;
}

export default function DocRow({ doc, onReload }: DocRowProps) {
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
            await fetch(`${API_URL}/api/v1/documents/${doc.id}`, {
                method: "DELETE",
                headers: authHeaders(),
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
        <div className="hover:bg-white/[0.02] transition">
            <div
                className={`grid grid-cols-12 gap-4 px-6 py-3.5 items-center ${hasParsed && !isPdf ? "cursor-pointer" : ""}`}
                onClick={() => {
                    if (hasParsed && !isPdf) setOpen(!open);
                }}
            >
                <div className="col-span-5 flex items-center gap-3 min-w-0">
                    <Icon className={`w-5 h-5 flex-shrink-0 ${isPdf ? "text-indigo-400" : "text-zinc-500"}`} />
                    <span className="text-sm text-white truncate">{doc.file_name}</span>
                </div>
                <div className="col-span-2 text-xs text-zinc-500">{formatSize(doc.file_size)}</div>
                <div className="col-span-2">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${st.color}`}>
                        {doc.status === "processing" && <Loader2 className="w-3 h-3 inline-block mr-1 animate-spin" />}
                        {(doc.status === "processed" || doc.status === "completed" || doc.status === "ready") && <CheckCircle2 className="w-3 h-3 inline-block mr-1" />}
                        {st.label}
                    </span>
                </div>
                <div className="col-span-3 flex items-center justify-between gap-2">
                    <span className="text-xs text-zinc-500">
                        {new Date(doc.created_at).toLocaleDateString("es-ES", {
                            day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit",
                        })}
                    </span>
                    <div className="flex items-center gap-2">
                        {canCancel && (
                            <button
                                onClick={handleCancel}
                                disabled={cancelling}
                                title="Cancelar procesamiento"
                                className="p-1 rounded text-zinc-600 hover:text-red-400 hover:bg-red-500/10 transition disabled:opacity-40"
                            >
                                {cancelling
                                    ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                    : <X className="w-3.5 h-3.5" />}
                            </button>
                        )}
                        <button
                            onClick={handleDownload}
                            title={isPdf ? "Descargar PDF" : "Descargar archivo"}
                            className={`p-1 rounded transition ${isPdf
                                ? "text-indigo-400 hover:text-indigo-300 hover:bg-indigo-500/10"
                                : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-700/50"
                                }`}
                        >
                            <Download className="w-3.5 h-3.5" />
                        </button>
                        <button
                            onClick={handleDelete}
                            title="Eliminar documento"
                            className="p-1 rounded text-zinc-600 hover:text-red-400 hover:bg-red-500/10 transition"
                        >
                            <Trash2 className="w-3.5 h-3.5" />
                        </button>
                        {hasParsed && !isPdf && (
                            <ChevronLeft className={`w-4 h-4 text-zinc-500 transition-transform duration-300 ${open ? "-rotate-90" : "rotate-180"}`} />
                        )}
                    </div>
                </div>
            </div>

            {hasParsed && !isPdf && (
                <div className={`grid transition-[grid-template-rows,opacity] duration-300 ease-in-out ${open ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0"}`}>
                    <div className="overflow-hidden">
                        <div className="px-6 pb-4 pt-2 border-t border-[#27272a]/50">
                            <p className="text-xs text-zinc-500 mb-2">Contenido extraido por el agente</p>
                            <pre className="px-4 py-3 rounded-lg bg-[#0d0d0f] text-xs text-zinc-300 border border-[#27272a] overflow-x-auto max-h-[300px] overflow-y-auto whitespace-pre-wrap">
                                {doc.parsed_content}
                            </pre>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
