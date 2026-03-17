"use client";

import { useEffect, useState } from "react";
import { api, Reservation, Client } from "@/lib/api";
import { CalendarRange, Plus, Search, CalendarClock, CheckCircle2, XCircle, Clock, CalendarCheck, X } from "lucide-react";
import { format } from "date-fns";
import { useToastStore } from "@/stores/toast";
import { logError } from "@/lib/logger";

const toLocalDatetime = (d: Date) => d.toISOString().slice(0, 16);

export default function ReservationsPage() {
    const toast = useToastStore();
    const [reservations, setReservations] = useState<Reservation[]>([]);
    const [clients, setClients] = useState<Client[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [search, setSearch] = useState("");

    const [showCreate, setShowCreate] = useState(false);
    const [creating, setCreating] = useState(false);
    const [form, setForm] = useState({
        client_id: "", notes: "",
        start_time: toLocalDatetime(new Date()),
        end_time: toLocalDatetime(new Date(Date.now() + 3600000)),
        status: "pending",
    });

    useEffect(() => { loadData(); }, []);

    const loadData = async () => {
        setIsLoading(true);
        try {
            const [res, clis] = await Promise.all([api.crm.reservations.list(), api.erp.clients.list()]);
            setReservations(res);
            setClients(clis);
        } catch (e) { logError("crm/reservas/page", e); }
        finally { setIsLoading(false); }
    };

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!form.client_id) { toast.warning("Selecciona un cliente"); return; }
        setCreating(true);
        try {
            await api.crm.reservations.create({
                ...form, notes: form.notes || undefined,
            } as any);
            setShowCreate(false);
            setForm({ client_id: "", notes: "", start_time: toLocalDatetime(new Date()), end_time: toLocalDatetime(new Date(Date.now() + 3600000)), status: "pending" });
            await loadData();
        } catch { toast.error("Error al crear la reserva"); }
        finally { setCreating(false); }
    };

    const handleStatusChange = async (id: string, status: string) => {
        try {
            await api.crm.reservations.update(id, { status });
            await loadData();
        } catch (e) { logError("crm/reservas/page", e); }
    };

    const filtered = reservations.filter(r => {
        const clientName = clients.find(c => c.id === r.client_id)?.name ?? "";
        return clientName.toLowerCase().includes(search.toLowerCase()) || (r.notes ?? "").toLowerCase().includes(search.toLowerCase());
    });

    const getStatusBadge = (status: string) => {
        switch (status) {
            case "pending": return <span className="flex items-center gap-1.5 px-3 py-1 bg-amber-500/10 text-amber-500 border border-amber-500/20 rounded text-xs font-medium"><Clock className="w-3.5 h-3.5" /> Pendiente</span>;
            case "confirmed": return <span className="flex items-center gap-1.5 px-3 py-1 bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 rounded text-xs font-medium"><CheckCircle2 className="w-3.5 h-3.5" /> Confirmada</span>;
            case "cancelled": return <span className="flex items-center gap-1.5 px-3 py-1 bg-red-500/10 text-red-500 border border-red-500/20 rounded text-xs font-medium"><XCircle className="w-3.5 h-3.5" /> Cancelada</span>;
            case "completed": return <span className="flex items-center gap-1.5 px-3 py-1 bg-blue-500/10 text-blue-400 border border-blue-500/20 rounded text-xs font-medium"><CalendarCheck className="w-3.5 h-3.5" /> Finalizada</span>;
            default: return null;
        }
    };

    return (
        <div className="min-h-screen bg-[#09090b] text-white p-8">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-8">
                <div>
                    <h1 className="text-3xl font-light text-white flex items-center gap-3">
                        <div className="p-2 bg-emerald-500/10 rounded-xl"><CalendarRange className="w-8 h-8 text-emerald-400" /></div>
                        Reservas y Espacios
                    </h1>
                    <p className="text-zinc-400 mt-2 ml-14 text-sm">Gestiona las reservas de tus clientes sobre tus servicios o instalaciones.</p>
                </div>
                <button onClick={() => setShowCreate(true)} className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-white px-5 py-2.5 rounded-full font-medium transition-colors">
                    <Plus className="w-4 h-4" /> Bloquear Espacio / Reservar
                </button>
            </div>

            <div className="bg-[#111113] border border-zinc-800 rounded-2xl overflow-hidden shadow-2xl">
                <div className="p-4 border-b border-zinc-800 flex justify-between items-center bg-[#161618]">
                    <div className="relative">
                        <Search className="w-4 h-4 text-zinc-500 absolute left-3 top-1/2 -translate-y-1/2" />
                        <input type="text" placeholder="Buscar por cliente o nota..." value={search} onChange={e => setSearch(e.target.value)}
                            className="bg-[#09090b] border border-zinc-800 text-sm text-white rounded-lg pl-10 pr-4 py-2 focus:outline-none focus:border-emerald-500 w-72" />
                    </div>
                    <span className="text-xs text-zinc-500">{filtered.length} reservas</span>
                </div>

                <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm whitespace-nowrap">
                        <thead className="bg-[#161618]/50 text-zinc-400 border-b border-zinc-800">
                            <tr>
                                <th className="px-6 py-4 font-medium">Cliente</th>
                                <th className="px-6 py-4 font-medium">Inicio</th>
                                <th className="px-6 py-4 font-medium">Fin</th>
                                <th className="px-6 py-4 font-medium">Notas</th>
                                <th className="px-6 py-4 font-medium">Estado</th>
                                <th className="px-6 py-4 font-medium">Acciones</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-zinc-800/50">
                            {isLoading ? (
                                <tr><td colSpan={6} className="px-6 py-12 text-center"><div className="animate-spin rounded-full h-6 w-6 border-b-2 border-emerald-500 mx-auto"></div></td></tr>
                            ) : filtered.length === 0 ? (
                                <tr><td colSpan={6} className="px-6 py-16 text-center">
                                    <CalendarClock className="w-10 h-10 text-zinc-600 mx-auto mb-3" />
                                    <p className="text-zinc-400 font-medium">No hay reservas</p>
                                </td></tr>
                            ) : filtered.map((res) => {
                                const clientName = clients.find(c => c.id === res.client_id)?.name ?? res.client_id.slice(0, 8);
                                return (
                                    <tr key={res.id} className="hover:bg-emerald-500/[0.02] transition-colors">
                                        <td className="px-6 py-4 font-medium text-white">{clientName}</td>
                                        <td className="px-6 py-4 text-zinc-400">{format(new Date(res.start_time), "dd/MM/yyyy HH:mm")}</td>
                                        <td className="px-6 py-4 text-zinc-400">{format(new Date(res.end_time), "dd/MM/yyyy HH:mm")}</td>
                                        <td className="px-6 py-4 text-zinc-500 max-w-[200px] truncate">{res.notes || "-"}</td>
                                        <td className="px-6 py-4">{getStatusBadge(res.status)}</td>
                                        <td className="px-6 py-4">
                                            <div className="flex items-center gap-2">
                                                {res.status === "pending" && (
                                                    <button onClick={() => handleStatusChange(res.id, "confirmed")}
                                                        className="text-xs px-2.5 py-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded hover:bg-emerald-500/20 transition-colors">
                                                        Confirmar
                                                    </button>
                                                )}
                                                {res.status === "confirmed" && (
                                                    <button onClick={() => handleStatusChange(res.id, "completed")}
                                                        className="text-xs px-2.5 py-1 bg-blue-500/10 text-blue-400 border border-blue-500/20 rounded hover:bg-blue-500/20 transition-colors">
                                                        Finalizar
                                                    </button>
                                                )}
                                                {(res.status === "pending" || res.status === "confirmed") && (
                                                    <button onClick={() => handleStatusChange(res.id, "cancelled")}
                                                        className="text-xs px-2.5 py-1 bg-red-500/10 text-red-400 border border-red-500/20 rounded hover:bg-red-500/20 transition-colors">
                                                        Cancelar
                                                    </button>
                                                )}
                                            </div>
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            </div>

            {showCreate && (
                <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                    <div className="bg-[#111113] border border-zinc-800 rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden">
                        <div className="p-6 border-b border-zinc-800 flex justify-between items-center bg-[#161618]">
                            <h2 className="text-lg font-medium text-white flex items-center gap-2"><CalendarRange className="w-5 h-5 text-emerald-400" /> Nueva Reserva</h2>
                            <button onClick={() => setShowCreate(false)} className="text-zinc-500 hover:text-white"><X className="w-5 h-5" /></button>
                        </div>
                        <form onSubmit={handleCreate} className="p-6 space-y-4">
                            <div>
                                <label className="block text-sm text-zinc-400 mb-1.5">Cliente *</label>
                                <select required value={form.client_id} onChange={e => setForm({ ...form, client_id: e.target.value })}
                                    className="w-full bg-[#09090b] border border-zinc-800 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-emerald-500">
                                    <option value="">Selecciona un cliente</option>
                                    {clients.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                                </select>
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm text-zinc-400 mb-1.5">Inicio *</label>
                                    <input required type="datetime-local" value={form.start_time} onChange={e => setForm({ ...form, start_time: e.target.value })}
                                        className="w-full bg-[#09090b] border border-zinc-800 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-emerald-500" />
                                </div>
                                <div>
                                    <label className="block text-sm text-zinc-400 mb-1.5">Fin *</label>
                                    <input required type="datetime-local" value={form.end_time} onChange={e => setForm({ ...form, end_time: e.target.value })}
                                        className="w-full bg-[#09090b] border border-zinc-800 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-emerald-500" />
                                </div>
                            </div>
                            <div>
                                <label className="block text-sm text-zinc-400 mb-1.5">Notas</label>
                                <textarea value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} rows={2}
                                    className="w-full bg-[#09090b] border border-zinc-800 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-emerald-500 resize-none"
                                    placeholder="Sala A, equipamiento necesario..." />
                            </div>
                            <div className="flex justify-end gap-3 pt-2 border-t border-zinc-800">
                                <button type="button" onClick={() => setShowCreate(false)} className="px-5 py-2.5 text-zinc-400 hover:text-white">Cancelar</button>
                                <button type="submit" disabled={creating} className="bg-emerald-600 hover:bg-emerald-500 text-white px-6 py-2.5 rounded-lg font-medium disabled:opacity-50">
                                    {creating ? "Guardando..." : "Reservar"}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
