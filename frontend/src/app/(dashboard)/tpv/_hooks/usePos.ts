"use client";

import { useCallback, useEffect, useState } from "react";
import { api, type PosSession, type Product } from "@/lib/api";
import { useToastStore } from "@/stores/toast";
import { logError } from "@/lib/logger";

export function usePos() {
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
            toast.error(e?.message || "Error abriendo sesión");
        } finally {
            setBusy(false);
        }
    }, [toast]);

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
                    toast.error(`No se encontró producto para "${code}"`);
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
                toast.error(e?.message || "Error añadiendo producto");
            } finally {
                setBusy(false);
            }
        },
        [session, toast],
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
                toast.error(e?.message || "Error añadiendo línea");
            } finally {
                setBusy(false);
            }
        },
        [session, toast],
    );

    const updateLineQuantity = useCallback(
        async (lineId: string, quantity: number) => {
            if (!session || quantity <= 0) return;
            setBusy(true);
            try {
                const updated = await api.pos.updateLine(session.id, lineId, quantity);
                setSession(updated);
            } catch (e: any) {
                toast.error(e?.message || "Error actualizando cantidad");
            } finally {
                setBusy(false);
            }
        },
        [session, toast],
    );

    const removeLine = useCallback(
        async (lineId: string) => {
            if (!session) return;
            setBusy(true);
            try {
                const updated = await api.pos.removeLine(session.id, lineId);
                setSession(updated);
            } catch (e: any) {
                toast.error(e?.message || "Error eliminando línea");
            } finally {
                setBusy(false);
            }
        },
        [session, toast],
    );

    const checkout = useCallback(
        async (payment_method: "cash" | "card") => {
            if (!session) return;
            setBusy(true);
            try {
                const closed = await api.pos.checkout(session.id, { payment_method });
                toast.success(
                    `Cobro registrado · ${closed.amount_total.toFixed(2)} €`,
                );
                setCheckoutOpen(false);
                setSession(null);
            } catch (e: any) {
                toast.error(e?.message || "Error al cobrar");
            } finally {
                setBusy(false);
            }
        },
        [session, toast],
    );

    const cancelSession = useCallback(async () => {
        if (!session) return;
        setBusy(true);
        try {
            await api.pos.cancel(session.id);
            toast.success("Sesión cancelada");
            setSession(null);
        } catch (e: any) {
            toast.error(e?.message || "Error cancelando");
        } finally {
            setBusy(false);
        }
    }, [session, toast]);

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
