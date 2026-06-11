"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { useFormat } from "@/hooks/useFormat";
import { CheckCircle2, Copy, Download, Trash2, ChevronDown, ChevronUp } from "lucide-react";
import type { HRDocument } from "@/lib/api/hr_documents";
import { DOC_TYPES } from "../_hooks/useHRDocumentos";

function StatusBadge({ status }: { status: HRDocument["status"] }) {
    const t = useTranslations("rrhh");
    return status === "approved" ? (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="w-3 h-3" /> {t("documentos.status.approved")}
        </span>
    ) : (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
            {t("documentos.status.draft")}
        </span>
    );
}

interface Props {
    doc: HRDocument;
    onApprove: (id: string) => void;
    onDelete: (id: string) => void;
}

export function DocumentCard({ doc, onApprove, onDelete }: Props) {
    const t = useTranslations("rrhh");
    const tc = useTranslations("common");
    const { fmtDate } = useFormat();
    const [expanded, setExpanded] = useState(false);
    const [copying, setCopying] = useState(false);
    const docTypeKey = DOC_TYPES.find(d => d.value === doc.doc_type)?.labelKey;
    const docTypeLabel = docTypeKey ? t(docTypeKey) : doc.doc_type;
    const date = fmtDate(doc.created_at, { day: "numeric", month: "short", year: "numeric" });

    const handleCopy = async () => {
        setCopying(true);
        await navigator.clipboard.writeText(doc.content_html).catch(() => {});
        setTimeout(() => setCopying(false), 1500);
    };

    const handleDownloadPdf = () => {
        const win = window.open("", "_blank");
        if (!win) return;
        win.document.write(`<!DOCTYPE html><html><head><meta charset="utf-8"><title>${doc.title}</title><style>@media print{body{margin:0}}</style></head><body>${doc.content_html}</body></html>`);
        win.document.close();
        win.focus();
        setTimeout(() => { win.print(); }, 400);
    };

    return (
        <div className="bg-card border border-border rounded-xl overflow-hidden">
            <div className="p-4 flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                        <h3 className="text-sm font-medium text-foreground truncate">{doc.title}</h3>
                        <StatusBadge status={doc.status} />
                        {doc.doc_number && (
                            <span className="text-[10px] font-mono text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
                                {doc.doc_number}
                            </span>
                        )}
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">{docTypeLabel} · {doc.employee_name} · {date}</p>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                    <button onClick={handleDownloadPdf} title={t("common.downloadPdf")}
                        className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors" aria-label={t("common.downloadPdf")}>
                        <Download className="w-4 h-4" aria-hidden="true" />
                    </button>
                    <button onClick={handleCopy} title={t("documentos.copyHtml")}
                        className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors" aria-label={t("documentos.copyHtml")}>
                        {copying ? <CheckCircle2 className="w-4 h-4 text-emerald-400" aria-hidden="true" /> : <Copy className="w-4 h-4" aria-hidden="true" />}
                    </button>
                    {doc.status === "draft" && (
                        <button onClick={() => onApprove(doc.id)} title={t("common.approve")}
                            className="p-1.5 rounded-lg text-emerald-400 hover:bg-emerald-500/10 transition-colors" aria-label={t("common.approve")}>
                            <CheckCircle2 className="w-4 h-4" aria-hidden="true" />
                        </button>
                    )}
                    <button onClick={() => onDelete(doc.id)} title={tc("delete")}
                        className="p-1.5 rounded-lg text-red-400 hover:bg-red-500/10 transition-colors" aria-label={tc("delete")}>
                        <Trash2 className="w-4 h-4" aria-hidden="true" />
                    </button>
                    <button onClick={() => setExpanded(v => !v)}
                        className="p-1.5 rounded-lg text-muted-foreground hover:bg-muted transition-colors" aria-label={t("documentos.toggleExpandAria")}>
                        {expanded ? <ChevronUp className="w-4 h-4" aria-hidden="true" /> : <ChevronDown className="w-4 h-4" aria-hidden="true" />}
                    </button>
                </div>
            </div>
            {expanded && (
                <div className="border-t border-border p-4 bg-background">
                    <div className="prose prose-invert prose-sm max-w-none text-foreground"
                        dangerouslySetInnerHTML={{ __html: doc.content_html }} />
                </div>
            )}
        </div>
    );
}
