"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api, Client, Product, InvoiceLine } from "@/lib/api";
import { useToastStore } from "@/stores/toast";

const today = () => new Date().toISOString().slice(0, 10);
const in30 = () => {
    const d = new Date();
    d.setDate(d.getDate() + 30);
    return d.toISOString().slice(0, 10);
};

export function emptyLine(): InvoiceLine & { _key: number } {
    return { _key: Date.now(), description: "", quantity: 1, unit_price: 0, discount_percentage: 0, tax_percentage: 21 };
}

export function calcLine(l: InvoiceLine) {
    const base = Number(l.quantity) * Number(l.unit_price) * (1 - Number(l.discount_percentage) / 100);
    const tax = base * (Number(l.tax_percentage) / 100);
    return { base, tax, total: base + tax };
}

export function useNuevaFactura() {
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
    const [fiscalRegime, setFiscalRegime] = useState("");
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
        const p = products.find(pr => pr.id === productId);
        if (!p) return;
        setLines(prev => prev.map(l => l._key === key ? {
            ...l, product_id: p.id, description: p.name, unit_price: p.price, tax_percentage: p.tax_percentage
        } : l));
    };

    const totals = lines.reduce((acc, l) => {
        const c = calcLine(l);
        return { base: acc.base + c.base, tax: acc.tax + c.tax, total: acc.total + c.total };
    }, { base: 0, tax: 0, total: 0 });

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!clientId) { toast.warning("Selecciona un cliente"); return; }
        if (lines.every(l => !l.description.trim())) { toast.warning("Anade al menos una linea"); return; }
        setSubmitting(true);
        try {
            const payload: any = {
                invoice_number: invoiceNumber || null,
                date: new Date(date).toISOString(),
                due_date: dueDate ? new Date(dueDate).toISOString() : null,
                status: "draft",
                invoice_type: "issued",
                notes: notes || null,
                fiscal_regime: fiscalRegime || null,
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

    return {
        clients, products, clientId, setClientId,
        invoiceNumber, setInvoiceNumber, date, setDate,
        dueDate, setDueDate, notes, setNotes,
        fiscalRegime, setFiscalRegime,
        lines, submitting, totals,
        addLine, removeLine, updateLine, fillFromProduct, handleSubmit,
    };
}
