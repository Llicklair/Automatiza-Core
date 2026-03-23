"use client";

import { useEffect, useState } from "react";
import { api, Invoice } from "@/lib/api";
import { FileText, Plus, Search, Download, Building2, Calendar, AlertTriangle, CheckCircle2, Copy, Trash2 } from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { useToastStore } from "@/stores/toast";
import { useNotificationStore } from "@/stores/notifications";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8080";

function getToken(): string {
    return typeof window !== "undefined" ? (localStorage.getItem("access_token") ?? "") : "";
}

async function downloadInvoicePdf(invoiceId: string, invoiceNumber: string | null) {
    try {
        const res = await fetch(`${API_BASE}/api/v1/invoices/${invoiceId}/pdf`, {
            headers: { Authorization: `Bearer ${getToken()}` },
        });
        if (!res.ok) throw new Error("Error al descargar el PDF");
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `Factura_${invoiceNumber || invoiceId.slice(0, 8)}.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    } catch {
        useToastStore.getState().error("No se pudo descargar el PDF de la factura");
    }
}

// Helper for status badges
function StatusBadge({ status }: { status: string }) {
    switch (status) {
        case 'draft':
            return <span className="px-2.5 py-1 bg-zinc-500/10 text-zinc-400 border border-zinc-500/20 rounded-full text-xs font-medium">Borrador</span>;
        case 'pending':
            return <span className="px-2.5 py-1 bg-amber-500/10 text-amber-400 border border-amber-500/20 rounded-full text-xs font-medium">Pendiente</span>;
        case 'paid':
            return <span className="px-2.5 py-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-full text-xs font-medium">Cobrada</span>;
        case 'overdue':
            return <span className="px-2.5 py-1 bg-red-500/10 text-red-400 border border-red-500/20 rounded-full text-xs font-medium">Vencida</span>;
        default:
            return <span className="px-2.5 py-1 bg-zinc-500/10 text-zinc-400 border border-zinc-500/20 rounded-full text-xs font-medium">{status.toUpperCase()}</span>;
    }
}

export default function FacturasPage() {
    const [invoices, setInvoices] = useState<Invoice[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState("");
    const refreshKey = useNotificationStore((s) => s.refreshKey);

    useEffect(() => {
        api.erp.invoices.list()
            .then(data => setInvoices(data))
            .catch(err => useToastStore.getState().error(err?.message || "Error al cargar facturas"))
            .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [refreshKey]);

    const handleDeleteInvoice = async (id: string) => {
        if (!confirm("¿Eliminar esta factura? Esta acción no se puede deshacer.")) return;
        try {
            await api.erp.invoices.delete(id);
            setInvoices(prev => prev.filter(i => i.id !== id));
            useToastStore.getState().success("Factura eliminada");
        } catch (err: any) {
            useToastStore.getState().error(err?.message || "Error al eliminar factura");
        }
    };

    const filteredInvoices = invoices.filter(inv => {
        const searchLower = searchTerm.toLowerCase();
        const clientNameMatch = inv.client?.name.toLowerCase().includes(searchLower) ?? false;
        const numberMatch = (inv.invoice_number || "Borrador").toLowerCase().includes(searchLower);
        return clientNameMatch || numberMatch;
    });

    return (
        <div className="p-8 max-w-7xl mx-auto space-y-8 relative">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-4xl font-bold tracking-tight text-white mb-2">Facturas de Venta</h1>
                    <p className="text-zinc-400">Gestiona tus ingresos, crea nuevas facturas y controla su estado.</p>
                </div>

                <Link
                    href="/ventas/facturas/nueva"
                    className="inline-flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2.5 rounded-xl transition-all shadow-lg shadow-indigo-500/20 font-medium"
                >
                    <Plus className="w-5 h-5" />
                    Nueva Factura
                </Link>
            </div>

            <div className="bg-zinc-900/50 border border-white/5 rounded-2xl p-6 backdrop-blur-xl flex flex-col min-h-[500px]">
                {/* Herramientas de tabla */}
                <div className="flex items-center gap-3 bg-black/40 border border-white/10 rounded-xl px-4 py-3 mb-6 focus-within:border-indigo-500/50 focus-within:ring-1 focus-within:ring-indigo-500/50 transition-all max-w-md">
                    <Search className="w-5 h-5 text-zinc-500" />
                    <input
                        type="text"
                        placeholder="Buscar por cliente o número..."
                        className="bg-transparent border-none outline-none text-zinc-100 w-full placeholder:text-zinc-600"
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                    />
                </div>

                {loading ? (
                    <div className="flex-1 flex flex-col items-center justify-center py-12">
                        <div className="animate-spin w-10 h-10 border-4 border-indigo-500/30 border-t-indigo-500 rounded-full mb-4"></div>
                        <p className="text-zinc-400">Cargando facturas...</p>
                    </div>
                ) : invoices.length === 0 ? (
                    <div className="flex-1 flex flex-col items-center justify-center text-center py-16 bg-black/20 rounded-xl border border-white/5 border-dashed">
                        <div className="bg-indigo-500/10 w-20 h-20 rounded-full flex items-center justify-center mb-6 border border-indigo-500/20 shadow-lg shadow-indigo-500/10">
                            <FileText className="w-10 h-10 text-indigo-400" />
                        </div>
                        <h3 className="text-xl font-bold text-white mb-2">Crea tu primera factura</h3>
                        <p className="text-zinc-400 max-w-sm mb-6">
                            Aún no has emitido ninguna factura de venta. Empieza ahora o deja que la IA lo haga por ti.
                        </p>
                        <Link
                            href="/ventas/facturas/nueva"
                            className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-6 py-3 rounded-xl transition-all shadow-lg font-medium mb-8"
                        >
                            <Plus className="w-5 h-5" />
                            Crear Factura
                        </Link>
                        <div className="flex flex-col items-center gap-3 w-full max-w-md">
                            <p className="text-xs text-zinc-500 uppercase tracking-widest font-medium">o pide a la IA</p>
                            <div className="flex flex-wrap justify-center gap-2">
                                {[
                                    "Crea una factura de consultoría por 1.500€",
                                    "Factura de mantenimiento mensual 500€",
                                    "Factura de servicios de diseño 800€",
                                ].map((suggestion) => (
                                    <button
                                        key={suggestion}
                                        onClick={async () => {
                                            try {
                                                await api.tasks.create("billing", suggestion);
                                                useToastStore.getState().show("Tarea enviada a la IA. Revisa Tareas IA para el resultado.", "info");
                                            } catch {
                                                useToastStore.getState().show("Error al enviar la tarea", "error");
                                            }
                                        }}
                                        className="text-xs bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 hover:border-indigo-500/40 text-zinc-300 hover:text-white px-3 py-1.5 rounded-lg transition-all"
                                    >
                                        {suggestion}
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-left border-collapse">
                            <thead>
                                <tr className="border-b border-white/5 text-sm text-zinc-400">
                                    <th className="pb-4 font-medium pl-4">Número</th>
                                    <th className="pb-4 font-medium">Contacto</th>
                                    <th className="pb-4 font-medium text-center">Estado</th>
                                    <th className="pb-4 font-medium text-right">Fecha</th>
                                    <th className="pb-4 font-medium text-right">Vencimiento</th>
                                    <th className="pb-4 font-medium text-right">Generada</th>
                                    <th className="pb-4 font-medium text-right">Total</th>
                                    <th className="pb-4 font-medium text-right pr-4">PDF</th>
                                </tr>
                            </thead>
                            <tbody className="text-sm">
                                {filteredInvoices.length > 0 ? (
                                    filteredInvoices.map((inv) => (
                                        <tr key={inv.id} className="border-b border-white/5 hover:bg-white/[0.02] transition-colors group">
                                            <td className="py-4 pl-4">
                                                <Link
                                                    href={`/ventas/facturas/${inv.id}`}
                                                    className="font-medium text-white flex items-center gap-2 hover:text-indigo-300 transition-colors"
                                                    title="Ver detalle"
                                                >
                                                    <FileText className="w-4 h-4 text-zinc-500 group-hover:text-indigo-400 transition-colors" />
                                                    {inv.invoice_number || <span className="text-zinc-600 italic">Borrador</span>}
                                                </Link>
                                            </td>
                                            <td className="py-4">
                                                <div className="flex flex-col">
                                                    <span className="text-zinc-200 font-medium">{inv.client?.name || "Cliente Desconocido"}</span>
                                                    {inv.client?.nif && <span className="text-xs text-zinc-500">{inv.client.nif}</span>}
                                                </div>
                                            </td>
                                            <td className="py-4 text-center">
                                                <StatusBadge status={inv.status} />
                                            </td>
                                            <td className="py-4 text-right text-zinc-400">
                                                {inv.date ? new Date(inv.date).toLocaleDateString('es-ES') : "-"}
                                            </td>
                                            <td className="py-4 text-right text-zinc-400">
                                                {inv.due_date ? new Date(inv.due_date).toLocaleDateString('es-ES') : "-"}
                                            </td>
                                            <td className="py-4 text-right">
                                                <div className="flex flex-col items-end">
                                                    <span className="text-zinc-400 text-xs">{new Date(inv.created_at).toLocaleDateString('es-ES')}</span>
                                                    <span className="text-zinc-600 text-xs">{new Date(inv.created_at).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
                                                </div>
                                            </td>
                                            <td className="py-4 pr-4 text-right font-medium text-white">
                                                {Number(inv.amount_total).toLocaleString('es-ES', { minimumFractionDigits: 2 })}€
                                            </td>
                                            <td className="py-4 pr-4 text-right">
                                                <div className="flex items-center justify-end gap-2">
                                                    <button
                                                        onClick={() => downloadInvoicePdf(inv.id, inv.invoice_number)}
                                                        title="Descargar PDF"
                                                        className="inline-flex items-center gap-1.5 text-xs text-indigo-400 hover:text-indigo-300 border border-indigo-500/20 hover:border-indigo-400/40 rounded-lg px-2.5 py-1.5 transition-all"
                                                    >
                                                        <Download className="w-3.5 h-3.5" />
                                                        PDF
                                                    </button>
                                                    <button
                                                        onClick={() => handleDeleteInvoice(inv.id)}
                                                        title="Eliminar factura"
                                                        className="inline-flex items-center gap-1.5 text-xs text-red-400 hover:text-red-300 border border-red-500/20 hover:border-red-400/40 rounded-lg px-2.5 py-1.5 transition-all"
                                                    >
                                                        <Trash2 className="w-3.5 h-3.5" />
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>
                                    ))
                                ) : (
                                    <tr>
                                        <td colSpan={7} className="py-16 text-center">
                                            <div className="flex flex-col items-center gap-2">
                                                <Search className="w-7 h-7 text-zinc-600" />
                                                <p className="text-zinc-400 text-sm font-medium">Sin resultados para &quot;{searchTerm}&quot;</p>
                                                <p className="text-zinc-600 text-xs">Prueba con el nombre del cliente o número de factura</p>
                                            </div>
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
}
