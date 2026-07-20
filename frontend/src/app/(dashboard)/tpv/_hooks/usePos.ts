"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { api, type PosSession, type Product } from "@/lib/api";
import { useToastStore } from "@/stores/toast";
import { logError } from "@/lib/logger";

export function usePos() {
    const t = useTranslations("tpv");
    const toast = useToastStore();
    const [session, setSession] = useState<PosSession | null>(null);
    const [loading, setLoading] = useState(true);
    const [busy, setBusy] = useState(false);
    const [checkoutOpen, setCheckoutOpen] = useState(false);

    const loadCurrent = useCallback(async () => {
        setLoading(true);
        try {
            const data = await api.pos.current();
            setSession(data);
        } catch (e: any) {
            logError("tpv/usePos.loadCurrent", e);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadCurrent();
    }, [loadCurrent]);

    const openSession = useCallback(async () => {
        setBusy(true);
        try {
            const s = await api.pos.open();
            setSession(s);
        } catch (e: any) {
            toast.error(e?.message || t("toast.openError"));
        } finally {
            setBusy(false);
        }
    }, [toast, t]);

    const addProductByCode = useCallback(
        async (code: string) => {
            if (!session) return;
            setBusy(true);
            try {
                // 1) Lookup directo por barcode
                let product: Product | null = null;
                try {
                    product = await api.erp.products.byBarcode(code);
                } catch {
                    // 2) Fallback: si no encuentra por barcode, buscar como SKU
                    const list = await api.erp.products.list({ q: code, limit: 5 });
                    product =
                        list.find((p) => p.sku === code || p.barcode === code) ||
                        list[0] ||
                        null;
                }
                if (!product) {
                    toast.error(t("toast.productNotFound", { code }));
                    return;
                }
                const existing = session.lines.find((l) => l.product_id === product!.id);
                if (existing) {
                    const updated = await api.pos.updateLine(
                        session.id,
                        existing.id,
                        existing.quantity + 1,
                    );
                    setSession(updated);
                } else {
                    const updated = await api.pos.addLine(session.id, {
                        product_id: product.id,
                        quantity: 1,
                    });
                    setSession(updated);
                }
            } catch (e: any) {
                toast.error(e?.message || t("toast.addProductError"));
            } finally {
                setBusy(false);
            }
        },
        [session, toast, t],
    );

    const addCustomLine = useCallback(
        async (description: string, unit_price: number, quantity = 1) => {
            if (!session) return;
            setBusy(true);
            try {
                const updated = await api.pos.addLine(session.id, {
                    description,
                    unit_price,
                    quantity,
                    tax_percentage: 21,
                });
                setSession(updated);
            } catch (e: any) {
                toast.error(e?.message || t("toast.addLineError"));
            } finally {
                setBusy(false);
            }
        },
        [session, toast, t],
    );

    const updateLineQuantity = useCallback(
        async (lineId: string, quantity: number) => {
            if (!session || quantity <= 0) return;
            setBusy(true);
            try {
                const updated = await api.pos.updateLine(session.id, lineId, quantity);
                setSession(updated);
            } catch (e: any) {
                toast.error(e?.message || t("toast.updateQuantityError"));
            } finally {
                setBusy(false);
            }
        },
        [session, toast, t],
    );

    const removeLine = useCallback(
        async (lineId: string) => {
            if (!session) return;
            setBusy(true);
            try {
                const updated = await api.pos.removeLine(session.id, lineId);
                setSession(updated);
            } catch (e: any) {
                toast.error(e?.message || t("toast.removeLineError"));
            } finally {
                setBusy(false);
            }
        },
        [session, toast, t],
    );

    const checkout = useCallback(
        async (payment_method: "cash" | "card") => {
            if (!session) return;
            setBusy(true);
            try {
                const closed = await api.pos.checkout(session.id, { payment_method });
                toast.success(
                    t("toast.checkoutSuccess", { amount: `${closed.amount_total.toFixed(2)} €` }),
                );
                // VeriFactu: cada venta emite su factura simplificada (F2). El cobro
                // ya quedó registrado; si la emisión falla se avisa aparte (es
                // idempotente, reintentar es seguro y no pierde la venta).
                try {
                    const invoice = await api.pos.emitirFactura(closed.id);
                    toast.success(
                        t("toast.facturaEmitida", {
                            number: invoice.invoice_number ?? invoice.id.slice(0, 8),
                        }),
                    );
                } catch (e: any) {
                    logError("tpv/usePos.emitirFactura", e);
                    toast.error(e?.message || t("toast.facturaError"));
                }
                setCheckoutOpen(false);
                setSession(null);
            } catch (e: any) {
                toast.error(e?.message || t("toast.checkoutError"));
            } finally {
                setBusy(false);
            }
        },
        [session, toast, t],
    );

    const cancelSession = useCallback(async () => {
        if (!session) return;
        setBusy(true);
        try {
            await api.pos.cancel(session.id);
            toast.success(t("toast.cancelSuccess"));
            setSession(null);
        } catch (e: any) {
            toast.error(e?.message || t("toast.cancelError"));
        } finally {
            setBusy(false);
        }
    }, [session, toast, t]);

    const subtotal = session
        ? session.lines.reduce(
              (acc, l) => acc + Number(l.quantity) * Number(l.unit_price),
              0,
          )
        : 0;
    const totalWithTax = session
        ? session.lines.reduce((acc, l) => acc + Number(l.total), 0)
        : 0;
    const taxAmount = totalWithTax - subtotal;

    return {
        session,
        loading,
        busy,
        checkoutOpen,
        setCheckoutOpen,
        subtotal,
        taxAmount,
        totalWithTax,
        openSession,
        addProductByCode,
        addCustomLine,
        updateLineQuantity,
        removeLine,
        checkout,
        cancelSession,
        reload: loadCurrent,
    };
}
