import { FileText, X, ScanLine, Loader2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { formatSize } from "../_hooks/useEscaner";

interface SelectedFilesListProps {
    files: File[];
    scanning: boolean;
    onRemove: (index: number) => void;
    onScan: () => void;
}

export default function SelectedFilesList({ files, scanning, onRemove, onScan }: SelectedFilesListProps) {
    const t = useTranslations("escaner");
    if (files.length === 0) return null;

    return (
        <div className="space-y-3">
            <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
                {t("selectedFiles.heading", { count: files.length })}
            </h2>
            <div className="rounded-xl border border-border bg-card divide-y divide-border">
                {files.map((file, i) => (
                    <div key={i} className="flex items-center justify-between px-5 py-3">
                        <div className="flex items-center gap-3 min-w-0">
                            <FileText className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                            <span className="text-sm text-foreground truncate">{file.name}</span>
                            <span className="text-xs text-muted-foreground">{formatSize(file.size)}</span>
                        </div>
                        <button
                            onClick={(e) => { e.stopPropagation(); onRemove(i); }}
                            className="p-1 rounded hover:bg-red-500/10 text-muted-foreground hover:text-red-400 transition"
                        >
                            <X className="w-4 h-4" />
                        </button>
                    </div>
                ))}
            </div>

            <button
                onClick={onScan}
                disabled={scanning}
                className="w-full flex items-center justify-center gap-2 bg-primary hover:bg-primary disabled:opacity-50 disabled:cursor-not-allowed text-foreground py-3 rounded-xl font-semibold transition-all shadow-lg shadow-primary/20"
            >
                {scanning ? (
                    <>
                        <Loader2 className="w-5 h-5 animate-spin" />
                        {t("selectedFiles.scanning")}
                    </>
                ) : (
                    <>
                        <ScanLine className="w-5 h-5" />
                        {t("selectedFiles.scanButton", { count: files.length })}
                    </>
                )}
            </button>
        </div>
    );
}
