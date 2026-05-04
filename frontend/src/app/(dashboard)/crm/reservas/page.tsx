"use client";

import { CalendarRange, Plus, Search, CalendarClock } from "lucide-react";
import { format } from "date-fns";
import { useReservas } from "./_hooks/useReservas";
import { CreateReservationModal } from "./_components/CreateReservationModal";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

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
        <div className="p-8 max-w-[1400px] mx-auto space-y-6">
            <PageHeader
                title="Reservas y Espacios"
                description="Gestiona las reservas de tus clientes sobre tus servicios o instalaciones."
                icon={CalendarRange}
                actions={
                    <Button onClick={() => setShowCreate(true)}>
                        <Plus className="w-4 h-4 mr-2" /> Bloquear Espacio / Reservar
                    </Button>
                }
            />

            <div className="bg-card border border-border rounded-2xl overflow-hidden shadow-2xl">
                <div className="p-4 border-b border-border flex justify-between items-center bg-muted/30">
                    <div className="relative">
                        <Search className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
                        <Input
                            placeholder="Buscar por cliente o nota..."
                            value={search}
                            onChange={e => setSearch(e.target.value)}
                            className="pl-10 w-72"
                        />
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
                        <tbody className="divide-y divide-border">
                            {isLoading ? (
                                <tr>
                                    <td colSpan={6} className="px-6 py-12 text-center">
                                        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary mx-auto" />
                                    </td>
                                </tr>
                            ) : filtered.length === 0 ? (
                                <tr>
                                    <td colSpan={6} className="px-6 py-16 text-center">
                                        <CalendarClock className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
                                        <p className="text-muted-foreground font-medium">No hay reservas</p>
                                    </td>
                                </tr>
                            ) : filtered.map((res) => {
                                const clientName = clients.find(c => c.id === res.client_id)?.name ?? res.client_id.slice(0, 8);
                                return (
                                    <tr key={res.id} className="hover:bg-muted/30 transition-colors">
                                        <td className="px-6 py-4 font-medium text-foreground">{clientName}</td>
                                        <td className="px-6 py-4 text-muted-foreground">{format(new Date(res.start_time), "dd/MM/yyyy HH:mm")}</td>
                                        <td className="px-6 py-4 text-muted-foreground">{format(new Date(res.end_time), "dd/MM/yyyy HH:mm")}</td>
                                        <td className="px-6 py-4 text-muted-foreground max-w-[200px] truncate">{res.notes || "-"}</td>
                                        <td className="px-6 py-4">{getStatusBadge(res.status)}</td>
                                        <td className="px-6 py-4">
                                            <div className="flex items-center gap-2">
                                                {res.status === "pending" && (
                                                    <Button size="sm" variant="ghost"
                                                        className="text-xs h-7 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/20"
                                                        onClick={() => handleStatusChange(res.id, "confirmed")}>
                                                        Confirmar
                                                    </Button>
                                                )}
                                                {res.status === "confirmed" && (
                                                    <Button size="sm" variant="ghost"
                                                        className="text-xs h-7 bg-blue-500/10 text-blue-400 border border-blue-500/20 hover:bg-blue-500/20"
                                                        onClick={() => handleStatusChange(res.id, "completed")}>
                                                        Finalizar
                                                    </Button>
                                                )}
                                                {(res.status === "pending" || res.status === "confirmed") && (
                                                    <Button size="sm" variant="ghost"
                                                        className="text-xs h-7 bg-red-500/10 text-red-400 border border-red-500/20 hover:bg-red-500/20"
                                                        onClick={() => handleStatusChange(res.id, "cancelled")}>
                                                        Cancelar
                                                    </Button>
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
