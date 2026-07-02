"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import { api, Quote, Client, Product } from "@/lib/api";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";
import { logError } from "@/lib/logger";
import { useTranslations } from "next-intl";

export interface QuoteLine {
    product_id: string;
    description: string;
    quantity: number;
    unit_price: number;
    tax_percentage: number;
}

const EMPTY_LINE: QuoteLine = { product_id: "", description: "", quantity: 1, unit_price: 0, tax_percentage: 21 };

export const formatCurrency = (val: number) =>
    new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" }).format(val);

export function usePresupuestos() {
    const toastNotif = useToastStore();
    const t = useTranslations("ventas");
    const tc = useTranslations("common");

    const [quotes, setQuotes] = useState<Quote[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);
    const [clients, setClients] = useState<Client[]>([]);
    const [products, setProducts] = useState<Product[]>([]);
    const [selectedClient, setSelectedClient] = useState("");
    const [validUntil, setValidUntil] = useState("");
    const [lines, setLines] = useState<QuoteLine[]>([{ ...EMPTY_LINE }]);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [convertingId, setConvertingId] = useState<string | null>(null);
    const [search, setSearch] = useState("");
    const [expiredOnly, setExpiredOnly] = useState(false);

    const filteredQuotes = useMemo(() => {
        const term = search.trim().toLowerCase();
        const todayStart = new Date().setHours(0, 0, 0, 0);
        // Expirado = venció su valid_until sin resolverse (accepted/rejected ya no son accionables).
        const isExpired = (q: Quote) =>
            !!q.valid_until &&
            (q.status === "draft" || q.status === "sent") &&
            new Date(q.valid_until).getTime() < todayStart;
        return quotes.filter(q =>
            (!expiredOnly || isExpired(q)) &&
            (!term ||
                (q.quote_number ?? "").toLowerCase().includes(term) ||
                (q.client?.name ?? "").toLowerCase().includes(term))
        );
    }, [quotes, search, expiredOnly]);

    const loadData = useCallback(async () => {
        setIsLoading(true);
        try {
            const [quotesRes, clientsRes, prodRes] = await Promise.all([
                api.erp.quotes.list(),
                api.erp.clients.list(),
                api.erp.products.list(),
            ]);
            setQuotes(quotesRes);
            setClients(clientsRes);
            setProducts(prodRes);
        } catch (error) {
            logError("ventas/presupuestos/page", error);
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => { loadData(); }, [loadData]);

    const resetForm = () => {
        setSelectedClient("");
        setValidUntil("");
        setLines([{ ...EMPTY_LINE }]);
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
                lines: lines.map(l => ({ ...l, product_id: l.product_id || null })) as any,
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
        if (!await showConfirm({
            message: t("quoteConvertConfirmDetail", { amount: formatCurrency(q.amount_total), client: q.client?.name ?? t("quoteThisClient") }),
            confirmLabel: tc("confirm"),
            confirmVariant: "primary",
        })) return;
        setConvertingId(q.id);
        try {
            const result = await api.erp.quotes.convertToInvoice(q.id);
            toastNotif.success(t("quoteInvoiceCreatedDetail", { number: result.invoice_number, amount: formatCurrency(result.amount_total) }));
            await loadData();
        } catch (e: any) {
            toastNotif.error(t("errorConvert") + ": " + (e.message || ""));
        } finally {
            setConvertingId(null);
        }
    };

    const handleDelete = async (id: string) => {
        if (!await showConfirm({ message: t("quoteDeleteConfirm"), confirmLabel: tc("delete"), confirmVariant: "danger" })) return;
        try {
            await api.erp.quotes.delete(id);
            setQuotes(prev => prev.filter(q => q.id !== id));
        } catch (e: any) {
            toastNotif.error(t("errorDelete") + ": " + (e.message || ""));
        }
    };

    const handleStatusChange = async (id: string, newStatus: string) => {
        try {
            setQuotes(prev => prev.map(q => q.id === id ? { ...q, status: newStatus } : q));
            await api.erp.quotes.update(id, { status: newStatus });
        } catch (error) {
            logError("ventas/presupuestos/page", error);
            await loadData();
        }
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

    const addLine = () => setLines(prev => [...prev, { ...EMPTY_LINE }]);

    return {
        quotes: filteredQuotes, isLoading, showModal, setShowModal,
        search, setSearch, expiredOnly, setExpiredOnly,
        clients, products,
        selectedClient, setSelectedClient,
        validUntil, setValidUntil,
        lines, isSubmitting, convertingId,
        handleCreate, handleConvert, handleDelete, handleStatusChange,
        updateLine, addLine,
        t, tc,
    };
}
