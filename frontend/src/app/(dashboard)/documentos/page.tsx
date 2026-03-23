"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { api, type Document as DocType } from "@/lib/api";
import {
    FileText, Loader2, CheckCircle2, AlertTriangle,
    FileImage, FileArchive, ChevronLeft, X, Send, Bot, User,
    Mail, Sheet, Upload, Download, Grid2x2, List, Database, Table2, FolderOpen, Trash2
} from "lucide-react";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

function authHeaders() {
    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : "";
    return { Authorization: `Bearer ${token}` };
}

const STATUS_STYLE: Record<string, { label: string; color: string }> = {
    uploaded: { label: "Subido", color: "text-blue-400 bg-blue-500/10" },
    processing: { label: "Procesando", color: "text-amber-400 bg-amber-500/10" },
    processed: { label: "Procesado", color: "text-emerald-400 bg-emerald-500/10" },
    ready: { label: "Listo", color: "text-emerald-400 bg-emerald-500/10" },
    completed: { label: "Completado", color: "text-emerald-400 bg-emerald-500/10" },
    failed: { label: "Error", color: "text-red-400 bg-red-500/10" },
};

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

function fileIcon(type: string | null) {
    if (!type) return FileText;
    if (type.startsWith("image/")) return FileImage;
    if (type.includes("zip") || type.includes("rar")) return FileArchive;
    return FileText;
}

function formatSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function DocumentosPage() {
    const [docs, setDocs] = useState<DocType[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [activeFolder, setActiveFolder] = useState<string | null>(null);
    const [viewMode, setViewMode] = useState<"list" | "grid">("grid");

    // RAG Chat State
    const [chatMessages, setChatMessages] = useState<{ role: "user" | "ai", content: string, sources?: number, sourceNames?: string[] }[]>([]);
    const [chatInput, setChatInput] = useState("");
    const [chatLoading, setChatLoading] = useState(false);

    // Upload Modal State
    const [uploadModalOpen, setUploadModalOpen] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [dragOver, setDragOver] = useState(false);
    const [uploadSuccess, setUploadSuccess] = useState("");
    const [uploadCategory, setUploadCategory] = useState("otros");
    const fileInputRef = useRef<HTMLInputElement>(null);

    // Import DB Modal State
    type ImportResult = { document_id: string; file_name: string; rows_detected: number; columns: string[]; category: string; task_id: string | null; message: string };
    const [importModalOpen, setImportModalOpen] = useState(false);
    const [importing, setImporting] = useState(false);
    const [importResults, setImportResults] = useState<ImportResult[]>([]);
    const [importFiles, setImportFiles] = useState<File[]>([]);
    const [importDragOver, setImportDragOver] = useState(false);
    const importFileRef = useRef<HTMLInputElement>(null);

    // Docs ZIP Export State
    const [exportingDocs, setExportingDocs] = useState(false);

    // Backup / Restore State
    const [backingUp, setBackingUp] = useState(false);
    const [restoreModalOpen, setRestoreModalOpen] = useState(false);
    const [restoreFile, setRestoreFile] = useState<File | null>(null);
    const [restoring, setRestoring] = useState(false);
    const restoreFileRef = useRef<HTMLInputElement>(null);
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

    function handleImportFiles(files: FileList | null) {
        if (!files) return;
        setImportFiles(prev => [...prev, ...Array.from(files)]);
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

    async function handleChat(e: React.FormEvent) {
        e.preventDefault();
        const prompt = chatInput.trim();
        if (!prompt) return;

        setChatInput("");
        setChatMessages(prev => [...prev, { role: "user", content: prompt }]);
        setChatLoading(true);

        try {
            const task = await api.tasks.create("rag", prompt);
            let current = task;

            while (current.status !== "done" && current.status !== "failed" && current.status !== "cancelled") {
                await new Promise(r => setTimeout(r, 2000));
                current = await api.tasks.get(task.id);
            }

            if (current.status === "done" && current.agent_results) {
                const ragResult = current.agent_results.find((r: any) => r.agent === "rag");
                if (ragResult?.success) {
                    setChatMessages(prev => [...prev, {
                        role: "ai",
                        content: ragResult.output.answer,
                        sources: ragResult.output.sources_used,
                        sourceNames: ragResult.output.source_names
                    }]);
                } else {
                    setChatMessages(prev => [...prev, { role: "ai", content: "No pude procesar la respuesta." }]);
                }
            } else {
                setChatMessages(prev => [...prev, { role: "ai", content: current.error_message || "La tarea falló." }]);
            }

        } catch (err: any) {
            setChatMessages(prev => [...prev, { role: "ai", content: `Error de conexión: ${err.message}` }]);
        } finally {
            setChatLoading(false);
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

                {/* Exportar Docs ZIP */}
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

                {/* Backup BD */}
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

                {/* Restaurar BD */}
                <button
                    onClick={() => { setRestoreModalOpen(true); setRestoreFile(null); }}
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

            {/* AI RAG Chat — siempre visible */}
            <div className="rounded-xl border border-[#27272a] bg-[#111113] overflow-hidden flex flex-col shadow-lg">
                <div className="px-6 py-4 border-b border-[#27272a] flex items-center gap-3">
                    <Bot className="w-5 h-5 text-indigo-400" />
                    <h2 className="text-sm font-semibold text-white">Búsqueda Universal & Consultas IA</h2>
                </div>

                <div className="p-6">
                    {chatMessages.length === 0 ? (
                        <div className="text-center py-4">
                            <p className="text-sm text-zinc-400">Encuentra cualquier archivo o pregunta detalles técnicos a tus documentos.</p>
                            <p className="text-xs text-zinc-500 mt-1">Ej: &quot;Busca la factura de Amazon&quot; o &quot;Resume el contrato de alquiler&quot;.</p>
                        </div>
                    ) : (
                        <div className="space-y-4 max-h-[280px] overflow-y-auto mb-4 pr-2">
                            {chatMessages.map((msg, idx) => (
                                <div key={idx} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                    {msg.role === 'ai' && <div className="w-8 h-8 rounded-full bg-indigo-500/20 flex items-center justify-center flex-shrink-0"><Bot className="w-4 h-4 text-indigo-400" /></div>}
                                    <div className={`px-4 py-3 rounded-2xl max-w-[80%] text-sm ${msg.role === 'user' ? 'bg-indigo-600 text-white rounded-br-none' : 'bg-[#27272a] text-zinc-200 rounded-bl-none'}`}>
                                        <div className="whitespace-pre-wrap">{msg.content}</div>
                                        {msg.sourceNames && msg.sourceNames.length > 0 && (
                                            <div className="mt-2 pt-2 border-t border-white/5 space-y-1">
                                                <p className="text-[10px] text-zinc-500 font-medium uppercase tracking-wider">Archivos relacionados:</p>
                                                {msg.sourceNames.map((name, i) => (
                                                    <div key={i} className="text-[10px] text-indigo-400 font-mono flex items-center gap-1">
                                                        <FileText className="w-3 h-3" /> {name}
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                    {msg.role === 'user' && <div className="w-8 h-8 rounded-full bg-zinc-800 flex items-center justify-center flex-shrink-0"><User className="w-4 h-4 text-zinc-400" /></div>}
                                </div>
                            ))}
                            {chatLoading && (
                                <div className="flex gap-3 justify-start">
                                    <div className="w-8 h-8 rounded-full bg-indigo-500/20 flex items-center justify-center flex-shrink-0"><Bot className="w-4 h-4 text-indigo-400" /></div>
                                    <div className="px-4 py-3 rounded-2xl bg-[#27272a] text-zinc-400 rounded-bl-none text-sm flex items-center gap-2">
                                        <Loader2 className="w-4 h-4 animate-spin" /> Consultando base de datos vectorial...
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    <form onSubmit={handleChat} className="flex gap-3">
                        <input
                            type="text"
                            value={chatInput}
                            onChange={(e) => setChatInput(e.target.value)}
                            disabled={chatLoading}
                            placeholder="Ej. ¿Qué dice el contrato sobre la rescisión anticipada?"
                            className="flex-1 bg-[#0d0d0f] border border-[#27272a] text-sm text-white rounded-xl px-4 py-3 focus:outline-none focus:border-indigo-500 transition disabled:opacity-50"
                        />
                        <button
                            type="submit"
                            disabled={chatLoading || !chatInput.trim()}
                            className="bg-indigo-600 hover:bg-indigo-500 text-white px-5 rounded-xl transition flex items-center justify-center disabled:opacity-50"
                        >
                            <Send className="w-4 h-4" />
                        </button>
                    </form>
                </div>
            </div>

            {/* Error */}
            {error && (
                <div className="rounded-lg border border-red-500/20 bg-red-500/5 px-4 py-3 text-sm text-red-400 flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                    {error}
                </div>
            )}

            {/* VISTA DE CARPETAS */}
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
                /* VISTA DE ARCHIVOS DENTRO DE CARPETA */
                <div>
                    {loading ? (
                        <div className="py-16 text-center text-zinc-500 text-sm flex items-center justify-center gap-2">
                            <Loader2 className="w-4 h-4 animate-spin" /> Cargando…
                        </div>
                    ) : docs.length === 0 ? (
                        <div className="rounded-xl border border-[#27272a] bg-[#111113] flex flex-col items-center justify-center py-16 text-center">
                            <FileText className="w-10 h-10 text-zinc-700 mb-3" />
                            <p className="text-sm text-zinc-400">Esta carpeta está vacía</p>
                            <p className="text-xs text-zinc-600 mt-1">Sube archivos desde &quot;Cargar Archivos&quot; en el menú superior</p>
                        </div>
                    ) : (
                        viewMode === "list" ? (
                            <div className="rounded-xl border border-[#27272a] bg-[#111113] overflow-hidden">
                                <div className="grid grid-cols-12 gap-4 px-6 py-3 border-b border-[#27272a] text-xs font-medium text-zinc-500 uppercase tracking-wide">
                                    <div className="col-span-5">Archivo</div>
                                    <div className="col-span-2">Tamaño</div>
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

            {/* Modal de Subida de Archivos */}
            {uploadModalOpen && (
                <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
                    <div className="bg-[#111113] border border-[#27272a] rounded-2xl shadow-2xl w-full max-w-xl overflow-hidden transform transition-all flex flex-col">
                        <div className="px-6 py-4 border-b border-[#27272a] flex items-center justify-between bg-zinc-900/50">
                            <h2 className="text-xl font-bold text-white flex items-center gap-2">
                                <Upload className="w-5 h-5 text-indigo-400" /> Cargar Documentos
                            </h2>
                            <button
                                onClick={() => setUploadModalOpen(false)}
                                className="p-2 rounded-lg hover:bg-white/5 text-zinc-400 hover:text-white transition-colors"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        <div className="p-6 space-y-6">
                            <div className="bg-zinc-900 border border-[#27272a] p-4 rounded-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
                                <div>
                                    <h3 className="text-sm font-medium text-white">Categoría de destino</h3>
                                    <p className="text-xs text-zinc-500 mt-0.5">¿A qué carpeta los asignamos?</p>
                                </div>
                                <select
                                    value={uploadCategory}
                                    onChange={(e) => setUploadCategory(e.target.value)}
                                    className="bg-[#0d0d0f] border border-[#27272a] text-white text-sm rounded-lg px-3 py-2 outline-none focus:border-indigo-500 transition-colors w-full md:w-auto"
                                >
                                    <option value="facturas">Facturas</option>
                                    <option value="bancos">Bancos</option>
                                    <option value="nominas">Nóminas</option>
                                    <option value="fiscal">Asesor Fiscal</option>
                                    <option value="crm">CRM</option>
                                    <option value="excels">Excels</option>
                                    <option value="informes">Informes</option>
                                    <option value="correos">Correos</option>
                                    <option value="automatizaciones">Automatizaciones</option>
                                    <option value="rrhh">RRHH</option>
                                    <option value="otros">Otros</option>
                                </select>
                            </div>

                            <div
                                onDragOver={e => { e.preventDefault(); setDragOver(true); }}
                                onDragLeave={() => setDragOver(false)}
                                onDrop={e => { e.preventDefault(); setDragOver(false); handleUpload(e.dataTransfer.files); }}
                                className={`rounded-xl border-2 border-dashed p-10 text-center transition-all duration-300 cursor-pointer ${dragOver
                                    ? "border-indigo-500 bg-indigo-500/10 scale-[1.02]"
                                    : "border-[#27272a] bg-zinc-900 hover:border-zinc-500"
                                    }`}
                                onClick={() => fileInputRef.current?.click()}
                            >
                                <div className="flex justify-center mb-3">
                                    <div className="w-12 h-12 rounded-full bg-indigo-500/10 flex items-center justify-center">
                                        <FileText className={`w-6 h-6 transition-colors ${dragOver ? "text-indigo-400" : "text-indigo-500"}`} />
                                    </div>
                                </div>
                                <h3 className="text-base font-medium text-white mb-1">
                                    {uploading ? "Procesando subida…" : "Arrastra los archivos o haz clic"}
                                </h3>
                                <p className="text-xs text-zinc-500 max-w-xs mx-auto">
                                    Formatos soportados: PDF, Imágenes, Excels, Word o importación de lote vía ZIP (max 50MB).
                                </p>
                                <input
                                    ref={fileInputRef}
                                    type="file"
                                    className="hidden"
                                    multiple
                                    accept=".pdf,.png,.jpg,.jpeg,.docx,.xlsx,.csv,.txt,.zip"
                                    onChange={e => handleUpload(e.target.files)}
                                />
                            </div>

                            {uploadSuccess && (
                                <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/10 p-3 text-xs text-emerald-400 flex items-center gap-2">
                                    <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                                    <span>{uploadSuccess}</span>
                                </div>
                            )}

                            {error && (
                                <div className="rounded-lg border border-red-500/20 bg-red-500/10 p-3 text-xs text-red-400 flex items-center gap-2">
                                    <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                                    <span>{error}</span>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* Modal Importar Base de Datos */}
            {importModalOpen && (
                <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
                    <div className="bg-[#111113] border border-[#27272a] rounded-2xl shadow-2xl w-full max-w-2xl overflow-hidden flex flex-col max-h-[85vh]">
                        <div className="px-6 py-4 border-b border-[#27272a] flex items-center justify-between bg-zinc-900/50">
                            <h2 className="text-xl font-bold text-white flex items-center gap-2">
                                <Database className="w-5 h-5 text-emerald-400" /> Importar Base de Datos
                            </h2>
                            <button
                                onClick={() => setImportModalOpen(false)}
                                className="p-2 rounded-lg hover:bg-white/5 text-zinc-400 hover:text-white transition-colors"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        <div className="p-6 space-y-5 overflow-y-auto">
                            <p className="text-sm text-zinc-400">
                                Sube archivos <span className="text-white font-medium">CSV, Excel (.xlsx), JSON u ODS</span>.
                                La IA analizará las columnas, detectará qué tipo de datos contienen y los diseminará
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
                                        onClick={handleImportDB}
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
                                                    {r.columns.length > 12 && <span className="text-[10px] text-zinc-600">+{r.columns.length - 12} más</span>}
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
            )}

            {/* ── Modal Restaurar BD ─────────────────────────────────────── */}
            {restoreModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: "rgba(0,0,0,0.7)", backdropFilter: "blur(6px)" }}>
                    <div className="bg-[#111113] border border-[#27272a] rounded-2xl p-6 w-full max-w-md shadow-2xl">
                        <div className="flex items-center justify-between mb-5">
                            <div className="flex items-center gap-3">
                                <div className="bg-red-500/10 w-10 h-10 rounded-xl flex items-center justify-center border border-red-500/20">
                                    <Upload className="w-5 h-5 text-red-400" />
                                </div>
                                <div>
                                    <h2 className="text-base font-semibold text-white">Restaurar Base de Datos</h2>
                                    <p className="text-xs text-zinc-500">Sobreescribirá todos los datos actuales</p>
                                </div>
                            </div>
                            <button onClick={() => setRestoreModalOpen(false)} className="text-zinc-500 hover:text-white transition">
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        <div className="bg-red-500/5 border border-red-500/20 rounded-xl px-4 py-3 mb-5 text-xs text-red-300">
                            ⚠️ Esta operación es irreversible. Asegúrate de tener un backup reciente antes de continuar.
                        </div>

                        {/* File picker */}
                        <input
                            ref={restoreFileRef}
                            type="file"
                            accept=".sql"
                            className="hidden"
                            onChange={(e) => setRestoreFile(e.target.files?.[0] ?? null)}
                        />
                        <button
                            onClick={() => restoreFileRef.current?.click()}
                            className="w-full border-2 border-dashed border-[#27272a] hover:border-zinc-600 rounded-xl py-6 flex flex-col items-center gap-2 transition mb-4"
                        >
                            {restoreFile ? (
                                <>
                                    <CheckCircle2 className="w-7 h-7 text-emerald-400" />
                                    <span className="text-sm text-white font-medium">{restoreFile.name}</span>
                                    <span className="text-xs text-zinc-500">{(restoreFile.size / 1024).toFixed(0)} KB</span>
                                </>
                            ) : (
                                <>
                                    <Database className="w-7 h-7 text-zinc-500" />
                                    <span className="text-sm text-zinc-400">Seleccionar archivo .sql</span>
                                </>
                            )}
                        </button>

                        <div className="flex gap-3">
                            <button
                                onClick={() => setRestoreModalOpen(false)}
                                className="flex-1 py-2.5 rounded-xl border border-[#27272a] text-zinc-400 hover:text-white hover:border-zinc-600 transition text-sm"
                            >
                                Cancelar
                            </button>
                            <button
                                disabled={!restoreFile || restoring}
                                onClick={async () => {
                                    if (!restoreFile) return;
                                    setRestoring(true);
                                    try {
                                        const res = await api.admin.restoreBackup(restoreFile);
                                        showToast(res.message, "success");
                                        setRestoreModalOpen(false);
                                    } catch (err) {
                                        showToast(err instanceof Error ? err.message : "Error al restaurar", "error");
                                    } finally {
                                        setRestoring(false);
                                    }
                                }}
                                className="flex-1 py-2.5 rounded-xl bg-red-600 hover:bg-red-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium flex items-center justify-center gap-2 transition"
                            >
                                {restoring ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
                                Restaurar ahora
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}


function DocRow({ doc, onReload }: { doc: DocType; onReload: () => void }) {
    const toast = useToastStore();
    const [open, setOpen] = useState(false);
    const [cancelling, setCancelling] = useState(false);
    const Icon = fileIcon(doc.file_type);
    const st = STATUS_STYLE[doc.status] ?? STATUS_STYLE.uploaded;
    const hasParsed = Boolean(doc.parsed_content);
    const canCancel = doc.status === "processing" || doc.status === "uploaded";
    const isPdf = doc.file_type === "application/pdf" || doc.file_name?.toLowerCase().endsWith(".pdf");

    const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8080";
    function authHeaders() {
        const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : "";
        return { Authorization: `Bearer ${token}` };
    }

    async function handleDownload(e: React.MouseEvent) {
        e.stopPropagation();
        try {
            const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : "";
            const res = await fetch(`${API}/api/v1/documents/${doc.id}/download`, {
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
        if (!await showConfirm({ message: "¿Cancelar el procesamiento de este documento?", confirmLabel: "Cancelar", confirmVariant: "danger" })) return;
        setCancelling(true);
        try {
            await fetch(`${API}/api/v1/documents/${doc.id}`, {
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
        if (!await showConfirm({ message: "¿Eliminar este documento? Esta acción no se puede deshacer.", confirmLabel: "Eliminar", confirmVariant: "danger" })) return;
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
                        {/* Botón de descarga para TODOS los archivos */}
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
                            <p className="text-xs text-zinc-500 mb-2">Contenido extraído por el agente</p>
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

function DocCard({ doc, onReload }: { doc: DocType; onReload: () => void }) {
    const toast = useToastStore();
    const [open, setOpen] = useState(false);
    const [cancelling, setCancelling] = useState(false);
    const Icon = fileIcon(doc.file_type);
    const st = STATUS_STYLE[doc.status] ?? STATUS_STYLE.uploaded;
    const hasParsed = Boolean(doc.parsed_content);
    const canCancel = doc.status === "processing" || doc.status === "uploaded";
    const isPdf = doc.file_type === "application/pdf" || doc.file_name?.toLowerCase().endsWith(".pdf");

    const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8080";

    async function handleDownload(e: React.MouseEvent) {
        e.stopPropagation();
        try {
            const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : "";
            const res = await fetch(`${API}/api/v1/documents/${doc.id}/download`, {
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
        if (!await showConfirm({ message: "¿Cancelar el procesamiento de este documento?", confirmLabel: "Cancelar", confirmVariant: "danger" })) return;
        setCancelling(true);
        try {
            const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : "";
            await fetch(`${API}/api/v1/documents/${doc.id}`, {
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
        if (!await showConfirm({ message: "¿Eliminar este documento? Esta acción no se puede deshacer.", confirmLabel: "Eliminar", confirmVariant: "danger" })) return;
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
                {/* Cabecera / Vista Previa Simulada */}
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

                {/* Info Card */}
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

            {/* Modal para ver contenido si aplica */}
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
                                <Download className="w-4 h-4" /> Descargar Archivo Físico
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}
