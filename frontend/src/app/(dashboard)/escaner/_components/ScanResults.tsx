import { Loader2, CheckCircle2, AlertTriangle, FileText, FileImage, Sheet, Mail, FolderOpen } from "lucide-react";
import type { ScanResult } from "../_hooks/useEscaner";
import { formatSize } from "../_hooks/useEscaner";

const CATEGORY_INFO: Record<string, { label: string; icon: typeof FileText; color: string; bg: string }> = {
    facturas: { label: "Facturas", icon: FileText, color: "text-primary", bg: "bg-primary/10" },
    bancos: { label: "Bancos", icon: FileText, color: "text-blue-400", bg: "bg-blue-500/10" },
    nominas: { label: "Nominas", icon: FileText, color: "text-emerald-400", bg: "bg-emerald-500/10" },
    fiscal: { label: "Asesor Fiscal", icon: AlertTriangle, color: "text-amber-400", bg: "bg-amber-500/10" },
    crm: { label: "CRM", icon: FileText, color: "text-rose-400", bg: "bg-rose-500/10" },
    excels: { label: "Excels", icon: Sheet, color: "text-green-400", bg: "bg-green-500/10" },
    informes: { label: "Informes", icon: Sheet, color: "text-purple-400", bg: "bg-purple-500/10" },
    correos: { label: "Correos", icon: Mail, color: "text-sky-400", bg: "bg-sky-500/10" },
    automatizaciones: { label: "Automatizacion", icon: Loader2, color: "text-orange-400", bg: "bg-orange-500/10" },
    rrhh: { label: "RRHH", icon: FileText, color: "text-muted-foreground", bg: "bg-muted" },
    otros: { label: "Otros", icon: FileImage, color: "text-muted-foreground", bg: "bg-muted" },
};

interface ScanResultsProps {
    results: ScanResult[];
    grouped: Record<string, ScanResult[]>;
    docStatuses: Record<string, { status: string; category: string | null }>;
}

export default function ScanResults({ results, grouped, docStatuses }: ScanResultsProps) {
    if (results.length === 0) return null;

    const done = results.filter(r => {
        const st = docStatuses[r.document.id]?.status || r.document.status;
        return st === "completed" || st === "processed" || st === "ready";
    }).length;
    const failed = results.filter(r => (docStatuses[r.document.id]?.status || r.document.status) === "failed").length;
    const pending = results.length - done - failed;

    return (
        <div className="space-y-4">
            <div className="flex items-center gap-3">
                {pending > 0 ? (
                    <Loader2 className="w-5 h-5 text-amber-400 animate-spin" />
                ) : (
                    <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                )}
                <h2 className="text-lg font-semibold text-foreground">
                    {results.length} archivo{results.length > 1 ? "s" : ""}
                </h2>
                <div className="flex gap-2 text-xs">
                    {done > 0 && <span className="text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full">{done} listos</span>}
                    {pending > 0 && <span className="text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded-full">{pending} procesando</span>}
                    {failed > 0 && <span className="text-red-400 bg-red-500/10 px-2 py-0.5 rounded-full">{failed} errores</span>}
                </div>
            </div>
            {/* Progress bar */}
            <div className="w-full h-1.5 bg-muted rounded-full overflow-hidden">
                <div
                    className="h-full bg-gradient-to-r from-emerald-500 to-emerald-400 transition-all duration-500 rounded-full"
                    style={{ width: `${((done + failed) / results.length) * 100}%` }}
                />
            </div>

            {Object.entries(grouped).map(([cat, items]) => {
                const info = CATEGORY_INFO[cat] || CATEGORY_INFO.otros;
                const Icon = info.icon;
                return (
                    <div key={cat} className="rounded-xl border border-border bg-card overflow-hidden">
                        <div className="px-5 py-3 border-b border-border flex items-center gap-3 bg-card">
                            <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${info.bg}`}>
                                <FolderOpen className={`w-4 h-4 ${info.color}`} />
                            </div>
                            <div>
                                <h3 className={`text-sm font-semibold ${info.color}`}>{info.label}</h3>
                                <p className="text-[10px] text-muted-foreground">{items.length} archivo{items.length > 1 ? "s" : ""}</p>
                            </div>
                        </div>
                        <div className="divide-y divide-border">
                            {items.map((r, i) => {
                                const live = docStatuses[r.document.id];
                                const st = live?.status || r.document.status;
                                const finalCat = live?.category || r.auto_category;
                                const reclassified = finalCat !== r.auto_category;
                                const isDone = st === "completed" || st === "processed" || st === "ready";
                                const isFailed = st === "failed";

                                return (
                                    <div key={i} className="flex items-center justify-between px-5 py-3">
                                        <div className="flex items-center gap-3 min-w-0">
                                            <Icon className={`w-4 h-4 ${info.color} flex-shrink-0`} />
                                            <span className="text-sm text-foreground truncate">{r.document.file_name}</span>
                                            <span className="text-xs text-muted-foreground">{formatSize(r.document.file_size)}</span>
                                            {reclassified && (
                                                <span className="text-[10px] text-primary bg-primary/10 px-1.5 py-0.5 rounded">
                                                    &rarr; {(CATEGORY_INFO[finalCat] || CATEGORY_INFO.otros).label}
                                                </span>
                                            )}
                                        </div>
                                        <div className="flex items-center gap-2">
                                            {isDone ? (
                                                <span className="text-[10px] text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full flex items-center gap-1">
                                                    <CheckCircle2 className="w-3 h-3" /> Clasificado
                                                </span>
                                            ) : isFailed ? (
                                                <span className="text-[10px] text-red-400 bg-red-500/10 px-2 py-0.5 rounded-full flex items-center gap-1">
                                                    <AlertTriangle className="w-3 h-3" /> Error
                                                </span>
                                            ) : (
                                                <span className="text-[10px] text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded-full">
                                                    <Loader2 className="w-3 h-3 inline-block mr-1 animate-spin" />
                                                    IA analizando
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                );
            })}
        </div>
    );
}
