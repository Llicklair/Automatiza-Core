"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api, Client, Product, InvoiceLine } from "@/lib/api";
import { Plus, Trash2, Save, FileText, Calendar, Building2, UserCircle } from "lucide-react";
import { useToastStore } from "@/stores/toast";

export default function InvoiceBuilder({ preselectedClientId }: { preselectedClientId?: string }) {
    const toast = useToastStore();
    const router = useRouter();
    const [clients, setClients] = useState<Client[]>([]);
    const [products, setProducts] = useState<Product[]>([]);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);

    // Invoice state
    const [clientId, setClientId] = useState<string>(preselectedClientId || "");
    const [invoiceDate, setInvoiceDate] = useState(new Date().toISOString().split('T')[0]);
    const [dueDate, setDueDate] = useState("");
    const [notes, setNotes] = useState("");

    // Lines state
    const [lines, setLines] = useState<Partial<InvoiceLine>[]>([
        { description: "", quantity: 1, unit_price: 0, tax_percentage: 21, discount_percentage: 0 }
    ]);

    useEffect(() => {
        Promise.allSettled([
            api.erp.clients.list(),
            api.erp.products.list()
        ]).then(([clientsRes, productsRes]) => {
            if (clientsRes.status === "fulfilled") {
                setClients(clientsRes.value);
            } else {
                console.error("Error loading clients", clientsRes.reason);
            }
            if (productsRes.status === "fulfilled") {
                setProducts(productsRes.value);
            } else {
                console.error("Error loading products", productsRes.reason);
            }
            setLoading(false);
        });
    }, []);

    const addLine = () => {
        setLines([...lines, { description: "", quantity: 1, unit_price: 0, tax_percentage: 21, discount_percentage: 0 }]);
    };

    const removeLine = (index: number) => {
        setLines(lines.filter((_, i) => i !== index));
    };

    const updateLine = (index: number, field: keyof InvoiceLine, value: any) => {
        const newLines = [...lines];
        newLines[index] = { ...newLines[index], [field]: value };

        // Auto-fill from product
        if (field === 'product_id' && value) {
            const product = products.find(p => p.id === value);
            if (product) {
                newLines[index].description = product.name;
                newLines[index].unit_price = product.price;
                newLines[index].tax_percentage = product.tax_percentage;
            }
        }

        setLines(newLines);
    };

    const calculateTotals = () => {
        let base = 0;
        let tax = 0;

        lines.forEach(line => {
            const q = Number(line.quantity) || 0;
            const up = Number(line.unit_price) || 0;
            const d = Number(line.discount_percentage) || 0;
            const t = Number(line.tax_percentage) || 0;

            const lineBase = (q * up) * (1 - d / 100);
            const lineTax = lineBase * (t / 100);

            base += lineBase;
            tax += lineTax;
        });

        return { base, tax, total: base + tax };
    };

    const { base, tax, total } = calculateTotals();

    const handleSave = async () => {
        if (!clientId) { toast.warning("Selecciona un cliente"); return; }
        if (lines.length === 0) { toast.warning("Añade al menos una línea"); return; }
        if (lines.some(l => !l.description)) { toast.warning("Todas las líneas deben tener descripción"); return; }

        try {
            setSaving(true);
            await api.erp.invoices.create(clientId, {
                date: new Date(invoiceDate).toISOString(),
                due_date: dueDate ? new Date(dueDate).toISOString() : null,
                notes,
                lines: lines as InvoiceLine[],
                invoice_type: "issued",
                status: "draft"
            });
            toast.success("Factura creada con éxito!");
            router.push("/ventas/facturas");
        } catch (err: any) {
            toast.error(err.message || "Error al crear factura");
        } finally {
            setSaving(false);
        }
    };

    if (loading) {
        return <div className="p-8 text-zinc-400">Cargando datos...</div>;
    }

    return (
        <div className="bg-zinc-900/50 border border-white/5 rounded-2xl p-6 backdrop-blur-xl">
            {/* Header / Meta */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8 pb-8 border-b border-white/5">
                <div>
                    <label className="block text-sm font-medium text-zinc-400 mb-2">Cliente *</label>
                    <select
                        className="w-full bg-[#18181b] border border-[#27272a] rounded-xl px-4 py-3 text-white outline-none focus:border-indigo-500 transition-colors"
                        value={clientId}
                        onChange={(e) => setClientId(e.target.value)}
                    >
                        <option value="">Seleccionar cliente...</option>
                        {clients.map(c => (
                            <option key={c.id} value={c.id}>{c.name}</option>
                        ))}
                    </select>
                </div>

                <div>
                    <label className="block text-sm font-medium text-zinc-400 mb-2">Fecha de Emisión *</label>
                    <input
                        type="date"
                        className="w-full bg-[#18181b] border border-[#27272a] rounded-xl px-4 py-3 text-white outline-none focus:border-indigo-500 transition-colors"
                        value={invoiceDate}
                        onChange={(e) => setInvoiceDate(e.target.value)}
                    />
                </div>

                <div>
                    <label className="block text-sm font-medium text-zinc-400 mb-2">Fecha de Vencimiento</label>
                    <input
                        type="date"
                        className="w-full bg-[#18181b] border border-[#27272a] rounded-xl px-4 py-3 text-white outline-none focus:border-indigo-500 transition-colors"
                        value={dueDate}
                        onChange={(e) => setDueDate(e.target.value)}
                    />
                </div>
            </div>

            {/* Lines Table */}
            <div className="mb-8">
                <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-medium text-white flex items-center gap-2">
                        <FileText className="w-5 h-5 text-indigo-400" />
                        Detalle de Factura
                    </h3>
                </div>

                <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                        <thead>
                            <tr className="border-b border-white/5 text-sm text-zinc-400">
                                <th className="pb-3 font-medium w-48">Catálogo</th>
                                <th className="pb-3 font-medium min-w-[200px]">Descripción *</th>
                                <th className="pb-3 font-medium w-24">Cant.</th>
                                <th className="pb-3 font-medium w-32">Precio (€)</th>
                                <th className="pb-3 font-medium w-24">Desc. (%)</th>
                                <th className="pb-3 font-medium w-24">IVA (%)</th>
                                <th className="pb-3 font-medium w-32 text-right">Total (€)</th>
                                <th className="pb-3 w-10"></th>
                            </tr>
                        </thead>
                        <tbody className="text-sm">
                            {lines.map((line, idx) => {
                                const q = Number(line.quantity) || 0;
                                const up = Number(line.unit_price) || 0;
                                const d = Number(line.discount_percentage) || 0;
                                const t = Number(line.tax_percentage) || 0;
                                const lineBase = (q * up) * (1 - d / 100);
                                const lineTotal = lineBase * (1 + t / 100);

                                return (
                                    <tr key={idx} className="border-b border-white/5 group">
                                        <td className="py-3 pr-2">
                                            <select
                                                className="w-full bg-[#18181b] border border-[#27272a] rounded-lg px-2 py-1.5 text-white outline-none focus:border-indigo-500 transition-colors"
                                                value={line.product_id || ""}
                                                onChange={(e) => updateLine(idx, 'product_id', e.target.value || null)}
                                            >
                                                <option value="">Libre</option>
                                                {products.map(p => (
                                                    <option key={p.id} value={p.id}>{p.name}</option>
                                                ))}
                                            </select>
                                        </td>
                                        <td className="py-3 px-2">
                                            <input
                                                type="text"
                                                className="w-full bg-[#18181b] border border-[#27272a] rounded-lg px-2 py-1.5 text-white outline-none focus:border-indigo-500 transition-colors"
                                                placeholder="Ej. Diseño Logo"
                                                value={line.description}
                                                onChange={(e) => updateLine(idx, 'description', e.target.value)}
                                            />
                                        </td>
                                        <td className="py-3 px-2">
                                            <input
                                                type="number"
                                                min="1"
                                                step="0.01"
                                                className="w-full bg-[#18181b] border border-[#27272a] rounded-lg px-2 py-1.5 text-white outline-none focus:border-indigo-500"
                                                value={line.quantity}
                                                onChange={(e) => updateLine(idx, 'quantity', parseFloat(e.target.value) || 0)}
                                            />
                                        </td>
                                        <td className="py-3 px-2">
                                            <input
                                                type="number"
                                                min="0"
                                                step="0.01"
                                                className="w-full bg-[#18181b] border border-[#27272a] rounded-lg px-2 py-1.5 text-white outline-none focus:border-indigo-500"
                                                value={line.unit_price}
                                                onChange={(e) => updateLine(idx, 'unit_price', parseFloat(e.target.value) || 0)}
                                            />
                                        </td>
                                        <td className="py-3 px-2">
                                            <input
                                                type="number"
                                                min="0"
                                                max="100"
                                                step="1"
                                                className="w-full bg-[#18181b] border border-[#27272a] rounded-lg px-2 py-1.5 text-white outline-none focus:border-indigo-500"
                                                value={line.discount_percentage}
                                                onChange={(e) => updateLine(idx, 'discount_percentage', parseFloat(e.target.value) || 0)}
                                            />
                                        </td>
                                        <td className="py-3 px-2">
                                            <input
                                                type="number"
                                                min="0"
                                                max="100"
                                                step="0.1"
                                                className="w-full bg-[#18181b] border border-[#27272a] rounded-lg px-2 py-1.5 text-white outline-none focus:border-indigo-500"
                                                value={line.tax_percentage}
                                                onChange={(e) => updateLine(idx, 'tax_percentage', parseFloat(e.target.value) || 0)}
                                            />
                                        </td>
                                        <td className="py-3 px-2 text-right font-medium text-zinc-300">
                                            {lineTotal.toLocaleString('es-ES', { minimumFractionDigits: 2 })}€
                                        </td>
                                        <td className="py-3 pl-2 text-right">
                                            <button
                                                onClick={() => removeLine(idx)}
                                                disabled={lines.length === 1}
                                                className="p-1.5 text-zinc-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors disabled:opacity-30"
                                                title="Eliminar línea"
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

                <div className="mt-4">
                    <button
                        onClick={addLine}
                        className="flex items-center gap-2 text-sm font-medium text-indigo-400 hover:text-indigo-300 px-3 py-1.5 rounded-lg hover:bg-indigo-500/10 transition-colors"
                    >
                        <Plus className="w-4 h-4" />
                        Añadir Línea
                    </button>
                </div>
            </div>

            {/* Footer / Totales */}
            <div className="flex flex-col md:flex-row gap-8 justify-between items-end border-t border-white/5 pt-8">
                <div className="w-full md:w-1/2">
                    <label className="block text-sm font-medium text-zinc-400 mb-2">Notas / Condiciones de la factura</label>
                    <textarea
                        className="w-full bg-[#18181b] border border-[#27272a] rounded-xl px-4 py-3 text-white outline-none focus:border-indigo-500 transition-colors min-h-[100px]"
                        placeholder="Ej. Forma de pago: Transferencia a ESXX XXXX... Pago a 30 días."
                        value={notes}
                        onChange={(e) => setNotes(e.target.value)}
                    />
                </div>

                <div className="w-full md:w-80 bg-[#18181b] rounded-2xl p-6 border border-[#27272a]">
                    <div className="space-y-3 font-medium text-sm">
                        <div className="flex justify-between text-zinc-400">
                            <span>Base Imponible</span>
                            <span>{base.toLocaleString('es-ES', { minimumFractionDigits: 2 })}€</span>
                        </div>
                        <div className="flex justify-between text-zinc-400">
                            <span>Impuestos</span>
                            <span>{tax.toLocaleString('es-ES', { minimumFractionDigits: 2 })}€</span>
                        </div>
                        <div className="pt-3 border-t border-[#27272a] flex justify-between text-lg text-white">
                            <span>Total Factura</span>
                            <span>{total.toLocaleString('es-ES', { minimumFractionDigits: 2 })}€</span>
                        </div>
                    </div>

                    <button
                        onClick={handleSave}
                        disabled={saving}
                        className="w-full flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white py-3 rounded-xl mt-6 transition-all shadow-lg font-semibold disabled:opacity-50"
                    >
                        {saving ? (
                            <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                        ) : (
                            <>
                                <Save className="w-5 h-5" />
                                Guardar Factura
                            </>
                        )}
                    </button>
                </div>
            </div>
        </div>
    );
}
