"use client";

import { useEffect, useRef, useState } from "react";
import {
    Upload, Loader2, AlertCircle, CheckCircle2, FileText, Trash2, AlertTriangle, Package,
} from "lucide-react";
import { api } from "@/lib/api";
import type { InvoiceDraft } from "@/lib/api/erp";

type Row = { draft: InvoiceDraft; filename: string };

/**
 * Escáner de facturas de COMPRA → integra en el ERP.
 * Sube 1+ facturas (PDF/imagen) → la IA extrae → revisas → crea facturas de
 * compra + asiento contable + (opcional) suma stock de las líneas que casan
 * con tu catálogo. Todo tras tu revisión.
 */
export function FacturasImportPanel({ initialFiles }: { initialFiles?: File[] } = {}) {
    const [rows, setRows] = useState<Row[]>([]);
    const [scanning, setScanning] = useState(false);
    const [importing, setImporting] = useState(false);
    const [scanErrors, setScanErrors] = useState<string[]>([]);
    const [summary, setSummary] = useState<string | null>(null);
    const fileRef = useRef<HTMLInputElement>(null);

    async function processFiles(files: File[]) {
        if (!files.length) return;
        setScanning(true);
        setScanErrors([]);
        setSummary(null);
        try {
            const res = await api.erp.invoices.scanBatch(files);
            const ok: Row[] = [];
            const errs: string[] = [];
            res.results.forEach(r => {
                if (r.extracted) ok.push({ draft: { ...r.extracted, apply_stock: false }, filename: r.filename });
                else errs.push(`${r.filename}: ${r.error || "no se pudo extraer"}`);
            });
            setRows(prev => [...prev, ...ok]);
            setScanErrors(errs);
        } catch (err: unknown) {
            setScanErrors([err instanceof Error ? err.message : "Error al escanear"]);
        } finally {
            setScanning(false);
            if (fileRef.current) fileRef.current.value = "";
        }
    }

    async function handleFiles(e: React.ChangeEvent<HTMLInputElement>) {
        await processFiles(Array.from(e.target.files || []));
    }

    // Auto-procesa las facturas enrutadas desde el intake unificado (sin re-subir).
    useEffect(() => {
        if (initialFiles?.length) void processFiles(initialFiles);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [initialFiles]);

    function patch(i: number, field: keyof InvoiceDraft, value: unknown) {
        setRows(prev => prev.map((r, idx) => idx === i ? { ...r, draft: { ...r.draft, [field]: value } } : r));
    }
    function patchEmisor(i: number, field: string, value: string) {
        setRows(prev => prev.map((r, idx) => idx === i
            ? { ...r, draft: { ...r.draft, emisor: { ...r.draft.emisor, [field]: value } } } : r));
    }
    function remove(i: number) {
        setRows(prev => prev.filter((_, idx) => idx !== i));
    }

    async function handleImport() {
        if (!rows.length) return;
        setImporting(true);
        setSummary(null);
        try {
            const res = await api.erp.invoices.import(rows.map(r => r.draft));
            const movedLines = res.results.reduce((n, r) => n + (r.stock_applied?.length || 0), 0);
            const unmatched = res.results.reduce((n, r) => n + (r.stock_unmatched?.length || 0), 0);
            const created = res.results.reduce((n, r) => n + (r.stock_created?.length || 0), 0);
            const failed = res.total - res.created;
            let msg = `${res.created} factura${res.created !== 1 ? "s" : ""} de compra creada${res.created !== 1 ? "s" : ""}`;
            if (movedLines) msg += ` · ${movedLines} línea${movedLines !== 1 ? "s" : ""} movieron stock`;
            if (created) msg += ` · ${created} producto${created !== 1 ? "s" : ""} creado${created !== 1 ? "s" : ""}`;
            if (unmatched) msg += ` · ${unmatched} sin casar (no afectan stock)`;
            if (failed) msg += ` · ${failed} con error`;
            setSummary(msg);
            if (failed === 0) setRows([]);
        } catch (err: unknown) {
            setSummary(err instanceof Error ? err.message : "Error al importar");
        } finally {
            setImporting(false);
        }
    }

    return (
        <div className="space-y-6">
            <p className="text-sm text-muted-foreground">
                Sube facturas de proveedor (PDF o foto). La IA extrae los datos; tú revisas y
                creas la <strong>factura de compra + asiento contable</strong>. Marca
                «actualizar stock» para sumar inventario de las líneas que casen con tu catálogo.
            </p>

            {/* Upload */}
            <label className={`flex flex-col items-center justify-center gap-3 border-2 border-dashed rounded-xl px-6 py-10 cursor-pointer transition-colors ${
                scanning ? "border-primary/50 bg-primary/5" : "border-border hover:border-primary/50 hover:bg-primary/5"
            }`}>
                {scanning ? <Loader2 className="w-8 h-8 text-primary animate-spin" /> : <Upload className="w-8 h-8 text-muted-foreground" />}
                <div className="text-center">
                    <p className="text-sm font-medium text-foreground">
                        {scanning ? "Escaneando facturas…" : "Arrastra una o varias facturas o haz clic"}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">PDF, JPG, PNG · hasta 20 por lote</p>
                </div>
                <input ref={fileRef} type="file" multiple accept=".pdf,image/*" className="hidden"
                    disabled={scanning} onChange={handleFiles} />
            </label>

            {scanErrors.length > 0 && (
                <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 px-4 py-3 text-sm text-amber-400 space-y-1">
                    {scanErrors.map((e, i) => (
                        <div key={i} className="flex items-start gap-2">
                            <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" /> <span>{e}</span>
                        </div>
                    ))}
                </div>
            )}

            {/* Review cards */}
            {rows.map((row, i) => {
                const d = row.draft;
                const lowConf = (d.confidence ?? 1) < 0.7;
                return (
                    <div key={i} className="rounded-xl border border-border bg-card p-5 space-y-4">
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2 min-w-0">
                                <FileText className="w-4 h-4 text-primary shrink-0" />
                                <span className="text-sm font-medium text-foreground truncate">{row.filename}</span>
                                <span className={`text-[10px] px-1.5 py-0.5 rounded shrink-0 ${
                                    lowConf ? "bg-amber-500/15 text-amber-400" : "bg-green-500/15 text-green-400"
                                }`}>
                                    {Math.round((d.confidence ?? 0) * 100)}% confianza
                                </span>
                            </div>
                            <button onClick={() => remove(i)} title="Descartar"
                                className="p-1.5 rounded hover:bg-red-500/10 text-muted-foreground hover:text-red-400 transition-colors">
                                <Trash2 className="w-4 h-4" />
                            </button>
                        </div>

                        {d.warnings?.length > 0 && (
                            <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 px-3 py-2 text-xs text-amber-400 space-y-0.5">
                                {d.warnings.map((w, k) => <div key={k}>⚠ {w}</div>)}
                            </div>
                        )}

                        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                            <Field label="Proveedor" value={d.emisor?.name || ""} onChange={v => patchEmisor(i, "name", v)} />
                            <Field label="NIF" value={d.emisor?.nif || ""} onChange={v => patchEmisor(i, "nif", v)} />
                            <Field label="Nº factura" value={d.invoice_number || ""} onChange={v => patch(i, "invoice_number", v)} />
                            <Field label="Fecha" value={d.issue_date || ""} onChange={v => patch(i, "issue_date", v)} />
                            <Field label="Base" type="number" value={String(d.amount_base ?? "")} onChange={v => patch(i, "amount_base", Number(v))} />
                            <Field label="IVA" type="number" value={String(d.tax_amount ?? "")} onChange={v => patch(i, "tax_amount", Number(v))} />
                            <Field label="Total" type="number" value={String(d.amount_total ?? "")} onChange={v => patch(i, "amount_total", Number(v))} />
                        </div>

                        {d.lines?.length > 0 && (
                            <div className="text-xs text-muted-foreground">
                                <div className="font-medium mb-1">{d.lines.length} línea{d.lines.length !== 1 ? "s" : ""}:</div>
                                <ul className="space-y-0.5 max-h-32 overflow-auto">
                                    {d.lines.map((l, k) => (
                                        <li key={k} className="flex justify-between gap-2">
                                            <span className="truncate">{l.quantity}× {l.description}</span>
                                            <span className="shrink-0">{l.total}€</span>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        )}

                        <label className="flex items-center gap-2 text-sm text-foreground cursor-pointer">
                            <input type="checkbox" checked={!!d.apply_stock}
                                onChange={e => patch(i, "apply_stock", e.target.checked)}
                                className="rounded border-border" />
                            <Package className="w-4 h-4 text-muted-foreground" />
                            Actualizar stock (casa por código de barras, SKU o nombre)
                        </label>
                        {d.apply_stock && (
                            <label className="flex items-center gap-2 text-sm text-foreground cursor-pointer ml-6">
                                <input type="checkbox" checked={!!d.create_missing}
                                    onChange={e => patch(i, "create_missing", e.target.checked)}
                                    className="rounded border-border" />
                                Crear automáticamente los productos que falten
                            </label>
                        )}
                    </div>
                );
            })}

            {rows.length > 0 && (
                <button onClick={handleImport} disabled={importing}
                    className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg bg-primary text-foreground font-medium hover:bg-primary/90 disabled:opacity-60 transition-colors">
                    {importing ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
                    Crear {rows.length} factura{rows.length !== 1 ? "s" : ""} de compra
                </button>
            )}

            {summary && (
                <div className="flex gap-2 text-sm rounded-lg px-4 py-3 border bg-green-500/10 text-green-400 border-green-500/20">
                    <CheckCircle2 className="w-4 h-4 mt-0.5 shrink-0" />
                    <span>{summary}</span>
                </div>
            )}
        </div>
    );
}

function Field({ label, value, onChange, type = "text" }: {
    label: string; value: string; onChange: (v: string) => void; type?: string;
}) {
    return (
        <label className="block">
            <span className="text-[11px] text-muted-foreground">{label}</span>
            <input type={type} value={value} onChange={e => onChange(e.target.value)}
                className="mt-0.5 w-full rounded-md border border-border bg-background px-2 py-1.5 text-sm text-foreground focus:border-primary focus:outline-none" />
        </label>
    );
}
