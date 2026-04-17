import type { Product, InvoiceLine } from "@/lib/api";
import { Plus, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { calcLine } from "../_hooks/useNuevaFactura";

interface InvoiceLinesTableProps {
    lines: (InvoiceLine & { _key: number })[];
    products: Product[];
    onAddLine: () => void;
    onRemoveLine: (key: number) => void;
    onUpdateLine: (key: number, field: keyof InvoiceLine, value: string | number) => void;
    onFillFromProduct: (key: number, productId: string) => void;
}

export default function InvoiceLinesTable({
    lines, products, onAddLine, onRemoveLine, onUpdateLine, onFillFromProduct,
}: InvoiceLinesTableProps) {
    const t = useTranslations("ventas");

    return (
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
                                            onChange={e => onFillFromProduct(line._key, e.target.value)}
                                            className="w-full bg-muted border border-border rounded-lg px-2 py-1.5 text-foreground text-xs outline-none"
                                        >
                                            <option value="">&mdash;</option>
                                            {products.map(p => (
                                                <option key={p.id} value={p.id}>{p.name}</option>
                                            ))}
                                        </select>
                                    </td>
                                    <td className="py-2 pr-2">
                                        <input
                                            type="text"
                                            value={line.description}
                                            onChange={e => onUpdateLine(line._key, "description", e.target.value)}
                                            placeholder="Descripcion del servicio/producto"
                                            className="w-full bg-muted border border-border rounded-lg px-2 py-1.5 text-foreground text-xs outline-none focus:border-primary/20"
                                        />
                                    </td>
                                    <td className="py-2 pr-2">
                                        <input type="number" min="0" step="0.01" value={line.quantity}
                                            onChange={e => onUpdateLine(line._key, "quantity", e.target.value)}
                                            className="w-full bg-muted border border-border rounded-lg px-2 py-1.5 text-foreground text-xs text-right outline-none focus:border-primary/20" />
                                    </td>
                                    <td className="py-2 pr-2">
                                        <input type="number" min="0" step="0.01" value={line.unit_price}
                                            onChange={e => onUpdateLine(line._key, "unit_price", e.target.value)}
                                            className="w-full bg-muted border border-border rounded-lg px-2 py-1.5 text-foreground text-xs text-right outline-none focus:border-primary/20" />
                                    </td>
                                    <td className="py-2 pr-2">
                                        <input type="number" min="0" max="100" step="0.01" value={line.discount_percentage}
                                            onChange={e => onUpdateLine(line._key, "discount_percentage", e.target.value)}
                                            className="w-full bg-muted border border-border rounded-lg px-2 py-1.5 text-foreground text-xs text-right outline-none focus:border-primary/20" />
                                    </td>
                                    <td className="py-2 pr-2">
                                        <input type="number" min="0" max="100" step="0.01" value={line.tax_percentage}
                                            onChange={e => onUpdateLine(line._key, "tax_percentage", e.target.value)}
                                            className="w-full bg-muted border border-border rounded-lg px-2 py-1.5 text-foreground text-xs text-right outline-none focus:border-primary/20" />
                                    </td>
                                    <td className="py-2 pr-2 text-right text-sm text-foreground font-medium tabular-nums whitespace-nowrap">
                                        {total.toLocaleString("es-ES", { minimumFractionDigits: 2 })}&euro;
                                    </td>
                                    <td className="py-2">
                                        <button type="button" onClick={() => onRemoveLine(line._key)} disabled={lines.length === 1}
                                            className="p-1 text-muted-foreground hover:text-red-400 disabled:opacity-30 transition-colors">
                                            <Trash2 className="w-4 h-4" />
                                        </button>
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>
            <button type="button" onClick={onAddLine}
                className="inline-flex items-center gap-2 text-sm text-primary hover:text-primary transition-colors">
                <Plus className="w-4 h-4" />
                Anadir linea
            </button>
        </div>
    );
}
