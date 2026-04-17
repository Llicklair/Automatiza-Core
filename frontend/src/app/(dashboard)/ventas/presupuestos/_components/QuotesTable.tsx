"use client";

import { Quote } from "@/lib/api";
import { formatCurrency } from "../_hooks/usePresupuestos";
import {
    FileSignature, Send, CheckCircle2, XCircle,
    FileCheck2, Loader2, Trash2, FilePlus2
} from "lucide-react";
import { format } from "date-fns";

interface QuotesTableProps {
    quotes: Quote[];
    isLoading: boolean;
    convertingId: string | null;
    onConvert: (q: Quote) => void;
    onDelete: (id: string) => void;
    onStatusChange: (id: string, status: string) => void;
    t: (key: string) => string;
}

function StatusBadge({ status, t }: { status: string; t: (key: string) => string }) {
    switch (status) {
        case "draft":
            return <span className="flex items-center gap-1.5 px-3 py-1 bg-muted text-foreground border border-border rounded-full text-xs font-medium"><FileSignature className="w-3.5 h-3.5" /> {t("draft")}</span>;
        case "sent":
            return <span className="flex items-center gap-1.5 px-3 py-1 bg-blue-500/10 text-blue-400 border border-blue-500/20 rounded-full text-xs font-medium"><Send className="w-3.5 h-3.5" /> {t("sent")}</span>;
        case "accepted":
            return <span className="flex items-center gap-1.5 px-3 py-1 bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 rounded-full text-xs font-medium"><CheckCircle2 className="w-3.5 h-3.5" /> {t("approved")}</span>;
        case "rejected":
            return <span className="flex items-center gap-1.5 px-3 py-1 bg-red-500/10 text-red-500 border border-red-500/20 rounded-full text-xs font-medium"><XCircle className="w-3.5 h-3.5" /> {t("rejected")}</span>;
        default:
            return null;
    }
}

export default function QuotesTable({ quotes, isLoading, convertingId, onConvert, onDelete, onStatusChange, t }: QuotesTableProps) {
    return (
        <div className="overflow-x-auto">
            <table className="w-full text-left text-sm whitespace-nowrap">
                <thead className="bg-muted/50 text-muted-foreground border-b border-border">
                    <tr>
                        <th className="px-6 py-4 font-medium">{t("quoteNumber")}</th>
                        <th className="px-6 py-4 font-medium">{t("client")}</th>
                        <th className="px-6 py-4 font-medium">{t("date")}</th>
                        <th className="px-6 py-4 font-medium text-right">{t("subtotal")}</th>
                        <th className="px-6 py-4 font-medium text-right text-primary">{t("total")}</th>
                        <th className="px-6 py-4 font-medium">{t("status")}</th>
                        <th className="px-6 py-4 font-medium text-right">{t("quoteAction")}</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800/50">
                    {isLoading ? (
                        <tr>
                            <td colSpan={7} className="px-6 py-12 text-center">
                                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary mx-auto"></div>
                            </td>
                        </tr>
                    ) : quotes.length === 0 ? (
                        <tr>
                            <td colSpan={7} className="px-6 py-16 text-center">
                                <FilePlus2 className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
                                <p className="text-muted-foreground font-medium">{t("quoteEmptyState")}</p>
                            </td>
                        </tr>
                    ) : quotes.map((q) => (
                        <tr key={q.id} className="hover:bg-primary/[0.02] transition-colors group">
                            <td className="px-6 py-4 font-medium text-foreground">
                                {q.quote_number || t("draft")}
                            </td>
                            <td className="px-6 py-4">
                                <div className="flex items-center gap-3">
                                    <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center text-muted-foreground font-medium">
                                        {q.client?.name.charAt(0) || "?"}
                                    </div>
                                    <span className="font-medium text-foreground">{q.client?.name || t("unknownClient")}</span>
                                </div>
                            </td>
                            <td className="px-6 py-4 text-muted-foreground">
                                {format(new Date(q.date), "dd/MM/yyyy")}
                            </td>
                            <td className="px-6 py-4 text-right text-foreground">
                                {formatCurrency(q.amount_base)}
                            </td>
                            <td className="px-6 py-4 text-right font-semibold text-primary">
                                {formatCurrency(q.amount_total)}
                            </td>
                            <td className="px-6 py-4">
                                <StatusBadge status={q.status} t={t} />
                            </td>
                            <td className="px-6 py-4 text-right">
                                <div className="flex items-center justify-end gap-2">
                                    {q.status !== "rejected" && q.status !== "accepted" && (
                                        <button
                                            onClick={() => onConvert(q)}
                                            disabled={convertingId === q.id}
                                            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-emerald-400 hover:text-emerald-300 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/20 rounded-lg transition-colors disabled:opacity-50"
                                            title={t("convertToInvoice")}
                                        >
                                            {convertingId === q.id
                                                ? <Loader2 className="w-3 h-3 animate-spin" />
                                                : <FileCheck2 className="w-3 h-3" />}
                                            {t("quoteToInvoice")}
                                        </button>
                                    )}
                                    {q.status === "accepted" && (
                                        <span className="text-xs text-muted-foreground italic">{t("quoteInvoiceIssued")}</span>
                                    )}
                                    <select
                                        value={q.status}
                                        onChange={(e) => onStatusChange(q.id, e.target.value)}
                                        className="bg-background text-xs border border-border rounded pl-2 pr-6 py-1.5 text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
                                    >
                                        <option value="draft">{t("draft")}</option>
                                        <option value="sent">{t("sent")}</option>
                                        <option value="accepted">{t("approved")}</option>
                                        <option value="rejected">{t("rejected")}</option>
                                    </select>
                                    <button
                                        onClick={() => onDelete(q.id)}
                                        className="p-1.5 rounded-lg text-muted-foreground hover:text-red-400 hover:bg-red-500/10 transition-colors"
                                        title={t("deleteQuote")}
                                    >
                                        <Trash2 className="w-3.5 h-3.5" />
                                    </button>
                                </div>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
