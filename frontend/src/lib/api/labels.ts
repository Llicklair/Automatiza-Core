/** Impresión de etiquetas con código de barras (devuelve el PDF como Blob). */
import { fetchBlob } from "./client";

export interface LabelItem {
    product_id: string;
    copies: number;
}

export const labels = {
    pdf: (items: LabelItem[], showPrice: boolean) =>
        fetchBlob("/api/v1/inventory/labels/pdf", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ items, show_price: showPrice }),
        }),
};
