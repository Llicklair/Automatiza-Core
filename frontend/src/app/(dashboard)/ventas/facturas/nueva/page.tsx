"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { api, Client, Product, InvoiceLine } from "@/lib/api";
import { ArrowLeft, Plus, Trash2, Loader2, FileText } from "lucide-react";
import { useToastStore } from "@/stores/toast";
import { useTranslations } from "next-intl";

const today = () => new Date().toISOString().slice(0, 10);
const in30 = () => {
    const d = new Date();
    d.setDate(d.getDate() + 30);
    return d.toISOString().slice(0, 10);
};

function emptyLine(): InvoiceLine & { _key: number } {
    return { _key: Date.now(), description: "", quantity: 1, unit_price: 0, discount_percentage: 0, tax_percentage: 21 };
}

function NuevaFacturaContent() {
    const t = useTranslations("ventas");
    const tc = useTranslations("common");
    const toast = useToastStore();
    const router = useRouter();
    const searchParams = useSearchParams();
    const preClientId = searchParams.get("client_id") || "";
    const duplicateId = searchParams.get("duplicate_id") || "";

    const [clients, setClients] = useState<Client[]>([]);
    const [products, setProducts] = useState<Product[]>([]);
    const [clientId, setClientId] = useState(preClientId);
    const [invoiceNumber, setInvoiceNumber] = useState("");
    const [date, setDate] = useState(today());
    const [dueDate, setDueDate] = useState(in30());
    const [notes, setNotes] = useState("");
    const [lines, setLines] = useState<(InvoiceLine & { _key: number })[]>([emptyLine()]);
    const [submitting, setSubmitting] = useState(false);

    useEffect(() => {
        Promise.all([api.erp.clients.list({ limit: 200 }), api.erp.products.list({ limit: 200 })])
            .then(([c, p]) => { setClients(c); setProducts(p); });
    }, []);

    useEffect(() => {
        if (!duplicateId) return;
        api.erp.invoices.get(duplicateId).then((inv: any) => {
            if (inv.client_id) setClientId(inv.client_id);
            if (inv.notes) setNotes(inv.notes);
            if (inv.lines && inv.lines.length > 0) {
                setLines(inv.lines.map((l: any) => ({
                    _key: Date.now() + Math.random(),
                    description: l.description || "",
                    quantity: l.quantity ?? 1,
                    unit_price: l.unit_price ?? 0,
                    discount_percentage: l.discount_percentage ?? 0,
                    tax_percentage: l.tax_percentage ?? 21,
                    product_id: l.product_id,
                })));
            }
        }).catch(() => {
            toast.error("No se pudo cargar la factura para duplicar");
        });
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [duplicateId]);

    const addLine = () => setLines(prev => [...prev, emptyLine()]);
    const removeLine = (key: number) => setLines(prev => prev.filter(l => l._key !== key));
    const updateLine = (key: number, field: keyof InvoiceLine, value: string | number) => {
        setLines(prev => prev.map(l => l._key === key ? { ...l, [field]: value } : l));
    };
    const fillFromProduct = (key: number, productId: string) => {
        const p = products.find(p => p.id === productId);
        if (!p) return;
        setLines(prev => prev.map(l => l._key === key ? {
            ...l, product_id: p.id, description: p.name, unit_price: p.price, tax_percentage: p.tax_percentage
        } : l));
    };

    const calcLine = (l: InvoiceLine) => {
        const base = Number(l.quantity) * Number(l.unit_price) * (1 - Number(l.discount_percentage) / 100);
        const tax = base * (Number(l.tax_percentage) / 100);
        return { base, tax, total: base + tax };
    };
    const totals = lines.reduce((acc, l) => {
        const c = calcLine(l);
        return { base: acc.base + c.base, tax: acc.tax + c.tax, total: acc.total + c.total };
    }, { base: 0, tax: 0, total: 0 });

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!clientId) { toast.warning("Selecciona un cliente"); return; }
        if (lines.every(l => !l.description.trim())) { toast.warning("Añade al menos una línea"); return; }
        setSubmitting(true);
        try {
            const payload: any = {
                invoice_number: invoiceNumber || null,
                date: new Date(date).toISOString(),
                due_date: dueDate ? new Date(dueDate).toISOString() : null,
                status: "draft",
                invoice_type: "issued",
                notes: notes || null,
                lines: lines.filter(l => l.description.trim()).map(({ _key, ...l }) => ({
                    ...l,
                    quantity: Number(l.quantity),
                    unit_price: Number(l.unit_price),
                    discount_percentage: Number(l.discount_percentage),
                    tax_percentage: Number(l.tax_percentage),
                })),
            };
            const inv = await api.erp.invoices.create(clientId, payload);
            router.push(`/ventas/facturas/${inv.id}`);
        } catch (e: any) {
            toast.error(e?.message || "Error creando factura");
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="p-8 max-w-5xl mx-auto space-y-8">
            <div className="flex items-center gap-4">
                <Link href="/ventas/facturas" className="p-2 -ml-2 rounded-xl text-muted-foreground hover:text-foreground hover:bg-accent/50 transition-colors">
                    <ArrowLeft className="w-5 h-5" />
                </Link>
                <div>
                    <h1 className="text-3xl font-bold text-foreground">{t("newInvoice")}</h1>
                    <p className="text-muted-foreground text-sm">{t("newInvoiceDescription")}</p>
                </div>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6">
                {/* Cabecera */}
                <div className="bg-card border border-border rounded-2xl p-6 grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="sm:col-span-2">
                        <label className="block text-xs font-medium text-muted-foreground mb-1.5">{t("client")} *</label>
                        <select
                            value={clientId}
                            onChange={e => setClientId(e.target.value)}
                            required
                            className="w-full bg-muted border border-border rounded-xl px-3 py-2.5 text-foreground text-sm outline-none focus:border-primary/20"
                        >
                            <option value="">Seleccionar cliente…</option>
                            {clients.map(c => (
                                <option key={c.id} value={c.id}>{c.name}{c.nif ? ` (${c.nif})` : ""}</option>
                            ))}
                        </select>
                    </div>
                    <div>
                        <label className="block text-xs font-medium text-muted-foreground mb-1.5">{t("invoiceNumber")}</label>
                        <input
                            type="text"
                            value={invoiceNumber}
                            onChange={e => setInvoiceNumber(e.target.value)}
                            placeholder="Ej: F-2024-001 (opcional)"
                            className="w-full bg-muted border border-border rounded-xl px-3 py-2.5 text-foreground text-sm outline-none focus:border-primary/20"
                        />
                    </div>
                    <div>{/* spacer */}</div>
                    <div>
                        <label className="block text-xs font-medium text-muted-foreground mb-1.5">{t("issueDate")} *</label>
                        <input
                            type="date"
                            value={date}
                            onChange={e => setDate(e.target.value)}
                            required
                            className="w-full bg-muted border border-border rounded-xl px-3 py-2.5 text-foreground text-sm outline-none focus:border-primary/20"
                        />
                    </div>
                    <div>
                        <label className="block text-xs font-medium text-muted-foreground mb-1.5">{t("dueDate")}</label>
                        <input
                            type="date"
                            value={dueDate}
                            onChange={e => setDueDate(e.target.value)}
                            className="w-full bg-muted border border-border rounded-xl px-3 py-2.5 text-foreground text-sm outline-none focus:border-primary/20"
                        />
                    </div>
                    <div className="sm:col-span-2">
                        <label className="block text-xs font-medium text-muted-foreground mb-1.5">{t("internalNotes")}</label>
                        <textarea
                            value={notes}
                            onChange={e => setNotes(e.target.value)}
                            rows={2}
                            placeholder="Observaciones o condiciones de pago..."
                            className="w-full bg-muted border border-border rounded-xl px-3 py-2.5 text-foreground text-sm outline-none focus:border-primary/20 resize-none"
                        />
                    </div>
                </div>

                {/* Líneas */}
                <div className="bg-card border border-border rounded-2xl p-6 space-y-4">
                    <h2 className="text-sm font-semibold text-foreground">{t("invoiceLines")}</h2>
                    <div className="overflow-x-auto">
                        <table className="w-full text-left border-collapse min-w-[700px]">
                            <thead>
                                <tr className="text-xs text-muted-foreground border-b border-border">
                                    <th className="pb-2 font-medium w-40">{t("product")}</th>
                                    <th className="pb-2 font-medium">{t("descriptionLabel")}</th>
                                    <th className="pb-2 font-medium text-right w-20">{t("qty")}</th>
                                    <th className="pb-2 font-medium text-right w-24">{t("unitPrice")}</th>
                                    <th className="pb-2 font-medium text-right w-20">{t("discount")}</th>
                                    <th className="pb-2 font-medium text-right w-20">{t("vat")}</th>
                                    <th className="pb-2 font-medium text-right w-24">{t("total")}</th>
                                    <th className="pb-2 w-8"></th>
                                </tr>
                            </thead>
                            <tbody>
                                {lines.map((line) => {
                                    const { total } = calcLine(line);
                                    return (
                                        <tr key={line._key} className="border-b border-border">
                                            <td className="py-2 pr-2">
                                                <select
                                                    value={line.product_id || ""}
                                                    onChange={e => fillFromProduct(line._key, e.target.value)}
                                                    className="w-full bg-muted border border-border rounded-lg px-2 py-1.5 text-foreground text-xs outline-none"
                                                >
                                                    <option value="">—</option>
                                                    {products.map(p => (
                                                        <option key={p.id} value={p.id}>{p.name}</option>
                                                    ))}
                                                </select>
                                            </td>
                                            <td className="py-2 pr-2">
                                                <input
                                                    type="text"
                                                    value={line.description}
                                                    onChange={e => updateLine(line._key, "description", e.target.value)}
                                                    placeholder="Descripción del servicio/producto"
                                                    className="w-full bg-muted border border-border rounded-lg px-2 py-1.5 text-foreground text-xs outline-none focus:border-primary/20"
                                                />
                                            </td>
                                            <td className="py-2 pr-2">
                                                <input
                                                    type="number"
                                                    min="0"
                                                    step="0.01"
                                                    value={line.quantity}
                                                    onChange={e => updateLine(line._key, "quantity", e.target.value)}
                                                    className="w-full bg-muted border border-border rounded-lg px-2 py-1.5 text-foreground text-xs text-right outline-none focus:border-primary/20"
                                                />
                                            </td>
                                            <td className="py-2 pr-2">
                                                <input
                                                    type="number"
                                                    min="0"
                                                    step="0.01"
                                                    value={line.unit_price}
                                                    onChange={e => updateLine(line._key, "unit_price", e.target.value)}
                                                    className="w-full bg-muted border border-border rounded-lg px-2 py-1.5 text-foreground text-xs text-right outline-none focus:border-primary/20"
                                                />
                                            </td>
                                            <td className="py-2 pr-2">
                                                <input
                                                    type="number"
                                                    min="0"
                                                    max="100"
                                                    step="0.01"
                                                    value={line.discount_percentage}
                                                    onChange={e => updateLine(line._key, "discount_percentage", e.target.value)}
                                                    className="w-full bg-muted border border-border rounded-lg px-2 py-1.5 text-foreground text-xs text-right outline-none focus:border-primary/20"
                                                />
                                            </td>
                                            <td className="py-2 pr-2">
                                                <input
                                                    type="number"
                                                    min="0"
                                                    max="100"
                                                    step="0.01"
                                                    value={line.tax_percentage}
                                                    onChange={e => updateLine(line._key, "tax_percentage", e.target.value)}
                                                    className="w-full bg-muted border border-border rounded-lg px-2 py-1.5 text-foreground text-xs text-right outline-none focus:border-primary/20"
                                                />
                                            </td>
                                            <td className="py-2 pr-2 text-right text-sm text-foreground font-medium tabular-nums whitespace-nowrap">
                                                {total.toLocaleString("es-ES", { minimumFractionDigits: 2 })}€
                                            </td>
                                            <td className="py-2">
                                                <button
                                                    type="button"
                                                    onClick={() => removeLine(line._key)}
                                                    disabled={lines.length === 1}
                                                    className="p-1 text-muted-foreground hover:text-red-400 disabled:opacity-30 transition-colors"
                                                >
                                                    <Trash2 className="w-4 h-4" />
                                                </button>
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                    <button
                        type="button"
                        onClick={addLine}
                        className="inline-flex items-center gap-2 text-sm text-primary hover:text-primary transition-colors"
                    >
                        <Plus className="w-4 h-4" />
                        Añadir línea
                    </button>
                </div>

                {/* Totales + submit */}
                <div className="flex flex-col sm:flex-row items-start sm:items-end justify-between gap-6">
                    <div className="bg-card border border-border rounded-2xl p-5 w-full sm:w-72 space-y-2 text-sm">
                        <div className="flex justify-between text-muted-foreground">
                            <span>{t("subtotal")}</span>
                            <span className="tabular-nums">{totals.base.toLocaleString("es-ES", { minimumFractionDigits: 2 })}€</span>
                        </div>
                        <div className="flex justify-between text-muted-foreground">
                            <span>{t("totalVat")}</span>
                            <span className="tabular-nums">{totals.tax.toLocaleString("es-ES", { minimumFractionDigits: 2 })}€</span>
                        </div>
                        <div className="flex justify-between text-foreground font-bold border-t border-border pt-2">
                            <span>{t("total")}</span>
                            <span className="tabular-nums">{totals.total.toLocaleString("es-ES", { minimumFractionDigits: 2 })}€</span>
                        </div>
                    </div>
                    <div className="flex gap-3">
                        <Link
                            href="/ventas/facturas"
                            className="inline-flex items-center gap-2 bg-muted hover:bg-accent text-foreground px-5 py-2.5 rounded-xl transition font-medium text-sm"
                        >
                            {tc("cancel")}
                        </Link>
                        <button
                            type="submit"
                            disabled={submitting}
                            className="inline-flex items-center gap-2 bg-primary hover:bg-primary disabled:opacity-50 text-foreground px-6 py-2.5 rounded-xl transition font-medium text-sm shadow-lg shadow-primary/20"
                        >
                            {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileText className="w-4 h-4" />}
                            {t("createInvoice")}
                        </button>
                    </div>
                </div>
            </form>
        </div>
    );
}

export default function NuevaFacturaPage() {
    return (
        <Suspense fallback={<div className="p-8 text-muted-foreground">Cargando...</div>}>
            <NuevaFacturaContent />
        </Suspense>
    );
}
