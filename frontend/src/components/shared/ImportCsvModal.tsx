"use client";
import { useRef, useState } from "react";
import { Upload, FileText, Download, AlertCircle, CheckCircle2, X } from "lucide-react";
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { csvToObjects } from "@/lib/utils/parse-csv";
import { exportToCsv } from "@/lib/utils/export-csv";

export interface ImportColumn {
    header: string;   // Display name shown to user
    field: string;    // Expected CSV column name (normalized)
    required?: boolean;
    example?: string;
}

interface ImportResult {
    imported: number;
    errors: { row: number; reason: string }[];
}

interface ImportCsvModalProps {
    open: boolean;
    onClose: () => void;
    entityName: string;
    columns: ImportColumn[];
    onImport: (rows: Record<string, string>[]) => Promise<ImportResult>;
    onSuccess?: () => void;
}

export function ImportCsvModal({
    open, onClose, entityName, columns, onImport, onSuccess,
}: ImportCsvModalProps) {
    const fileRef = useRef<HTMLInputElement>(null);
    const [rows, setRows] = useState<Record<string, string>[]>([]);
    const [fileName, setFileName] = useState("");
    const [step, setStep] = useState<"upload" | "preview" | "result">("upload");
    const [result, setResult] = useState<ImportResult | null>(null);
    const [loading, setLoading] = useState(false);
    const [parseError, setParseError] = useState<string | null>(null);
    const [dragOver, setDragOver] = useState(false);

    const reset = () => {
        setRows([]); setFileName(""); setStep("upload");
        setResult(null); setParseError(null);
    };

    const handleClose = () => { reset(); onClose(); };

    const processFile = (file: File) => {
        if (!file.name.endsWith(".csv")) { setParseError("Solo se admiten archivos .csv"); return; }
        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const text = e.target?.result as string;
                const parsed = csvToObjects(text);
                if (parsed.length === 0) { setParseError("El archivo está vacío o no tiene filas de datos."); return; }
                setRows(parsed); setFileName(file.name); setParseError(null); setStep("preview");
            } catch { setParseError("No se pudo leer el archivo."); }
        };
        reader.readAsText(file, "UTF-8");
    };

    const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0]; if (file) processFile(file);
        e.target.value = "";
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault(); setDragOver(false);
        const file = e.dataTransfer.files?.[0]; if (file) processFile(file);
    };

    const handleImport = async () => {
        setLoading(true);
        try {
            const res = await onImport(rows);
            setResult(res); setStep("result");
            if (res.imported > 0) onSuccess?.();
        } catch { setResult({ imported: 0, errors: [{ row: 0, reason: "Error inesperado al importar." }] }); setStep("result"); }
        finally { setLoading(false); }
    };

    const downloadTemplate = () => {
        exportToCsv(`plantilla_${entityName}`, [{}], columns.map((c) => ({
            header: c.header,
            accessor: () => c.example ?? "",
        })));
    };

    const previewRows = rows.slice(0, 8);
    const visibleCols = columns.filter((c) => rows[0] && c.field in rows[0]);

    return (
        <Dialog open={open} onOpenChange={handleClose}>
            <DialogContent className="max-w-2xl max-h-[80vh] flex flex-col overflow-hidden">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <Upload className="w-4 h-4 text-primary" />
                        Importar {entityName} desde CSV
                    </DialogTitle>
                </DialogHeader>

                <div className="flex-1 overflow-y-auto space-y-4 py-2">
                    {/* Upload step */}
                    {step === "upload" && (
                        <div className="space-y-4">
                            <div
                                onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                                onDragLeave={() => setDragOver(false)}
                                onDrop={handleDrop}
                                onClick={() => fileRef.current?.click()}
                                className={`border-2 border-dashed rounded-xl p-10 flex flex-col items-center gap-3 cursor-pointer transition-colors ${
                                    dragOver ? "border-primary bg-primary/5" : "border-border hover:border-primary/50 hover:bg-muted/30"
                                }`}
                            >
                                <FileText className="w-10 h-10 text-muted-foreground opacity-50" />
                                <div className="text-center">
                                    <p className="text-sm font-medium text-foreground">Arrastra tu archivo o haz clic para seleccionar</p>
                                    <p className="text-xs text-muted-foreground mt-1">Solo archivos .csv · UTF-8</p>
                                </div>
                                <input ref={fileRef} type="file" accept=".csv" className="hidden" onChange={handleFile} />
                            </div>

                            {parseError && (
                                <div className="flex items-center gap-2 text-destructive text-sm">
                                    <AlertCircle className="w-4 h-4 shrink-0" /> {parseError}
                                </div>
                            )}

                            {/* Column reference */}
                            <div className="rounded-lg border border-border bg-muted/20 p-4 space-y-2">
                                <div className="flex items-center justify-between">
                                    <p className="text-xs font-medium text-foreground">Columnas esperadas</p>
                                    <Button variant="ghost" size="sm" className="h-7 text-xs gap-1" onClick={downloadTemplate}>
                                        <Download className="w-3 h-3" /> Descargar plantilla
                                    </Button>
                                </div>
                                <div className="flex flex-wrap gap-2">
                                    {columns.map((c) => (
                                        <span key={c.field} className={`text-xs px-2 py-0.5 rounded border ${
                                            c.required ? "bg-primary/10 border-primary/30 text-primary" : "bg-muted border-border text-muted-foreground"
                                        }`}>
                                            {c.header}{c.required ? " *" : ""}
                                        </span>
                                    ))}
                                </div>
                                <p className="text-[10px] text-muted-foreground">* obligatorio</p>
                            </div>
                        </div>
                    )}

                    {/* Preview step */}
                    {step === "preview" && (
                        <div className="space-y-3">
                            <div className="flex items-center justify-between">
                                <p className="text-sm text-muted-foreground">
                                    <span className="font-medium text-foreground">{rows.length}</span> filas detectadas en <span className="font-mono text-xs">{fileName}</span>
                                </p>
                                <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={reset}>
                                    <X className="w-3 h-3 mr-1" /> Cambiar archivo
                                </Button>
                            </div>
                            <div className="overflow-x-auto rounded-lg border border-border">
                                <table className="text-xs w-full">
                                    <thead className="bg-muted/40 text-muted-foreground">
                                        <tr>
                                            <th className="px-3 py-2 text-left font-medium">#</th>
                                            {visibleCols.map((c) => (
                                                <th key={c.field} className="px-3 py-2 text-left font-medium whitespace-nowrap">{c.header}</th>
                                            ))}
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-border">
                                        {previewRows.map((row, i) => (
                                            <tr key={i} className="bg-card hover:bg-muted/20">
                                                <td className="px-3 py-2 text-muted-foreground">{i + 2}</td>
                                                {visibleCols.map((c) => (
                                                    <td key={c.field} className="px-3 py-2 max-w-[140px] truncate text-foreground">{row[c.field] ?? ""}</td>
                                                ))}
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                                {rows.length > 8 && (
                                    <p className="text-[10px] text-muted-foreground px-3 py-2 border-t border-border">
                                        + {rows.length - 8} filas más…
                                    </p>
                                )}
                            </div>
                        </div>
                    )}

                    {/* Result step */}
                    {step === "result" && result && (
                        <div className="space-y-4">
                            <div className={`flex items-center gap-3 p-4 rounded-xl border ${
                                result.errors.length === 0 ? "bg-emerald-500/10 border-emerald-500/20" : "bg-amber-500/10 border-amber-500/20"
                            }`}>
                                {result.errors.length === 0
                                    ? <CheckCircle2 className="w-6 h-6 text-emerald-400 shrink-0" />
                                    : <AlertCircle className="w-6 h-6 text-amber-400 shrink-0" />
                                }
                                <div>
                                    <p className="text-sm font-medium text-foreground">
                                        {result.imported} {entityName} importados correctamente
                                    </p>
                                    {result.errors.length > 0 && (
                                        <p className="text-xs text-muted-foreground">{result.errors.length} filas con errores</p>
                                    )}
                                </div>
                            </div>
                            {result.errors.length > 0 && (
                                <div className="rounded-lg border border-border overflow-hidden">
                                    <table className="text-xs w-full">
                                        <thead className="bg-muted/30 text-muted-foreground">
                                            <tr>
                                                <th className="px-3 py-2 text-left">Fila</th>
                                                <th className="px-3 py-2 text-left">Error</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-border">
                                            {result.errors.slice(0, 10).map((e, i) => (
                                                <tr key={i} className="bg-card">
                                                    <td className="px-3 py-2 text-muted-foreground">{e.row}</td>
                                                    <td className="px-3 py-2 text-destructive">{e.reason}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </div>
                    )}
                </div>

                <DialogFooter className="border-t border-border pt-4">
                    {step === "upload" && (
                        <Button variant="outline" onClick={handleClose}>Cancelar</Button>
                    )}
                    {step === "preview" && (
                        <>
                            <Button variant="outline" onClick={reset}>Atrás</Button>
                            <Button onClick={handleImport} disabled={loading}>
                                {loading ? "Importando…" : `Importar ${rows.length} filas`}
                            </Button>
                        </>
                    )}
                    {step === "result" && (
                        <Button onClick={handleClose}>Cerrar</Button>
                    )}
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
