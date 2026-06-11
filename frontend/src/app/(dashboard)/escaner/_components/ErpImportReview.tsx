"use client";

import { useEffect, useState } from "react";
import { Loader2, AlertTriangle, CheckCircle2, Database, X } from "lucide-react";
import { api } from "@/lib/api";
import type { ErpImportPreview, ErpImportResult } from "@/lib/api/documents";

/**
 * Revisión + confirmación de una importación Excel/CSV → entidades del ERP.
 * Previsualiza el mapeo de columnas (sin escribir), permite elegir el destino
 * (productos / clientes / empleados) y crea los registros tras confirmar.
 */
export function ErpImportReview({
    documentId, fileName, onClose, onDone,
}: {
    documentId: string;
    fileName: string;
    onClose: () => void;
    onDone: (result: ErpImportResult) => void;
}) {
    const [preview, setPreview] = useState<ErpImportPreview | null>(null);
    const [loading, setLoading] = useState(true);
    const [importing, setImporting] = useState(false);
    const [error, setError] = useState<string | null>(null);

    async function loadPreview(target?: string) {
        setLoading(true);
        setError(null);
        try {
            setPreview(await api.documents.erpImportPreview(documentId, target));
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : "No se pudo previsualizar");
            setPreview(null);
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => { loadPreview(); /* eslint-disable-next-line */ }, [documentId]);

    async function handleImport() {
        if (!preview) return;
        setImporting(true);
        setError(null);
        try {
            const res = await api.documents.erpImportApply(documentId, preview.target);
            onDone(res);
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : "Error al importar");
        } finally {
            setImporting(false);
        }
    }

    return (
        <div className="rounded-xl border border-primary/30 bg-primary/5 p-5 space-y-4">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 min-w-0">
                    <Database className="w-4 h-4 text-primary shrink-0" />
                    <span className="text-sm font-medium text-foreground truncate">
                        Integrar «{fileName}» en el ERP
                    </span>
                </div>
                <button onClick={onClose} className="p-1 rounded hover:bg-muted text-muted-foreground" aria-label="Cerrar">
                    <X className="w-4 h-4" aria-hidden="true" />
                </button>
            </div>

            {loading ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground py-4">
                    <Loader2 className="w-4 h-4 animate-spin" /> Analizando columnas…
                </div>
            ) : error && !preview ? (
                <div className="flex items-start gap-2 text-sm text-amber-400">
                    <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" /> <span>{error}</span>
                </div>
            ) : preview ? (
                <>
                    {/* Target selector */}
                    <div>
                        <span className="text-[11px] text-muted-foreground">Crear como</span>
                        <div className="flex flex-wrap gap-2 mt-1">
                            {preview.available_targets.map(t => (
                                <button key={t.key} onClick={() => loadPreview(t.key)}
                                    className={`px-3 py-1.5 rounded-md text-sm border transition-colors ${
                                        preview.target === t.key
                                            ? "border-primary bg-primary/15 text-foreground"
                                            : "border-border text-muted-foreground hover:text-foreground"
                                    }`}>
                                    {t.label}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Resumen del mapeo */}
                    <div className="text-xs text-muted-foreground space-y-1">
                        <div>
                            <span className="text-green-400 font-medium">{preview.importable}</span> de {preview.total_rows} filas
                            importables{preview.skipped > 0 && ` · ${preview.skipped} se omitirán (sin nombre)`}.
                        </div>
                        <div>Columnas reconocidas: <span className="text-foreground">{preview.mapped_fields.join(", ") || "ninguna"}</span></div>
                        {preview.unmapped_columns.length > 0 && (
                            <div>Ignoradas: {preview.unmapped_columns.join(", ")}</div>
                        )}
                    </div>

                    {/* Muestra */}
                    {preview.sample.length > 0 && (
                        <div className="border border-border rounded-lg overflow-auto max-h-56">
                            <table className="w-full text-xs">
                                <thead className="bg-muted/40 text-muted-foreground">
                                    <tr>
                                        <th className="text-left px-2 py-1.5">#</th>
                                        {preview.mapped_fields.map(f => <th key={f} className="text-left px-2 py-1.5">{f}</th>)}
                                    </tr>
                                </thead>
                                <tbody>
                                    {preview.sample.map((s, i) => (
                                        <tr key={i} className={`border-t border-border ${s.ok ? "" : "opacity-40"}`}>
                                            <td className="px-2 py-1">{s.ok ? i + 1 : "—"}</td>
                                            {preview.mapped_fields.map(f => (
                                                <td key={f} className="px-2 py-1 text-foreground truncate max-w-[160px]">
                                                    {String(s.record[f] ?? "")}
                                                </td>
                                            ))}
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}

                    {error && (
                        <div className="flex items-start gap-2 text-sm text-amber-400">
                            <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" /> <span>{error}</span>
                        </div>
                    )}

                    <button onClick={handleImport} disabled={importing || preview.importable === 0}
                        className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-primary text-foreground font-medium hover:bg-primary/90 disabled:opacity-60 transition-colors">
                        {importing ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
                        Crear {preview.importable} {preview.target_label.toLowerCase()}
                    </button>
                </>
            ) : null}
        </div>
    );
}
