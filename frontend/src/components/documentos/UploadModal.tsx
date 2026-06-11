"use client";

import { useRef } from "react";
import { Upload, X, FileText, CheckCircle2, AlertTriangle } from "lucide-react";

interface UploadModalProps {
    uploading: boolean;
    dragOver: boolean;
    setDragOver: (v: boolean) => void;
    uploadSuccess: string;
    uploadCategory: string;
    setUploadCategory: (v: string) => void;
    error: string;
    onUpload: (files: FileList | null) => void;
    onClose: () => void;
}

export default function UploadModal({
    uploading, dragOver, setDragOver, uploadSuccess, uploadCategory,
    setUploadCategory, error, onUpload, onClose,
}: UploadModalProps) {
    const fileInputRef = useRef<HTMLInputElement>(null);

    return (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-card border border-border rounded-2xl shadow-2xl w-full max-w-xl overflow-hidden transform transition-all flex flex-col">
                <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-card">
                    <h2 className="text-xl font-bold text-foreground flex items-center gap-2">
                        <Upload className="w-5 h-5 text-indigo-400" /> Cargar Documentos
                    </h2>
                    <button
                        onClick={onClose}
                        className="p-2 rounded-lg hover:bg-white/5 text-muted-foreground hover:text-foreground transition-colors"
                     aria-label="Cerrar">
                        <X className="w-5 h-5" aria-hidden="true" />
                    </button>
                </div>

                <div className="p-6 space-y-6">
                    <div className="bg-card border border-border p-4 rounded-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
                        <div>
                            <h3 className="text-sm font-medium text-foreground">Categoria de destino</h3>
                            <p className="text-xs text-muted-foreground mt-0.5">A que carpeta los asignamos?</p>
                        </div>
                        <select
                            value={uploadCategory}
                            onChange={(e) => setUploadCategory(e.target.value)}
                            className="bg-background border border-border text-foreground text-sm rounded-lg px-3 py-2 outline-none focus:border-primary transition-colors w-full md:w-auto"
                        >
                            <option value="facturas">Facturas</option>
                            <option value="bancos">Bancos</option>
                            <option value="nominas">Nominas</option>
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
                        onDrop={e => { e.preventDefault(); setDragOver(false); onUpload(e.dataTransfer.files); }}
                        className={`rounded-xl border-2 border-dashed p-10 text-center transition-all duration-300 cursor-pointer ${dragOver
                            ? "border-indigo-500 bg-indigo-500/10 scale-[1.02]"
                            : "border-border bg-card hover:border-muted-foreground"
                            }`}
                        onClick={() => fileInputRef.current?.click()}
                    >
                        <div className="flex justify-center mb-3">
                            <div className="w-12 h-12 rounded-full bg-indigo-500/10 flex items-center justify-center">
                                <FileText className={`w-6 h-6 transition-colors ${dragOver ? "text-indigo-400" : "text-indigo-500"}`} />
                            </div>
                        </div>
                        <h3 className="text-base font-medium text-foreground mb-1">
                            {uploading ? "Procesando subida..." : "Arrastra los archivos o haz clic"}
                        </h3>
                        <p className="text-xs text-muted-foreground max-w-xs mx-auto">
                            Formatos soportados: PDF, Imagenes, Excels, Word o importacion de lote via ZIP (max 50MB).
                        </p>
                        <input
                            ref={fileInputRef}
                            type="file"
                            className="hidden"
                            multiple
                            accept=".pdf,.png,.jpg,.jpeg,.docx,.xlsx,.csv,.txt,.zip"
                            onChange={e => onUpload(e.target.files)}
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
    );
}
