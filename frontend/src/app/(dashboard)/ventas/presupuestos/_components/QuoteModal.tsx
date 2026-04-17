"use client";

import { Client, Product } from "@/lib/api";
import { QuoteLine } from "../_hooks/usePresupuestos";
import { FileText, Plus, DollarSign } from "lucide-react";

interface QuoteModalProps {
    clients: Client[];
    products: Product[];
    selectedClient: string;
    onClientChange: (v: string) => void;
    validUntil: string;
    onValidUntilChange: (v: string) => void;
    lines: QuoteLine[];
    isSubmitting: boolean;
    onSubmit: (e: React.FormEvent) => void;
    onClose: () => void;
    onUpdateLine: (index: number, field: string, value: any) => void;
    onAddLine: () => void;
    t: (key: string) => string;
    tc: (key: string) => string;
}

export default function QuoteModal({
    clients, products, selectedClient, onClientChange,
    validUntil, onValidUntilChange, lines, isSubmitting,
    onSubmit, onClose, onUpdateLine, onAddLine, t, tc,
}: QuoteModalProps) {
    return (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-card border border-border rounded-2xl w-full max-w-3xl overflow-hidden shadow-2xl">
                <div className="p-5 border-b border-border flex justify-between items-center bg-muted">
                    <h2 className="text-lg font-medium text-foreground flex items-center gap-2">
                        <FileText className="w-4 h-4 text-primary" />
                        {t("newQuote")}
                    </h2>
                    <button onClick={onClose} className="text-muted-foreground hover:text-foreground">&#10005;</button>
                </div>

                <form onSubmit={onSubmit} className="p-6 space-y-6">
                    <div className="grid grid-cols-2 gap-6 border-b border-border pb-6">
                        <div>
                            <label className="block text-sm text-muted-foreground mb-1.5">{t("client")}</label>
                            <select
                                required
                                value={selectedClient}
                                onChange={e => onClientChange(e.target.value)}
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
                                onChange={e => onValidUntilChange(e.target.value)}
                                className="w-full bg-background border border-border rounded-lg px-4 py-2.5 text-foreground focus:outline-none focus:border-primary"
                            />
                        </div>
                    </div>

                    <div>
                        <div className="flex justify-between items-center mb-3">
                            <label className="block text-sm font-medium text-foreground">{t("conceptLines")}</label>
                            <button
                                type="button"
                                onClick={onAddLine}
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
                                            onChange={e => onUpdateLine(i, "description", e.target.value)}
                                            placeholder={t("conceptPlaceholder")}
                                            className="w-full bg-background border border-border rounded px-3 py-1.5 text-sm text-foreground focus:border-primary"
                                        />
                                        <div className="mt-2 text-xs flex gap-2">
                                            <select
                                                value={l.product_id}
                                                onChange={e => onUpdateLine(i, "product_id", e.target.value)}
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
                                            onChange={e => onUpdateLine(i, "quantity", parseFloat(e.target.value))}
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
                                            onChange={e => onUpdateLine(i, "unit_price", parseFloat(e.target.value))}
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
                            onClick={onClose}
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
    );
}
