"use client";

import { useEffect, useState } from "react";
import { api, Quote, Client, Product } from "@/lib/api";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";
import { logError } from "@/lib/logger";
import { useTranslations } from "next-intl";
import {
    FileText, Plus, Search, FileSignature, CheckCircle2,
    XCircle, Clock, Send, FilePlus2, DollarSign,
    FileCheck2, Loader2, AlertCircle, X, Trash2
} from "lucide-react";
import { format } from "date-fns";
import { es } from "date-fns/locale";

export default function QuotesPage() {
    const toastNotif = useToastStore();
    const t = useTranslations("ventas");
    const tc = useTranslations("common");
    const [quotes, setQuotes] = useState<Quote[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);

    // Formularios
    const [clients, setClients] = useState<Client[]>([]);
    const [products, setProducts] = useState<Product[]>([]);

    // Nuevo Presupuesto State
    const [selectedClient, setSelectedClient] = useState("");
    const [validUntil, setValidUntil] = useState("");
    const [lines, setLines] = useState([{ product_id: "", description: "", quantity: 1, unit_price: 0, tax_percentage: 21 }]);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [convertingId, setConvertingId] = useState<string | null>(null);
    const [toast, setToast] = useState<{ msg: string; type: "ok" | "err" } | null>(null);

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        setIsLoading(true);
        try {
            const [quotesRes, clientsRes, prodRes] = await Promise.all([
                api.erp.quotes.list(),
                api.erp.clients.list(),
                api.erp.products.list()
            ]);
            setQuotes(quotesRes);
            setClients(clientsRes);
            setProducts(prodRes);
        } catch (error) {
            logError("ventas/presupuestos/page", error);
        } finally {
            setIsLoading(false);
        }
    };

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsSubmitting(true);
        try {
            await api.erp.quotes.create({
                client_id: selectedClient,
                date: new Date().toISOString(),
                valid_until: validUntil ? new Date(validUntil).toISOString() : null,
                status: "draft",
                lines: lines.map(l => ({
                    ...l,
                    product_id: l.product_id || null
                })) as any
            });
            setShowModal(false);
            resetForm();
            await loadData();
        } catch (error) {
            logError("ventas/presupuestos/page", error);
            toastNotif.error(t("quoteErrorCreate"));
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleConvert = async (q: Quote) => {
        if (!await showConfirm({ message: t("quoteConvertConfirmDetail", { amount: formatCurrency(q.amount_total), client: q.client?.name ?? t("quoteThisClient") }), confirmLabel: tc("confirm"), confirmVariant: "primary" })) return;
        setConvertingId(q.id);
        try {
            const result = await api.erp.quotes.convertToInvoice(q.id);
            setToast({ msg: t("quoteInvoiceCreatedDetail", { number: result.invoice_number, amount: formatCurrency(result.amount_total) }), type: "ok" });
            await loadData();
        } catch (e: any) {
            setToast({ msg: t("errorConvert") + ": " + (e.message || ""), type: "err" });
        } finally {
            setConvertingId(null);
            setTimeout(() => setToast(null), 6000);
        }
    };

    const handleDelete = async (id: string) => {
        if (!await showConfirm({ message: t("quoteDeleteConfirm"), confirmLabel: tc("delete"), confirmVariant: "danger" })) return;
        try {
            await api.erp.quotes.delete(id);
            setQuotes(prev => prev.filter(q => q.id !== id));
        } catch (e: any) {
            setToast({ msg: t("errorDelete") + ": " + (e.message || ""), type: "err" });
            setTimeout(() => setToast(null), 4000);
        }
    };

    const handleStatusChange = async (id: string, newStatus: string) => {
        try {
            // Optimistic update
            setQuotes(prev => prev.map(q => q.id === id ? { ...q, status: newStatus } : q));
            await api.erp.quotes.update(id, { status: newStatus });
        } catch (error) {
            logError("ventas/presupuestos/page", error);
            await loadData(); // Revert
        }
    };

    const resetForm = () => {
        setSelectedClient("");
        setValidUntil("");
        setLines([{ product_id: "", description: "", quantity: 1, unit_price: 0, tax_percentage: 21 }]);
    };

    const updateLine = (index: number, field: string, value: any) => {
        const newLines = [...lines];
        if (field === "product_id" && value) {
            const prod = products.find(p => p.id === value);
            if (prod) {
                newLines[index].description = prod.name;
                newLines[index].unit_price = prod.price;
                newLines[index].tax_percentage = prod.tax_percentage;
            }
        }
        (newLines[index] as any)[field] = value;
        setLines(newLines);
    };

    const formatCurrency = (val: number) => {
        return new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' }).format(val);
    };

    const getStatusBadge = (status: string) => {
        switch (status) {
            case 'draft':
                return <span className="flex items-center gap-1.5 px-3 py-1 bg-muted text-foreground border border-border rounded-full text-xs font-medium"><FileSignature className="w-3.5 h-3.5" /> {t("draft")}</span>;
            case 'sent':
                return <span className="flex items-center gap-1.5 px-3 py-1 bg-blue-500/10 text-blue-400 border border-blue-500/20 rounded-full text-xs font-medium"><Send className="w-3.5 h-3.5" /> {t("sent")}</span>;
            case 'accepted':
                return <span className="flex items-center gap-1.5 px-3 py-1 bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 rounded-full text-xs font-medium"><CheckCircle2 className="w-3.5 h-3.5" /> {t("approved")}</span>;
            case 'rejected':
                return <span className="flex items-center gap-1.5 px-3 py-1 bg-red-500/10 text-red-500 border border-red-500/20 rounded-full text-xs font-medium"><XCircle className="w-3.5 h-3.5" /> {t("rejected")}</span>;
            default:
                return null;
        }
    };

    return (
        <div className="min-h-screen bg-background text-foreground p-8">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-8">
                <div>
                    <h1 className="text-3xl font-light text-foreground flex items-center gap-3">
                        <div className="p-2 bg-primary/10 rounded-xl">
                            <FileText className="w-8 h-8 text-primary" />
                        </div>
                        {t("quotes")}
                    </h1>
                    <p className="text-muted-foreground mt-2 ml-14 text-sm max-w-2xl">
                        {t("quotesDescription")}
                    </p>
                </div>

                <div className="flex gap-3">
                    <button
                        onClick={() => setShowModal(true)}
                        className="flex items-center gap-2 bg-primary hover:bg-primary text-foreground shadow-lg shadow-primary/20 px-5 py-2.5 rounded-full font-medium transition-colors"
                    >
                        <Plus className="w-4 h-4" />
                        {t("newQuote")}
                    </button>
                    <button className="flex items-center gap-2 bg-card border border-border hover:bg-muted text-foreground px-5 py-2.5 rounded-full font-medium transition-colors">
                        <Clock className="w-4 h-4 text-muted-foreground" />
                        {t("quoteExpired")}
                    </button>
                </div>
            </div>

            <div className="bg-card border border-border rounded-2xl overflow-hidden shadow-xl">
                <div className="p-4 border-b border-border flex justify-between items-center bg-muted">
                    <div className="relative">
                        <Search className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
                        <input
                            type="text"
                            placeholder={t("quoteSearchPlaceholder")}
                            className="bg-background border border-border text-sm text-foreground rounded-lg pl-10 pr-4 py-2 focus:outline-none focus:border-primary transition-colors w-72"
                        />
                    </div>
                </div>

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
                                                {q.client?.name.charAt(0) || '?'}
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
                                        {getStatusBadge(q.status)}
                                    </td>
                                    <td className="px-6 py-4 text-right">
                                        <div className="flex items-center justify-end gap-2">
                                            {/* Convertir en Factura */}
                                            {q.status !== "rejected" && q.status !== "accepted" && (
                                                <button
                                                    onClick={() => handleConvert(q)}
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
                                            {/* Cambiar estado */}
                                            <select
                                                value={q.status}
                                                onChange={(e) => handleStatusChange(q.id, e.target.value)}
                                                className="bg-background text-xs border border-border rounded pl-2 pr-6 py-1.5 text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
                                            >
                                                <option value="draft">{t("draft")}</option>
                                                <option value="sent">{t("sent")}</option>
                                                <option value="accepted">{t("approved")}</option>
                                                <option value="rejected">{t("rejected")}</option>
                                            </select>
                                            {/* Eliminar */}
                                            <button
                                                onClick={() => handleDelete(q.id)}
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
            </div>

            {/* Modal Crear Presupuesto Rápido */}
            {showModal && (
                <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                    <div className="bg-card border border-border rounded-2xl w-full max-w-3xl overflow-hidden shadow-2xl">
                        <div className="p-5 border-b border-border flex justify-between items-center bg-muted">
                            <h2 className="text-lg font-medium text-foreground flex items-center gap-2">
                                <FileText className="w-4 h-4 text-primary" />
                                {t("newQuote")}
                            </h2>
                            <button onClick={() => setShowModal(false)} className="text-muted-foreground hover:text-foreground">✕</button>
                        </div>

                        <form onSubmit={handleCreate} className="p-6 space-y-6">
                            <div className="grid grid-cols-2 gap-6 border-b border-border pb-6">
                                <div>
                                    <label className="block text-sm text-muted-foreground mb-1.5">{t("client")}</label>
                                    <select
                                        required
                                        value={selectedClient}
                                        onChange={e => setSelectedClient(e.target.value)}
                                        className="w-full bg-background border border-border rounded-lg px-4 py-2.5 text-foreground focus:outline-none focus:border-primary"
                                    >
                                        <option value="" disabled>{t("quoteSelectClient")}</option>
                                        {clients.map(c => (
                                            <option key={c.id} value={c.id}>{c.name}</option>
                                        ))}
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-sm text-muted-foreground mb-1.5">{t("validUntil")}</label>
                                    <input
                                        type="date"
                                        value={validUntil}
                                        onChange={e => setValidUntil(e.target.value)}
                                        className="w-full bg-background border border-border rounded-lg px-4 py-2.5 text-foreground focus:outline-none focus:border-primary"
                                    />
                                </div>
                            </div>

                            <div>
                                <div className="flex justify-between items-center mb-3">
                                    <label className="block text-sm font-medium text-foreground">{t("conceptLines")}</label>
                                    <button
                                        type="button"
                                        onClick={() => setLines([...lines, { product_id: "", description: "", quantity: 1, unit_price: 0, tax_percentage: 21 }])}
                                        className="text-xs text-primary hover:text-primary flex items-center gap-1 font-medium"
                                    >
                                        <Plus className="w-3 h-3" /> {t("addConcept")}
                                    </button>
                                </div>
                                <div className="space-y-3">
                                    {lines.map((l, i) => (
                                        <div key={i} className="flex gap-3 items-start bg-muted p-3 rounded-lg border border-border">
                                            <div className="flex-1">
                                                <input
                                                    type="text"
                                                    required
                                                    value={l.description}
                                                    onChange={e => updateLine(i, 'description', e.target.value)}
                                                    placeholder={t("conceptPlaceholder")}
                                                    className="w-full bg-background border border-border rounded px-3 py-1.5 text-sm text-foreground focus:border-primary"
                                                />
                                                <div className="mt-2 text-xs flex gap-2">
                                                    <select
                                                        value={l.product_id}
                                                        onChange={e => updateLine(i, 'product_id', e.target.value)}
                                                        className="bg-background border border-border rounded px-2 text-muted-foreground"
                                                    >
                                                        <option value="">{t("quoteFreeEntry")}</option>
                                                        {products.map(p => <option key={p.id} value={p.id}>{t("quoteCatalog")}: {p.name}</option>)}
                                                    </select>
                                                </div>
                                            </div>
                                            <div className="w-20">
                                                <input
                                                    type="number"
                                                    min="1"
                                                    value={l.quantity}
                                                    onChange={e => updateLine(i, 'quantity', parseFloat(e.target.value))}
                                                    className="w-full bg-background border border-border rounded px-3 py-1.5 text-sm text-center text-foreground focus:border-primary"
                                                />
                                                <span className="text-[10px] text-muted-foreground block text-center mt-1">{t("quoteUnits")}</span>
                                            </div>
                                            <div className="w-28 relative">
                                                <DollarSign className="w-3 h-3 text-muted-foreground absolute left-2 top-2.5" />
                                                <input
                                                    type="number"
                                                    step="0.01"
                                                    value={l.unit_price}
                                                    onChange={e => updateLine(i, 'unit_price', parseFloat(e.target.value))}
                                                    className="w-full bg-background border border-border rounded pl-6 pr-2 py-1.5 text-sm text-right text-foreground focus:border-primary"
                                                />
                                                <span className="text-[10px] text-muted-foreground block text-right mt-1 pr-1">{t("quoteUnitPrice")}</span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            <div className="pt-4 flex justify-end gap-3 mt-4">
                                <button
                                    type="button"
                                    onClick={() => setShowModal(false)}
                                    className="px-5 py-2.5 text-foreground hover:text-foreground transition-colors font-medium border border-transparent hover:border-border rounded-lg"
                                >
                                    {tc("cancel")}
                                </button>
                                <button
                                    type="submit"
                                    disabled={isSubmitting || !selectedClient || lines.some(l => !l.description)}
                                    className="bg-primary hover:bg-primary text-foreground px-6 py-2.5 rounded-lg font-medium transition-colors shadow-lg shadow-primary/20 disabled:opacity-50"
                                >
                                    {isSubmitting ? t("quoteSaving") : t("quoteCreateDraft")}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Toast */}
            {toast && (
                <div className={`fixed bottom-6 right-6 z-50 flex items-center gap-3 px-5 py-3 rounded-2xl shadow-2xl text-sm font-medium max-w-sm ${toast.type === "ok"
                    ? "bg-emerald-500/10 border border-emerald-500/20 text-emerald-400"
                    : "bg-red-500/10 border border-red-500/20 text-red-400"
                    }`}>
                    {toast.type === "ok" ? <CheckCircle2 className="w-5 h-5 flex-shrink-0" /> : <AlertCircle className="w-5 h-5 flex-shrink-0" />}
                    <span className="flex-1">{toast.msg}</span>
                    <button onClick={() => setToast(null)} className="opacity-60 hover:opacity-100"><X className="w-4 h-4" /></button>
                </div>
            )}
        </div>
    );
}
