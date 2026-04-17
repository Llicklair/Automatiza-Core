"use client";

import {
    FileText, Loader2, AlertTriangle, FileImage, Upload, Download,
    Grid2x2, List, Database, Sheet, Mail, User, ChevronLeft,
} from "lucide-react";
import UploadModal from "@/components/documentos/UploadModal";
import ImportDbModal from "@/components/documentos/ImportDbModal";
import RestoreModal from "@/components/documentos/RestoreModal";
import DocRow from "@/components/documentos/DocRow";
import DocCard from "@/components/documentos/DocCard";
import RagChatBox from "@/components/documentos/RagChatBox";
import { useDocumentos } from "./_hooks/useDocumentos";

const FOLDERS = [
    { id: "facturas",        label: "Facturas",        desc: "Ventas y Compras",            icon: FileText,     color: "text-primary",            bg: "bg-primary/10",     border: "hover:border-primary/20" },
    { id: "bancos",          label: "Bancos",           desc: "Extractos y movimientos",     icon: Grid2x2,      color: "text-blue-400",           bg: "bg-blue-500/10",    border: "hover:border-blue-500/40" },
    { id: "nominas",         label: "Nóminas",          desc: "Recibos de salario",          icon: User,         color: "text-emerald-400",        bg: "bg-emerald-500/10", border: "hover:border-emerald-500/40" },
    { id: "fiscal",          label: "Asesor Fiscal",    desc: "Impuestos y alertas",         icon: AlertTriangle,color: "text-amber-400",          bg: "bg-amber-500/10",   border: "hover:border-amber-500/40" },
    { id: "crm",             label: "CRM",              desc: "Ventas y Oportunidades",      icon: FileText,     color: "text-rose-400",           bg: "bg-rose-500/10",    border: "hover:border-rose-500/40" },
    { id: "excels",          label: "Excels",           desc: "Hojas de cálculo y datos",    icon: Sheet,        color: "text-green-400",          bg: "bg-green-500/10",   border: "hover:border-green-500/40" },
    { id: "informes",        label: "Informes",         desc: "Análisis y rentabilidad",     icon: Sheet,        color: "text-purple-400",         bg: "bg-purple-500/10",  border: "hover:border-purple-500/40" },
    { id: "correos",         label: "Correos",          desc: "Resúmenes de email",          icon: Mail,         color: "text-sky-400",            bg: "bg-sky-500/10",     border: "hover:border-sky-500/40" },
    { id: "automatizaciones",label: "Automatización",   desc: "Reglas y Workflows",          icon: Loader2,      color: "text-orange-400",         bg: "bg-orange-500/10",  border: "hover:border-orange-500/40" },
    { id: "rrhh",            label: "RRHH",             desc: "Contratos y Personal",        icon: User,         color: "text-muted-foreground",   bg: "bg-muted",          border: "hover:border-border" },
    { id: "otros",           label: "Otros",            desc: "Documentos varios",           icon: FileImage,    color: "text-muted-foreground",   bg: "bg-muted",          border: "hover:border-border" },
];

export default function DocumentosPage() {
    const {
        docs, loading, error, activeFolder, setActiveFolder, viewMode, setViewMode,
        uploadModalOpen, setUploadModalOpen, uploading, dragOver, setDragOver,
        uploadSuccess, uploadCategory, setUploadCategory,
        importModalOpen, setImportModalOpen, importing, importResults, importFiles, setImportFiles,
        pageDragOver, setPageDragOver,
        exportingDocs, backingUp, restoreModalOpen, setRestoreModalOpen,
        loadFolder, handleUpload, handleImportDB, handleExportDocs, handleBackup,
    } = useDocumentos();

    const activeInfo = FOLDERS.find(f => f.id === activeFolder);

    return (
        <div
            className="p-8 max-w-5xl mx-auto space-y-8 relative"
            onDragOver={e => { e.preventDefault(); setPageDragOver(true); }}
            onDragLeave={e => { if (e.currentTarget === e.target || !e.currentTarget.contains(e.relatedTarget as Node)) setPageDragOver(false); }}
            onDrop={e => { e.preventDefault(); setPageDragOver(false); handleUpload(e.dataTransfer.files); }}
        >
            {pageDragOver && (
                <div className="fixed inset-0 z-40 bg-primary/5 backdrop-blur-[2px] flex items-center justify-center pointer-events-none">
                    <div className="border-2 border-dashed border-primary rounded-2xl px-12 py-10 bg-card/90 shadow-2xl flex flex-col items-center gap-3">
                        <Upload className="w-10 h-10 text-primary" />
                        <p className="text-lg font-semibold text-foreground">Suelta aquí para subir</p>
                        <p className="text-sm text-muted-foreground">Los archivos se subirán a la carpeta &quot;{uploadCategory}&quot;</p>
                    </div>
                </div>
            )}

            {/* Header */}
            <div>
                {activeFolder && (
                    <div className="flex items-center gap-3 mb-1">
                        <button onClick={() => setActiveFolder(null)}
                            className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition font-medium">
                            <ChevronLeft className="w-4 h-4" /> Documentos
                        </button>
                        <span className="text-muted-foreground">/</span>
                        {activeInfo && <span className={`text-sm font-medium ${activeInfo.color}`}>{activeInfo.label}</span>}
                    </div>
                )}
                <h1 className="text-2xl font-bold text-foreground">
                    {activeFolder && activeInfo ? activeInfo.label : "Documentos"}
                </h1>
                <p className="text-sm text-muted-foreground mt-1">
                    {activeFolder
                        ? `Archivos clasificados en la carpeta ${activeInfo?.label ?? activeFolder}`
                        : "Selecciona una carpeta para ver los documentos clasificados"}
                </p>
            </div>

            {/* Toolbar */}
            <div className="flex justify-end gap-3">
                {activeFolder && (
                    <div className="flex bg-card border border-border rounded-xl p-1">
                        <button onClick={() => setViewMode("list")}
                            className={`p-1.5 rounded-lg transition-colors ${viewMode === "list" ? "bg-muted text-foreground" : "text-muted-foreground hover:text-foreground"}`}>
                            <List className="w-4 h-4" />
                        </button>
                        <button onClick={() => setViewMode("grid")}
                            className={`p-1.5 rounded-lg transition-colors ${viewMode === "grid" ? "bg-muted text-foreground" : "text-muted-foreground hover:text-foreground"}`}>
                            <Grid2x2 className="w-4 h-4" />
                        </button>
                    </div>
                )}
                <button onClick={() => { setImportModalOpen(true); }}
                    className="inline-flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-foreground px-5 py-2.5 rounded-xl transition-all shadow-lg shadow-emerald-500/20 font-medium">
                    <Database className="w-4 h-4" /> Importar BD
                </button>
                <button onClick={handleExportDocs} disabled={exportingDocs}
                    className="inline-flex items-center gap-2 bg-primary hover:bg-primary disabled:opacity-50 disabled:cursor-not-allowed text-foreground px-5 py-2.5 rounded-xl transition-all shadow-lg shadow-primary/20 font-medium">
                    {exportingDocs ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />} Exportar Docs
                </button>
                <button onClick={handleBackup} disabled={backingUp}
                    className="inline-flex items-center gap-2 bg-amber-600 hover:bg-amber-500 disabled:opacity-50 disabled:cursor-not-allowed text-foreground px-5 py-2.5 rounded-xl transition-all shadow-lg shadow-amber-500/20 font-medium">
                    {backingUp ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />} Backup BD
                </button>
                <button onClick={() => setRestoreModalOpen(true)}
                    className="inline-flex items-center gap-2 bg-accent hover:bg-accent text-foreground px-5 py-2.5 rounded-xl transition-all shadow-lg font-medium border border-border">
                    <Upload className="w-4 h-4" /> Restaurar BD
                </button>
                <button onClick={() => setUploadModalOpen(true)}
                    className="inline-flex items-center gap-2 bg-primary hover:bg-primary text-foreground px-5 py-2.5 rounded-xl transition-all shadow-lg shadow-primary/20 font-medium">
                    <Upload className="w-4 h-4" /> Subir Archivos
                </button>
            </div>

            <RagChatBox />

            {error && (
                <div className="rounded-lg border border-red-500/20 bg-red-500/5 px-4 py-3 text-sm text-red-400 flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 flex-shrink-0" /> {error}
                </div>
            )}

            {!activeFolder ? (
                <div>
                    <h2 className="text-lg font-semibold text-foreground mb-4">Carpetas</h2>
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                        {FOLDERS.map(folder => (
                            <div key={folder.id} onClick={() => setActiveFolder(folder.id)}
                                className={`bg-card border border-border ${folder.border} rounded-2xl p-6 cursor-pointer transition-all flex items-start gap-4 group hover:bg-card`}>
                                <div className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 ${folder.bg}`}>
                                    <folder.icon className={`w-6 h-6 ${folder.color}`} />
                                </div>
                                <div>
                                    <h3 className={`text-base font-semibold text-foreground group-hover:${folder.color} transition-colors`}>{folder.label}</h3>
                                    <p className="text-sm text-muted-foreground mt-0.5">{folder.desc}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            ) : (
                <div>
                    {loading ? (
                        <div className="py-16 text-center text-muted-foreground text-sm flex items-center justify-center gap-2">
                            <Loader2 className="w-4 h-4 animate-spin" /> Cargando...
                        </div>
                    ) : docs.length === 0 ? (
                        <div className="rounded-xl border border-border bg-card flex flex-col items-center justify-center py-16 text-center">
                            <FileText className="w-10 h-10 text-muted-foreground mb-3" />
                            <p className="text-sm text-muted-foreground">Esta carpeta esta vacia</p>
                            <p className="text-xs text-muted-foreground mt-1">Sube archivos desde &quot;Cargar Archivos&quot; en el menu superior</p>
                        </div>
                    ) : viewMode === "list" ? (
                        <div className="rounded-xl border border-border bg-card overflow-hidden">
                            <div className="grid grid-cols-12 gap-4 px-6 py-3 border-b border-border text-xs font-medium text-muted-foreground uppercase tracking-wide">
                                <div className="col-span-5">Archivo</div>
                                <div className="col-span-2">Tamano</div>
                                <div className="col-span-2">Estado</div>
                                <div className="col-span-3">Subido</div>
                            </div>
                            <div className="divide-y divide-border">
                                {docs.map(doc => <DocRow key={doc.id} doc={doc} onReload={() => loadFolder(activeFolder)} />)}
                            </div>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                            {docs.map(doc => <DocCard key={doc.id} doc={doc} onReload={() => loadFolder(activeFolder)} />)}
                        </div>
                    )}
                </div>
            )}

            {uploadModalOpen && (
                <UploadModal
                    uploading={uploading} dragOver={dragOver} setDragOver={setDragOver}
                    uploadSuccess={uploadSuccess} uploadCategory={uploadCategory}
                    setUploadCategory={setUploadCategory} error={error}
                    onUpload={handleUpload} onClose={() => setUploadModalOpen(false)}
                />
            )}
            {importModalOpen && (
                <ImportDbModal
                    importing={importing} importResults={importResults}
                    importFiles={importFiles} setImportFiles={setImportFiles}
                    onImport={handleImportDB} onClose={() => setImportModalOpen(false)}
                />
            )}
            {restoreModalOpen && <RestoreModal onClose={() => setRestoreModalOpen(false)} />}
        </div>
    );
}
