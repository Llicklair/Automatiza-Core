"use client";

import { useEffect, useState } from "react";
import { api, Client, Invoice } from "@/lib/api";
import {
    Plus, Building2, UserCircle, Search, Mail, MapPin, X,
    FileText, ArrowUpRight, ArrowDownLeft, Hash, Calendar,
    Phone, Globe, Loader2, ChevronRight, Download, ExternalLink
} from "lucide-react";
import Link from "next/link";
import { useToastStore } from "@/stores/toast";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8080";

function getToken(): string {
    return typeof window !== "undefined" ? (localStorage.getItem("access_token") ?? "") : "";
}

async function downloadInvoicePdf(invoiceId: string, invoiceNumber: string | null) {
    try {
        const res = await fetch(`${API_BASE}/api/v1/invoices/${invoiceId}/pdf`, {
            headers: { Authorization: `Bearer ${getToken()}` },
        });
        if (!res.ok) throw new Error();
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
        useToastStore.getState().error("No se pudo descargar el PDF");
    }
}

const CLIENT_TYPE_MAP: Record<string, { label: string; color: string }> = {
    customer: { label: "Cliente", color: "text-indigo-400 bg-indigo-500/10 border-indigo-500/20" },
    supplier: { label: "Proveedor", color: "text-amber-400 bg-amber-500/10 border-amber-500/20" },
    company: { label: "Empresa", color: "text-blue-400 bg-blue-500/10 border-blue-500/20" },
    lead: { label: "Lead", color: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20" },
};

const STATUS_INV: Record<string, string> = {
    draft: "text-zinc-400 bg-zinc-800 border-zinc-700",
    pending: "text-amber-400 bg-amber-500/10 border-amber-500/20",
    paid: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
    overdue: "text-red-400 bg-red-500/10 border-red-500/20",
};
const STATUS_INV_LABEL: Record<string, string> = {
    draft: "Borrador", pending: "Pendiente", paid: "Cobrada", overdue: "Vencida",
};

export default function ClientesPage() {
    const toast = useToastStore();
    const [clients, setClients] = useState<Client[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [searchTerm, setSearchTerm] = useState("");

    // Drawer
    const [selectedClient, setSelectedClient] = useState<Client | null>(null);
    const [clientInvoices, setClientInvoices] = useState<Invoice[]>([]);
    const [loadingInvoices, setLoadingInvoices] = useState(false);

    // Creación / Edición
    const [isCreating, setIsCreating] = useState(false);
    const [editingClient, setEditingClient] = useState<Client | null>(null);
    const [newClient, setNewClient] = useState<Partial<Client>>({ client_type: "customer" });
    const [saving, setSaving] = useState(false);
    const [deleting, setDeleting] = useState(false);

    const loadClients = async () => {
        try {
            setLoading(true);
            const data = await api.erp.clients.list();
            setClients(data);
        } catch (err: any) {
            setError(err.message || "Error al cargar clientes");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { loadClients(); }, []);

    const handleCreateClient = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            setSaving(true);
            if (editingClient) {
                await api.erp.clients.update(editingClient.id, newClient);
            } else {
                await api.erp.clients.create(newClient);
            }
            setIsCreating(false);
            setEditingClient(null);
            setNewClient({ client_type: "customer" });
            loadClients();
        } catch (err: any) {
            toast.error(err.message || "Error al guardar cliente");
        } finally {
            setSaving(false);
        }
    };

    const openEditClient = (client: Client) => {
        setEditingClient(client);
        setNewClient({
            name: client.name, nif: client.nif, client_type: client.client_type,
            email: client.email, address: client.address, city: client.city,
            postal_code: client.postal_code,
        });
        setIsCreating(true);
        closeDrawer();
    };

    const handleDeleteClient = async (client: Client) => {
        if (!confirm(`¿Eliminar "${client.name}"? Esta acción no se puede deshacer.`)) return;
        setDeleting(true);
        try {
            await api.erp.clients.delete(client.id);
            closeDrawer();
            loadClients();
        } catch (err: any) {
            toast.error(err.message || "Error al eliminar cliente");
        } finally {
            setDeleting(false);
        }
    };

    const openClientDrawer = async (client: Client) => {
        setSelectedClient(client);
        setLoadingInvoices(true);
        try {
            const data = await api.erp.clients.invoices(client.id);
            setClientInvoices(data);
        } catch {
            setClientInvoices([]);
        } finally {
            setLoadingInvoices(false);
        }
    };

    const closeDrawer = () => {
        setSelectedClient(null);
        setClientInvoices([]);
    };

    const filtered = clients.filter(c =>
        c.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (c.nif && c.nif.toLowerCase().includes(searchTerm.toLowerCase())) ||
        (c.email && c.email.toLowerCase().includes(searchTerm.toLowerCase()))
    );

    const totalFacturado = clientInvoices.reduce((s, i) => s + Number(i.amount_total), 0);

    return (
        <div className="p-8 max-w-7xl mx-auto space-y-6 relative">

            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight text-white">Directorio de Clientes</h1>
                    <p className="text-zinc-400 text-sm mt-1">
                        {clients.length} contacto{clients.length !== 1 ? "s" : ""} registrado{clients.length !== 1 ? "s" : ""}
                    </p>
                </div>
                <button
                    onClick={() => setIsCreating(true)}
                    className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2.5 rounded-xl transition-all shadow-lg shadow-indigo-500/20 font-medium text-sm"
                >
                    <Plus className="w-4 h-4" />
                    Nuevo Cliente
                </button>
            </div>

            {/* Buscador */}
            <div className="flex items-center gap-3 bg-[#111113] border border-[#27272a] rounded-xl px-4 py-3 focus-within:border-indigo-500/50 transition-all max-w-md">
                <Search className="w-4 h-4 text-zinc-500 flex-shrink-0" />
                <input
                    type="text"
                    placeholder="Buscar por nombre, NIF o email..."
                    className="bg-transparent border-none outline-none text-zinc-100 text-sm w-full placeholder:text-zinc-600"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                />
                {searchTerm && (
                    <button onClick={() => setSearchTerm("")} className="text-zinc-500 hover:text-white transition">
                        <X className="w-4 h-4" />
                    </button>
                )}
            </div>

            {/* Tabla */}
            <div className="bg-[#111113] border border-[#27272a] rounded-2xl overflow-hidden">
                {/* Cabecera */}
                <div className="grid grid-cols-12 gap-4 px-6 py-3 border-b border-[#27272a] text-xs font-medium text-zinc-500 uppercase tracking-wide">
                    <div className="col-span-4">Nombre / Razón social</div>
                    <div className="col-span-2">NIF / CIF</div>
                    <div className="col-span-2">Tipo</div>
                    <div className="col-span-2">Email</div>
                    <div className="col-span-1">Ciudad</div>
                    <div className="col-span-1 text-right">Alta</div>
                </div>

                {loading ? (
                    <div className="py-16 flex items-center justify-center gap-2 text-zinc-500 text-sm">
                        <Loader2 className="w-4 h-4 animate-spin" /> Cargando directorio…
                    </div>
                ) : error ? (
                    <div className="py-10 text-center text-red-400 text-sm">{error}</div>
                ) : filtered.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-16 text-center">
                        <Building2 className="w-10 h-10 text-zinc-700 mb-3" />
                        <p className="text-sm text-zinc-400">
                            {searchTerm ? `Sin resultados para "${searchTerm}"` : "Ningún cliente registrado aún"}
                        </p>
                        {!searchTerm && (
                            <button
                                onClick={() => setIsCreating(true)}
                                className="mt-4 text-xs text-indigo-400 hover:text-indigo-300 underline transition"
                            >
                                Crear primer cliente
                            </button>
                        )}
                    </div>
                ) : (
                    <div className="divide-y divide-[#27272a]">
                        {filtered.map(client => {
                            const typeInfo = CLIENT_TYPE_MAP[client.client_type] ?? { label: client.client_type, color: "text-zinc-400 bg-zinc-800 border-zinc-700" };
                            return (
                                <div
                                    key={client.id}
                                    onClick={() => openClientDrawer(client)}
                                    className="grid grid-cols-12 gap-4 px-6 py-3.5 items-center hover:bg-white/[0.02] cursor-pointer transition group"
                                >
                                    {/* Nombre */}
                                    <div className="col-span-4 flex items-center gap-3 min-w-0">
                                        <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center flex-shrink-0">
                                            {client.client_type === "company" || client.client_type === "supplier"
                                                ? <Building2 className="w-4 h-4 text-indigo-400" />
                                                : <UserCircle className="w-4 h-4 text-indigo-400" />
                                            }
                                        </div>
                                        <div className="min-w-0">
                                            <p className="text-sm font-medium text-white truncate group-hover:text-indigo-300 transition">{client.name}</p>
                                            {client.city && <p className="text-xs text-zinc-600 truncate">{client.city}</p>}
                                        </div>
                                    </div>

                                    {/* NIF */}
                                    <div className="col-span-2">
                                        {client.nif ? (
                                            <span className="text-xs font-mono bg-zinc-800/60 border border-zinc-700/50 text-zinc-300 px-2 py-0.5 rounded">
                                                {client.nif}
                                            </span>
                                        ) : (
                                            <span className="text-xs text-zinc-600 italic">Sin NIF</span>
                                        )}
                                    </div>

                                    {/* Tipo */}
                                    <div className="col-span-2">
                                        <span className={`text-[10px] px-2 py-0.5 rounded-full border font-semibold uppercase tracking-wide ${typeInfo.color}`}>
                                            {typeInfo.label}
                                        </span>
                                    </div>

                                    {/* Email */}
                                    <div className="col-span-2 text-xs text-zinc-400 truncate">
                                        {client.email || <span className="text-zinc-600 italic">—</span>}
                                    </div>

                                    {/* Ciudad */}
                                    <div className="col-span-1 text-xs text-zinc-500 truncate">
                                        {client.city || "—"}
                                    </div>

                                    {/* Fecha */}
                                    <div className="col-span-1 text-xs text-zinc-500 text-right">
                                        {new Date(client.created_at).toLocaleDateString("es-ES", { day: "2-digit", month: "short", year: "2-digit" })}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>

            {/* Backdrop */}
            {(selectedClient || isCreating) && (
                <div
                    className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 transition-opacity"
                    onClick={() => { if (isCreating) { setIsCreating(false); setEditingClient(null); setNewClient({ client_type: "customer" }); } else closeDrawer(); }}
                />
            )}

            {/* Modal creación */}
            {isCreating && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
                    <div className="bg-[#111113] border border-[#27272a] rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden">
                        <div className="px-6 py-4 border-b border-[#27272a] flex justify-between items-center bg-[#18181b]">
                            <h2 className="text-base font-bold text-white flex items-center gap-2">
                                <Plus className="w-4 h-4 text-indigo-400" /> {editingClient ? "Editar Cliente" : "Nuevo Cliente"}
                            </h2>
                            <button onClick={() => setIsCreating(false)} className="text-zinc-500 hover:text-white transition"><X className="w-5 h-5" /></button>
                        </div>
                        <form onSubmit={handleCreateClient} className="p-6 space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-1.5 col-span-2">
                                    <label className="text-xs font-medium text-zinc-400 uppercase tracking-wider">Nombre o Razón Social *</label>
                                    <input required type="text" value={newClient.name || ""} onChange={e => setNewClient({ ...newClient, name: e.target.value })}
                                        className="w-full bg-black/40 border border-[#27272a] rounded-xl px-4 py-2.5 text-sm text-white focus:border-indigo-500/50 outline-none" placeholder="Acme Corp S.L." />
                                </div>
                                <div className="space-y-1.5">
                                    <label className="text-xs font-medium text-zinc-400 uppercase tracking-wider">NIF / CIF</label>
                                    <input type="text" value={newClient.nif || ""} onChange={e => setNewClient({ ...newClient, nif: e.target.value })}
                                        className="w-full bg-black/40 border border-[#27272a] rounded-xl px-4 py-2.5 text-sm text-white focus:border-indigo-500/50 outline-none uppercase" placeholder="B12345678" />
                                </div>
                                <div className="space-y-1.5">
                                    <label className="text-xs font-medium text-zinc-400 uppercase tracking-wider">Tipo</label>
                                    <select value={newClient.client_type || "customer"} onChange={e => setNewClient({ ...newClient, client_type: e.target.value })}
                                        className="w-full bg-black/40 border border-[#27272a] rounded-xl px-4 py-2.5 text-sm text-white focus:border-indigo-500/50 outline-none">
                                        <option value="customer">Cliente</option>
                                        <option value="supplier">Proveedor</option>
                                        <option value="company">Empresa</option>
                                        <option value="lead">Lead</option>
                                    </select>
                                </div>
                                <div className="space-y-1.5 col-span-2">
                                    <label className="text-xs font-medium text-zinc-400 uppercase tracking-wider">Email</label>
                                    <input type="email" value={newClient.email || ""} onChange={e => setNewClient({ ...newClient, email: e.target.value })}
                                        className="w-full bg-black/40 border border-[#27272a] rounded-xl px-4 py-2.5 text-sm text-white focus:border-indigo-500/50 outline-none" placeholder="contacto@empresa.com" />
                                </div>
                                <div className="space-y-1.5 col-span-2">
                                    <label className="text-xs font-medium text-zinc-400 uppercase tracking-wider">Dirección</label>
                                    <input type="text" value={newClient.address || ""} onChange={e => setNewClient({ ...newClient, address: e.target.value })}
                                        className="w-full bg-black/40 border border-[#27272a] rounded-xl px-4 py-2.5 text-sm text-white focus:border-indigo-500/50 outline-none" placeholder="Calle Principal 123" />
                                </div>
                                <div className="space-y-1.5">
                                    <label className="text-xs font-medium text-zinc-400 uppercase tracking-wider">Ciudad</label>
                                    <input type="text" value={newClient.city || ""} onChange={e => setNewClient({ ...newClient, city: e.target.value })}
                                        className="w-full bg-black/40 border border-[#27272a] rounded-xl px-4 py-2.5 text-sm text-white focus:border-indigo-500/50 outline-none" placeholder="Madrid" />
                                </div>
                                <div className="space-y-1.5">
                                    <label className="text-xs font-medium text-zinc-400 uppercase tracking-wider">Código Postal</label>
                                    <input type="text" value={newClient.postal_code || ""} onChange={e => setNewClient({ ...newClient, postal_code: e.target.value })}
                                        className="w-full bg-black/40 border border-[#27272a] rounded-xl px-4 py-2.5 text-sm text-white focus:border-indigo-500/50 outline-none" placeholder="28001" />
                                </div>
                            </div>
                            <div className="flex gap-3 justify-end pt-2 border-t border-[#27272a] mt-2">
                                <button type="button" onClick={() => setIsCreating(false)} className="px-5 py-2.5 rounded-xl text-sm text-zinc-400 hover:text-white hover:bg-white/5 transition">Cancelar</button>
                                <button type="submit" disabled={saving || !newClient.name} className="px-5 py-2.5 rounded-xl text-sm font-medium bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white transition">
                                    {saving ? <span className="flex items-center gap-2"><Loader2 className="w-4 h-4 animate-spin" />Guardando...</span> : editingClient ? "Guardar cambios" : "Crear Cliente"}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Drawer lateral detalle cliente */}
            <div className={`fixed top-0 right-0 h-full w-full max-w-[480px] bg-[#111113] border-l border-[#27272a] shadow-2xl z-50 transform transition-transform duration-300 ease-in-out flex flex-col ${selectedClient ? "translate-x-0" : "translate-x-full"}`}>
                {selectedClient && (
                    <>
                        {/* Header del drawer */}
                        <div className="px-6 py-5 border-b border-[#27272a] bg-[#18181b] sticky top-0 z-10">
                            <div className="flex items-start justify-between gap-3">
                                <div className="flex items-center gap-3 min-w-0">
                                    <div className="w-12 h-12 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center flex-shrink-0">
                                        {selectedClient.client_type === "company" || selectedClient.client_type === "supplier"
                                            ? <Building2 className="w-6 h-6 text-indigo-400" />
                                            : <UserCircle className="w-6 h-6 text-indigo-400" />
                                        }
                                    </div>
                                    <div className="min-w-0">
                                        <h2 className="text-lg font-bold text-white leading-tight truncate">{selectedClient.name}</h2>
                                        <div className="flex items-center gap-2 mt-1 flex-wrap">
                                            {selectedClient.nif && (
                                                <span className="text-xs font-mono text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded">
                                                    {selectedClient.nif}
                                                </span>
                                            )}
                                            {(() => {
                                                const t = CLIENT_TYPE_MAP[selectedClient.client_type] ?? { label: selectedClient.client_type, color: "text-zinc-400 bg-zinc-800 border-zinc-700" };
                                                return (
                                                    <span className={`text-[10px] px-2 py-0.5 rounded-full border font-semibold uppercase tracking-wide ${t.color}`}>
                                                        {t.label}
                                                    </span>
                                                );
                                            })()}
                                        </div>
                                    </div>
                                </div>
                                <button onClick={closeDrawer} className="p-2 rounded-lg hover:bg-white/5 text-zinc-400 hover:text-white transition flex-shrink-0">
                                    <X className="w-5 h-5" />
                                </button>
                            </div>
                        </div>

                        <div className="flex-1 overflow-y-auto">
                            {/* Datos de contacto */}
                            <div className="px-6 py-5 border-b border-[#27272a]">
                                <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-3">Información de contacto</h3>
                                <dl className="space-y-2.5">
                                    {selectedClient.email && (
                                        <div className="flex items-center gap-3">
                                            <Mail className="w-4 h-4 text-zinc-600 flex-shrink-0" />
                                            <span className="text-sm text-zinc-300">{selectedClient.email}</span>
                                        </div>
                                    )}
                                    {selectedClient.address && (
                                        <div className="flex items-start gap-3">
                                            <MapPin className="w-4 h-4 text-zinc-600 flex-shrink-0 mt-0.5" />
                                            <span className="text-sm text-zinc-300">{selectedClient.address}</span>
                                        </div>
                                    )}
                                    {(selectedClient.city || selectedClient.postal_code) && (
                                        <div className="flex items-center gap-3 pl-7">
                                            <span className="text-sm text-zinc-400">
                                                {[selectedClient.postal_code, selectedClient.city].filter(Boolean).join(" · ")}
                                            </span>
                                        </div>
                                    )}
                                    {!selectedClient.email && !selectedClient.address && !selectedClient.city && (
                                        <p className="text-sm text-zinc-600 italic">Sin datos de contacto</p>
                                    )}
                                </dl>
                            </div>

                            {/* Métricas rápidas */}
                            <div className="px-6 py-4 border-b border-[#27272a] grid grid-cols-3 gap-3">
                                <div className="bg-[#18181b] rounded-xl border border-[#27272a] p-3 text-center">
                                    <p className="text-2xl font-bold text-white">{clientInvoices.length}</p>
                                    <p className="text-[10px] text-zinc-500 mt-0.5 uppercase tracking-wide">Facturas</p>
                                </div>
                                <div className="bg-[#18181b] rounded-xl border border-[#27272a] p-3 text-center">
                                    <p className="text-2xl font-bold text-emerald-400">
                                        {totalFacturado.toLocaleString("es-ES", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}€
                                    </p>
                                    <p className="text-[10px] text-zinc-500 mt-0.5 uppercase tracking-wide">Facturado</p>
                                </div>
                                <div className="bg-[#18181b] rounded-xl border border-[#27272a] p-3 text-center">
                                    <p className="text-xs text-zinc-300 font-medium mt-1">
                                        {new Date(selectedClient.created_at).toLocaleDateString("es-ES", { day: "2-digit", month: "short", year: "numeric" })}
                                    </p>
                                    <p className="text-[10px] text-zinc-500 mt-0.5 uppercase tracking-wide">Alta</p>
                                </div>
                            </div>

                            {/* Historial de facturas */}
                            <div className="px-6 py-5">
                                <div className="flex items-center justify-between mb-4">
                                    <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider flex items-center gap-2">
                                        <FileText className="w-3.5 h-3.5" /> Historial de facturas
                                    </h3>
                                    <Link
                                        href={`/ventas/facturas/nueva?client_id=${selectedClient.id}`}
                                        className="text-xs font-medium text-indigo-400 hover:text-indigo-300 bg-indigo-500/10 hover:bg-indigo-500/20 px-2.5 py-1 rounded-lg transition-colors flex items-center gap-1"
                                    >
                                        <Plus className="w-3 h-3" /> Nueva
                                    </Link>
                                </div>

                                {loadingInvoices ? (
                                    <div className="flex items-center justify-center gap-2 py-8 text-zinc-500 text-sm">
                                        <Loader2 className="w-4 h-4 animate-spin" /> Cargando…
                                    </div>
                                ) : clientInvoices.length === 0 ? (
                                    <div className="text-center py-10 bg-[#18181b] rounded-xl border border-[#27272a] border-dashed">
                                        <FileText className="w-8 h-8 text-zinc-700 mx-auto mb-2" />
                                        <p className="text-sm text-zinc-500">Sin facturas registradas</p>
                                    </div>
                                ) : (
                                    <div className="space-y-2">
                                        {clientInvoices.map(inv => {
                                            const stCls = STATUS_INV[inv.status] ?? STATUS_INV.draft;
                                            const stLabel = STATUS_INV_LABEL[inv.status] ?? inv.status;
                                            return (
                                                <div key={inv.id} className="bg-[#18181b] rounded-xl border border-[#27272a] hover:border-indigo-500/30 transition p-4 flex items-center gap-3">
                                                    <div className="flex-1 min-w-0">
                                                        <div className="flex items-center gap-2 mb-1">
                                                            <span className="text-sm font-medium text-white truncate">
                                                                {inv.invoice_number || "Borrador"}
                                                            </span>
                                                            <span className={`text-[10px] px-2 py-0.5 rounded-full border font-medium flex-shrink-0 ${stCls}`}>
                                                                {stLabel}
                                                            </span>
                                                        </div>
                                                        <div className="flex items-center gap-2 text-xs text-zinc-500">
                                                            <span>{new Date(inv.date).toLocaleDateString("es-ES", { day: "2-digit", month: "short", year: "numeric" })}</span>
                                                            {inv.lines && inv.lines.length > 0 && (
                                                                <span className="text-zinc-600">· {inv.lines[0].description?.slice(0, 40)}{(inv.lines[0].description?.length ?? 0) > 40 ? "..." : ""}</span>
                                                            )}
                                                        </div>
                                                    </div>
                                                    <div className="text-right flex-shrink-0">
                                                        <p className="text-sm font-semibold text-white tabular-nums">
                                                            {Number(inv.amount_total).toLocaleString("es-ES", { minimumFractionDigits: 2 })}€
                                                        </p>
                                                        <p className="text-[10px] text-zinc-600">
                                                            Base {Number(inv.amount_base).toLocaleString("es-ES", { minimumFractionDigits: 2 })}€
                                                        </p>
                                                    </div>
                                                    <button
                                                        onClick={() => downloadInvoicePdf(inv.id, inv.invoice_number)}
                                                        title="Descargar PDF"
                                                        className="p-2 rounded-lg text-zinc-500 hover:text-indigo-400 hover:bg-indigo-500/10 transition flex-shrink-0"
                                                    >
                                                        <Download className="w-4 h-4" />
                                                    </button>
                                                </div>
                                            );
                                        })}
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* Footer del drawer */}
                        <div className="px-6 py-4 border-t border-[#27272a] bg-[#0d0d0f] space-y-2">
                            <div className="flex gap-2">
                                <button
                                    onClick={() => openEditClient(selectedClient)}
                                    className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-medium text-indigo-400 hover:text-white border border-indigo-500/30 hover:border-indigo-500 hover:bg-indigo-500/10 transition"
                                >
                                    <FileText className="w-4 h-4" />
                                    Editar cliente
                                </button>
                                <button
                                    onClick={() => handleDeleteClient(selectedClient)}
                                    disabled={deleting}
                                    className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium text-red-400 hover:text-white border border-red-500/30 hover:border-red-500 hover:bg-red-500/10 transition disabled:opacity-50"
                                >
                                    {deleting ? <Loader2 className="w-4 h-4 animate-spin" /> : <X className="w-4 h-4" />}
                                    Eliminar
                                </button>
                            </div>
                            <Link
                                href={`/clientes/${selectedClient.id}`}
                                className="flex items-center justify-center gap-2 w-full py-2.5 rounded-xl text-sm font-medium text-indigo-400 hover:text-white border border-indigo-500/20 hover:border-indigo-500 hover:bg-indigo-500/10 transition"
                            >
                                <ExternalLink className="w-4 h-4" />
                                Ver historial completo
                            </Link>
                            <Link
                                href="/ventas/facturas"
                                className="flex items-center justify-center gap-2 w-full py-2.5 rounded-xl text-sm font-medium text-zinc-400 hover:text-white border border-[#27272a] hover:border-zinc-500 hover:bg-white/5 transition"
                            >
                                <ExternalLink className="w-4 h-4" />
                                Ver todas las facturas en Ventas
                            </Link>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
}
