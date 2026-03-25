"use client";

import { useEffect, useState, useCallback } from "react";
import { api, type Document as DocType } from "@/lib/api";
import {
    FileText, Loader2, CheckCircle2, AlertTriangle,
    FileImage, Upload, Download, Grid2x2, List, Database,
    Sheet, Mail, User, ChevronLeft,
} from "lucide-react";
import { useToastStore } from "@/stores/toast";
import type { ImportResult } from "@/components/documentos/ImportDbModal";

import UploadModal from "@/components/documentos/UploadModal";
import ImportDbModal from "@/components/documentos/ImportDbModal";
import RestoreModal from "@/components/documentos/RestoreModal";
import DocRow from "@/components/documentos/DocRow";
import DocCard from "@/components/documentos/DocCard";
import RagChatBox from "@/components/documentos/RagChatBox";

const FOLDERS = [
    { id: "facturas", label: "Facturas", desc: "Ventas y Compras", icon: FileText, color: "text-indigo-400", bg: "bg-indigo-500/10", border: "hover:border-indigo-500/40" },
    { id: "bancos", label: "Bancos", desc: "Extractos y movimientos", icon: Grid2x2, color: "text-blue-400", bg: "bg-blue-500/10", border: "hover:border-blue-500/40" },
    { id: "nominas", label: "Nóminas", desc: "Recibos de salario", icon: User, color: "text-emerald-400", bg: "bg-emerald-500/10", border: "hover:border-emerald-500/40" },
    { id: "fiscal", label: "Asesor Fiscal", desc: "Impuestos y alertas", icon: AlertTriangle, color: "text-amber-400", bg: "bg-amber-500/10", border: "hover:border-amber-500/40" },
    { id: "crm", label: "CRM", desc: "Ventas y Oportunidades", icon: CheckCircle2, color: "text-rose-400", bg: "bg-rose-500/10", border: "hover:border-rose-500/40" },
    { id: "excels", label: "Excels", desc: "Hojas de cálculo y datos", icon: Sheet, color: "text-green-400", bg: "bg-green-500/10", border: "hover:border-green-500/40" },
    { id: "informes", label: "Informes", desc: "Análisis y rentabilidad", icon: Sheet, color: "text-purple-400", bg: "bg-purple-500/10", border: "hover:border-purple-500/40" },
    { id: "correos", label: "Correos", desc: "Resúmenes de email", icon: Mail, color: "text-sky-400", bg: "bg-sky-500/10", border: "hover:border-sky-500/40" },
    { id: "automatizaciones", label: "Automatización", desc: "Reglas y Workflows", icon: Loader2, color: "text-orange-400", bg: "bg-orange-500/10", border: "hover:border-orange-500/40" },
    { id: "rrhh", label: "RRHH", desc: "Contratos y Personal", icon: User, color: "text-zinc-400", bg: "bg-zinc-500/10", border: "hover:border-zinc-500/40" },
    { id: "otros", label: "Otros", desc: "Documentos varios", icon: FileImage, color: "text-zinc-500", bg: "bg-zinc-500/5", border: "hover:border-zinc-500/20" },
];

export default function DocumentosPage() {
    const [docs, setDocs] = useState<DocType[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [activeFolder, setActiveFolder] = useState<string | null>(null);
    const [viewMode, setViewMode] = useState<"list" | "grid">("grid");

    // Upload Modal State
    const [uploadModalOpen, setUploadModalOpen] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [dragOver, setDragOver] = useState(false);
    const [uploadSuccess, setUploadSuccess] = useState("");
    const [uploadCategory, setUploadCategory] = useState("otros");

    // Import DB Modal State
    const [importModalOpen, setImportModalOpen] = useState(false);
    const [importing, setImporting] = useState(false);
    const [importResults, setImportResults] = useState<ImportResult[]>([]);
    const [importFiles, setImportFiles] = useState<File[]>([]);

    // Export & Backup State
    const [exportingDocs, setExportingDocs] = useState(false);
    const [backingUp, setBackingUp] = useState(false);
    const [restoreModalOpen, setRestoreModalOpen] = useState(false);
    const { show: showToast } = useToastStore();

    const loadFolder = useCallback((folderId: string) => {
        setLoading(true);
        setError("");
        api.documents.list({ category: folderId })
            .then(setDocs)
            .catch(() => setError("Error al cargar documentos"))
            .finally(() => setLoading(false));
    }, []);

    useEffect(() => {
        if (activeFolder) {
            loadFolder(activeFolder);
        }
    }, [loadFolder, activeFolder]);

    async function handleUpload(files: FileList | null) {
        if (!files || files.length === 0) return;
        setUploading(true);
        setError("");
        setUploadSuccess("");

        try {
            let count = 0;
            for (let i = 0; i < files.length; i++) {
                const file = files[i];
                if (file.name.toLowerCase().endsWith(".zip")) {
                    const extracted = await api.documents.uploadBulk(file, uploadCategory);
                    count += extracted.length;
                } else {
                    await api.documents.upload(file, uploadCategory);
                    count += 1;
                }
            }
            setUploadSuccess(`¡Se han subido y puesto en cola ${count} documento(s)!`);
            if (activeFolder === uploadCategory) {
                loadFolder(activeFolder);
            }
            setTimeout(() => {
                setUploadModalOpen(false);
                setUploadSuccess("");
            }, 2000);
        } catch (e: any) {
            setError(e.message || "Error al subir archivos");
        } finally {
            setUploading(false);
        }
    }

    async function handleImportDB() {
        if (importFiles.length === 0) return;
        setImporting(true);
        setError("");
        setImportResults([]);
        try {
            const res = await api.documents.importDB(importFiles);
            setImportResults(res);
            setImportFiles([]);
        } catch (e: any) {
            setError(e.message || "Error al importar base de datos");
        } finally {
            setImporting(false);
        }
    }

    const activeInfo = FOLDERS.find(f => f.id === activeFolder);

    return (
        <div className="p-8 max-w-5xl mx-auto space-y-8">
            {/* Header */}
            <div>
                {activeFolder ? (
                    <div className="flex items-center gap-3 mb-1">
                        <button
                            onClick={() => setActiveFolder(null)}
                            className="flex items-center gap-1.5 text-sm text-zinc-400 hover:text-white transition font-medium"
                        >
                            <ChevronLeft className="w-4 h-4" />
                            Documentos
                        </button>
                        <span className="text-zinc-700">/</span>
                        {activeInfo && (
                            <span className={`text-sm font-medium ${activeInfo.color}`}>
                                {activeInfo.label}
                            </span>
                        )}
                    </div>
                ) : null}
                <h1 className="text-2xl font-bold text-white">
                    {activeFolder && activeInfo ? activeInfo.label : "Documentos"}
                </h1>
                <p className="text-sm text-zinc-400 mt-1">
                    {activeFolder
                        ? `Archivos clasificados en la carpeta ${activeInfo?.label ?? activeFolder}`
                        : "Selecciona una carpeta para ver los documentos clasificados"}
                </p>
            </div>

            {/* Toolbar */}
            <div className="flex justify-end gap-3">
                {activeFolder && (
                    <div className="flex bg-[#111113] border border-[#27272a] rounded-xl p-1">
                        <button
                            onClick={() => setViewMode("list")}
                            className={`p-1.5 rounded-lg transition-colors ${viewMode === "list" ? "bg-zinc-800 text-white" : "text-zinc-500 hover:text-zinc-300"}`}
                        >
                            <List className="w-4 h-4" />
                        </button>
                        <button
                            onClick={() => setViewMode("grid")}
                            className={`p-1.5 rounded-lg transition-colors ${viewMode === "grid" ? "bg-zinc-800 text-white" : "text-zinc-500 hover:text-zinc-300"}`}
                        >
                            <Grid2x2 className="w-4 h-4" />
                        </button>
                    </div>
                )}
                <button
                    onClick={() => { setImportModalOpen(true); setImportResults([]); setImportFiles([]); }}
                    className="inline-flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-white px-5 py-2.5 rounded-xl transition-all shadow-lg shadow-emerald-500/20 font-medium"
                >
                    <Database className="w-4 h-4" />
                    Importar BD
                </button>

                <button
                    onClick={async () => {
                        setExportingDocs(true);
                        try {
                            await api.documents.exportZip();
                            showToast("Documentos exportados correctamente", "success");
                        } catch {
                            showToast("Error al exportar documentos", "error");
                        } finally {
                            setExportingDocs(false);
                        }
                    }}
                    disabled={exportingDocs}
                    className="inline-flex items-center gap-2 bg-indigo-700 hover:bg-indigo-600 disabled:opacity-50 disabled:cursor-not-allowed text-white px-5 py-2.5 rounded-xl transition-all shadow-lg shadow-indigo-500/10 font-medium"
                >
                    {exportingDocs ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                    Exportar Docs
                </button>

                <button
                    onClick={async () => {
                        setBackingUp(true);
                        try {
                            await api.admin.downloadBackup();
                            showToast("Backup descargado correctamente", "success");
                        } catch {
                            showToast("Error al generar el backup", "error");
                        } finally {
                            setBackingUp(false);
                        }
                    }}
                    disabled={backingUp}
                    className="inline-flex items-center gap-2 bg-amber-600 hover:bg-amber-500 disabled:opacity-50 disabled:cursor-not-allowed text-white px-5 py-2.5 rounded-xl transition-all shadow-lg shadow-amber-500/20 font-medium"
                >
                    {backingUp ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                    Backup BD
                </button>

                <button
                    onClick={() => setRestoreModalOpen(true)}
                    className="inline-flex items-center gap-2 bg-zinc-700 hover:bg-zinc-600 text-white px-5 py-2.5 rounded-xl transition-all shadow-lg font-medium border border-white/10"
                >
                    <Upload className="w-4 h-4" />
                    Restaurar BD
                </button>

                <button
                    onClick={() => setUploadModalOpen(true)}
                    className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2.5 rounded-xl transition-all shadow-lg shadow-indigo-500/20 font-medium"
                >
                    <Upload className="w-4 h-4" />
                    Subir Archivos
                </button>
            </div>

            {/* RAG Chat */}
            <RagChatBox />

            {/* Error */}
            {error && (
                <div className="rounded-lg border border-red-500/20 bg-red-500/5 px-4 py-3 text-sm text-red-400 flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                    {error}
                </div>
            )}

            {/* Folder View */}
            {!activeFolder ? (
                <div>
                    <h2 className="text-lg font-semibold text-white mb-4">Carpetas</h2>
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                        {FOLDERS.map(folder => (
                            <div
                                key={folder.id}
                                onClick={() => setActiveFolder(folder.id)}
                                className={`bg-[#111113] border border-[#27272a] ${folder.border} rounded-2xl p-6 cursor-pointer transition-all flex items-start gap-4 group hover:bg-[#18181b]`}
                            >
                                <div className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 ${folder.bg}`}>
                                    <folder.icon className={`w-6 h-6 ${folder.color}`} />
                                </div>
                                <div>
                                    <h3 className={`text-base font-semibold text-white group-hover:${folder.color} transition-colors`}>{folder.label}</h3>
                                    <p className="text-sm text-zinc-500 mt-0.5">{folder.desc}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            ) : (
                /* File List inside Folder */
                <div>
                    {loading ? (
                        <div className="py-16 text-center text-zinc-500 text-sm flex items-center justify-center gap-2">
                            <Loader2 className="w-4 h-4 animate-spin" /> Cargando...
                        </div>
                    ) : docs.length === 0 ? (
                        <div className="rounded-xl border border-[#27272a] bg-[#111113] flex flex-col items-center justify-center py-16 text-center">
                            <FileText className="w-10 h-10 text-zinc-700 mb-3" />
                            <p className="text-sm text-zinc-400">Esta carpeta esta vacia</p>
                            <p className="text-xs text-zinc-600 mt-1">Sube archivos desde &quot;Cargar Archivos&quot; en el menu superior</p>
                        </div>
                    ) : (
                        viewMode === "list" ? (
                            <div className="rounded-xl border border-[#27272a] bg-[#111113] overflow-hidden">
                                <div className="grid grid-cols-12 gap-4 px-6 py-3 border-b border-[#27272a] text-xs font-medium text-zinc-500 uppercase tracking-wide">
                                    <div className="col-span-5">Archivo</div>
                                    <div className="col-span-2">Tamano</div>
                                    <div className="col-span-2">Estado</div>
                                    <div className="col-span-3">Subido</div>
                                </div>
                                <div className="divide-y divide-[#27272a]">
                                    {docs.map(doc => <DocRow key={doc.id} doc={doc} onReload={() => loadFolder(activeFolder)} />)}
                                </div>
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                                {docs.map(doc => <DocCard key={doc.id} doc={doc} onReload={() => loadFolder(activeFolder)} />)}
                            </div>
                        )
                    )}
                </div>
            )}

            {/* Modals */}
            {uploadModalOpen && (
                <UploadModal
                    uploading={uploading}
                    dragOver={dragOver}
                    setDragOver={setDragOver}
                    uploadSuccess={uploadSuccess}
                    uploadCategory={uploadCategory}
                    setUploadCategory={setUploadCategory}
                    error={error}
                    onUpload={handleUpload}
                    onClose={() => setUploadModalOpen(false)}
                />
            )}

            {importModalOpen && (
                <ImportDbModal
                    importing={importing}
                    importResults={importResults}
                    importFiles={importFiles}
                    setImportFiles={setImportFiles}
                    onImport={handleImportDB}
                    onClose={() => setImportModalOpen(false)}
                />
            )}

            {restoreModalOpen && (
                <RestoreModal onClose={() => setRestoreModalOpen(false)} />
            )}
        </div>
    );
}
