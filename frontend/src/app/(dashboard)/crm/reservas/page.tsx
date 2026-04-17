"use client";

import { CalendarRange, Plus, Search, CalendarClock } from "lucide-react";
import { format } from "date-fns";
import { useReservas } from "./_hooks/useReservas";
import { CreateReservationModal } from "./_components/CreateReservationModal";

export default function ReservationsPage() {
    const {
        clients, isLoading,
        search, setSearch,
        showCreate, setShowCreate,
        creating, form, setForm,
        handleCreate, handleStatusChange,
        filtered, getStatusBadge,
    } = useReservas();

    return (
        <div className="min-h-screen bg-background text-foreground p-8">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-8">
                <div>
                    <h1 className="text-3xl font-light text-foreground flex items-center gap-3">
                        <div className="p-2 bg-emerald-500/10 rounded-xl"><CalendarRange className="w-8 h-8 text-emerald-400" /></div>
                        Reservas y Espacios
                    </h1>
                    <p className="text-muted-foreground mt-2 ml-14 text-sm">Gestiona las reservas de tus clientes sobre tus servicios o instalaciones.</p>
                </div>
                <button onClick={() => setShowCreate(true)} className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-foreground px-5 py-2.5 rounded-full font-medium transition-colors">
                    <Plus className="w-4 h-4" /> Bloquear Espacio / Reservar
                </button>
            </div>

            <div className="bg-card border border-border rounded-2xl overflow-hidden shadow-2xl">
                <div className="p-4 border-b border-border flex justify-between items-center bg-muted">
                    <div className="relative">
                        <Search className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
                        <input type="text" placeholder="Buscar por cliente o nota..." value={search} onChange={e => setSearch(e.target.value)}
                            className="bg-background border border-border text-sm text-foreground rounded-lg pl-10 pr-4 py-2 focus:outline-none focus:border-emerald-500 w-72" />
                    </div>
                    <span className="text-xs text-muted-foreground">{filtered.length} reservas</span>
                </div>

                <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm whitespace-nowrap">
                        <thead className="bg-muted/50 text-muted-foreground border-b border-border">
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
                                    <CalendarClock className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
                                    <p className="text-muted-foreground font-medium">No hay reservas</p>
                                </td></tr>
                            ) : filtered.map((res) => {
                                const clientName = clients.find(c => c.id === res.client_id)?.name ?? res.client_id.slice(0, 8);
                                return (
                                    <tr key={res.id} className="hover:bg-emerald-500/[0.02] transition-colors">
                                        <td className="px-6 py-4 font-medium text-foreground">{clientName}</td>
                                        <td className="px-6 py-4 text-muted-foreground">{format(new Date(res.start_time), "dd/MM/yyyy HH:mm")}</td>
                                        <td className="px-6 py-4 text-muted-foreground">{format(new Date(res.end_time), "dd/MM/yyyy HH:mm")}</td>
                                        <td className="px-6 py-4 text-muted-foreground max-w-[200px] truncate">{res.notes || "-"}</td>
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
                <CreateReservationModal
                    clients={clients}
                    form={form}
                    setForm={setForm}
                    creating={creating}
                    onSubmit={handleCreate}
                    onClose={() => setShowCreate(false)}
                />
            )}
        </div>
    );
}
