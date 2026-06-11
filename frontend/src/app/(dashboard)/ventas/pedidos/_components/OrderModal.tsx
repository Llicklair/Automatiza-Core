"use client";

import { type Client, type Product, type SalesOrderLine } from "@/lib/api";
import { fmt } from "../_hooks/usePedidos";
import { Plus, X, Loader2 } from "lucide-react";

type OrderForm = {
    client_id: string;
    expected_delivery: string;
    notes: string;
    lines: SalesOrderLine[];
};

interface OrderModalProps {
    form: OrderForm;
    setForm: React.Dispatch<React.SetStateAction<OrderForm>>;
    clients: Client[];
    products: Product[];
    saving: boolean;
    lineTotal: (line: SalesOrderLine) => number;
    orderTotal: number;
    onSubmit: (e: React.FormEvent) => void;
    onClose: () => void;
    setLine: (i: number, field: keyof SalesOrderLine, value: any) => void;
    addLine: () => void;
    removeLine: (i: number) => void;
    t: (key: string, params?: any) => string;
    tc: (key: string) => string;
}

type FormType = OrderModalProps["form"];

export default function OrderModal({
    form, setForm, clients, products, saving,
    lineTotal, orderTotal, onSubmit, onClose,
    setLine, addLine, removeLine, t, tc,
}: OrderModalProps) {
    return (
        <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/60 backdrop-blur-sm pt-16 pb-8 overflow-y-auto">
            <div className="bg-card border border-border rounded-2xl p-8 w-full max-w-2xl shadow-2xl">
                <div className="flex items-center justify-between mb-6">
                    <h2 className="text-lg font-bold text-foreground">{t("newOrderTitle")}</h2>
                    <button onClick={onClose} className="text-muted-foreground hover:text-foreground transition-colors" aria-label="Cerrar formulario de pedido">
                        <X className="w-5 h-5" aria-hidden="true" />
                    </button>
                </div>
                <form onSubmit={onSubmit} className="space-y-6">
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-xs text-muted-foreground mb-1.5 font-medium">{t("client")} *</label>
                            <select
                                required value={form.client_id}
                                onChange={e => setForm((f: FormType) => ({ ...f, client_id: e.target.value }))}
                                className="w-full bg-card border border-border text-foreground text-sm rounded-xl px-3 py-2.5 focus:outline-none focus:border-primary transition-colors"
                            >
                                <option value="">{t("orderSelectClient")}</option>
                                {clients.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                            </select>
                        </div>
                        <div>
                            <label className="block text-xs text-muted-foreground mb-1.5 font-medium">{t("expectedDelivery")}</label>
                            <input
                                type="date" value={form.expected_delivery}
                                onChange={e => setForm((f: FormType) => ({ ...f, expected_delivery: e.target.value }))}
                                className="w-full bg-card border border-border text-foreground text-sm rounded-xl px-3 py-2.5 focus:outline-none focus:border-primary transition-colors"
                            />
                        </div>
                    </div>

                    <div>
                        <div className="flex items-center justify-between mb-3">
                            <p className="text-sm font-semibold text-foreground">{t("orderLines")}</p>
                            <button type="button" onClick={addLine} className="text-xs text-primary hover:text-primary flex items-center gap-1 transition-colors">
                                <Plus className="w-3 h-3" /> {t("addLine")}
                            </button>
                        </div>
                        <div className="space-y-3">
                            {form.lines.map((line, i) => (
                                <div key={i} className="grid grid-cols-12 gap-2 items-end bg-muted rounded-xl p-3">
                                    <div className="col-span-5">
                                        <label className="block text-xs text-muted-foreground mb-1">{t("productDescription")}</label>
                                        <select
                                            value={line.product_id || ""}
                                            onChange={e => setLine(i, "product_id" as any, e.target.value || null)}
                                            className="w-full bg-card border border-border text-foreground text-xs rounded-lg px-2 py-2 focus:outline-none focus:border-primary mb-1"
                                        >
                                            <option value="">{t("orderSelectProduct")}</option>
                                            {products.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                                        </select>
                                        <input
                                            type="text" placeholder={t("descriptionLabel")} value={line.description}
                                            onChange={e => setLine(i, "description", e.target.value)}
                                            className="w-full bg-card border border-border text-foreground text-xs rounded-lg px-2 py-2 focus:outline-none focus:border-primary"
                                        />
                                    </div>
                                    <div className="col-span-2">
                                        <label className="block text-xs text-muted-foreground mb-1">{t("orderQtyShort")}</label>
                                        <input
                                            type="number" min={0.01} step={0.01} value={line.quantity}
                                            onChange={e => setLine(i, "quantity", parseFloat(e.target.value) || 0)}
                                            className="w-full bg-card border border-border text-foreground text-xs rounded-lg px-2 py-2 focus:outline-none focus:border-primary"
                                        />
                                    </div>
                                    <div className="col-span-2">
                                        <label className="block text-xs text-muted-foreground mb-1">{t("orderPrice")}</label>
                                        <input
                                            type="number" min={0} step={0.01} value={line.unit_price}
                                            onChange={e => setLine(i, "unit_price", parseFloat(e.target.value) || 0)}
                                            className="w-full bg-card border border-border text-foreground text-xs rounded-lg px-2 py-2 focus:outline-none focus:border-primary"
                                        />
                                    </div>
                                    <div className="col-span-2">
                                        <label className="block text-xs text-muted-foreground mb-1">{t("vatPercent")}</label>
                                        <select
                                            value={line.tax_percentage}
                                            onChange={e => setLine(i, "tax_percentage", parseFloat(e.target.value))}
                                            className="w-full bg-card border border-border text-foreground text-xs rounded-lg px-2 py-2 focus:outline-none focus:border-primary"
                                        >
                                            {[0, 4, 10, 21].map(v => <option key={v} value={v}>{v}%</option>)}
                                        </select>
                                    </div>
                                    <div className="col-span-1 flex items-end justify-end">
                                        <button type="button" onClick={() => removeLine(i)} disabled={form.lines.length === 1} className="p-2 rounded-lg hover:bg-rose-500/10 text-muted-foreground hover:text-rose-400 transition-colors disabled:opacity-30" aria-label="Eliminar línea">
                                            <X className="w-3.5 h-3.5" aria-hidden="true" />
                                        </button>
                                    </div>
                                    <div className="col-span-12 text-right text-xs text-muted-foreground">
                                        {t("orderLineTotal")}: <span className="text-foreground font-mono">{fmt(lineTotal(line))}</span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    <div className="bg-muted rounded-xl p-4 flex items-center justify-between">
                        <span className="text-sm text-muted-foreground">{t("orderTotal")}</span>
                        <span className="text-xl font-bold text-foreground">{fmt(orderTotal)}</span>
                    </div>

                    <div>
                        <label className="block text-xs text-muted-foreground mb-1.5 font-medium">{t("orderInternalNotes")}</label>
                        <textarea
                            value={form.notes} rows={2}
                            onChange={e => setForm((f: FormType) => ({ ...f, notes: e.target.value }))}
                            className="w-full bg-card border border-border text-foreground text-sm rounded-xl px-3 py-2.5 focus:outline-none focus:border-primary transition-colors resize-none"
                            placeholder={t("orderNotesPlaceholder")}
                        />
                    </div>

                    <div className="flex gap-3">
                        <button type="button" onClick={onClose} className="flex-1 py-2.5 rounded-xl border border-border text-muted-foreground text-sm hover:bg-accent/50 transition-colors">
                            {tc("cancel")}
                        </button>
                        <button type="submit" disabled={saving} className="flex-1 py-2.5 rounded-xl bg-primary hover:bg-primary text-foreground text-sm font-medium transition-colors disabled:opacity-50 flex items-center justify-center gap-2">
                            {saving && <Loader2 className="w-4 h-4 animate-spin" />}
                            {t("createOrder")}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
