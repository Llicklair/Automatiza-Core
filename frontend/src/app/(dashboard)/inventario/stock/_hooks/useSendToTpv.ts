"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { api, type Product } from "@/lib/api";
import { useToastStore } from "@/stores/toast";

/**
 * Manda un producto del stock al carrito del TPV del usuario actual.
 *
 * Flujo mostrador: marcar varios productos desde Inventario → Stock y cobrarlos
 * de una vez en el TPV, sin teclear/escanear cada código. Si no hay sesión de
 * TPV abierta, la abre; si el producto ya está en el carrito, incrementa la
 * cantidad (misma semántica que escanear en el TPV).
 */
export function useSendToTpv() {
    const t = useTranslations("inventario");
    const toast = useToastStore();
    const [sendingId, setSendingId] = useState<string | null>(null);

    const sendToTpv = async (product: Product) => {
        setSendingId(product.id);
        try {
            let session = await api.pos.current();
            if (!session || session.status !== "open") {
                session = await api.pos.open();
            }
            const existing = session.lines.find((l) => l.product_id === product.id);
            if (existing) {
                await api.pos.updateLine(session.id, existing.id, existing.quantity + 1);
            } else {
                await api.pos.addLine(session.id, { product_id: product.id, quantity: 1 });
            }
            toast.success(t("stock.sendToTpvOk", { name: product.name }));
        } catch (e: any) {
            toast.error(e?.message || t("stock.sendToTpvError"));
        } finally {
            setSendingId(null);
        }
    };

    return { sendToTpv, sendingId };
}
