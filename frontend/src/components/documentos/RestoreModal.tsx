"use client";

import { useRef, useState } from "react";
import { Upload, X, Database, CheckCircle2, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { useToastStore } from "@/stores/toast";

interface RestoreModalProps {
    onClose: () => void;
}

export default function RestoreModal({ onClose }: RestoreModalProps) {
    const [restoreFile, setRestoreFile] = useState<File | null>(null);
    const [restoring, setRestoring] = useState(false);
    const restoreFileRef = useRef<HTMLInputElement>(null);
    const { show: showToast } = useToastStore();

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: "rgba(0,0,0,0.7)", backdropFilter: "blur(6px)" }}>
            <div className="bg-[#111113] border border-[#27272a] rounded-2xl p-6 w-full max-w-md shadow-2xl">
                <div className="flex items-center justify-between mb-5">
                    <div className="flex items-center gap-3">
                        <div className="bg-red-500/10 w-10 h-10 rounded-xl flex items-center justify-center border border-red-500/20">
                            <Upload className="w-5 h-5 text-red-400" />
                        </div>
                        <div>
                            <h2 className="text-base font-semibold text-white">Restaurar Base de Datos</h2>
                            <p className="text-xs text-zinc-500">Sobreescribira todos los datos actuales</p>
                        </div>
                    </div>
                    <button onClick={onClose} className="text-zinc-500 hover:text-white transition">
                        <X className="w-5 h-5" />
                    </button>
                </div>

                <div className="bg-red-500/5 border border-red-500/20 rounded-xl px-4 py-3 mb-5 text-xs text-red-300">
                    Esta operacion es irreversible. Asegurate de tener un backup reciente antes de continuar.
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
                        onClick={onClose}
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
                                onClose();
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
    );
}
