"use client";

import { useEffect, useState } from "react";
import { api, Reservation, Client } from "@/lib/api";
import { useToastStore } from "@/stores/toast";
import { logError } from "@/lib/logger";
import { Clock, CheckCircle2, XCircle, CalendarCheck } from "lucide-react";

const toLocalDatetime = (d: Date) => d.toISOString().slice(0, 16);

export function useReservas() {
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

    return {
        reservations, clients, isLoading,
        search, setSearch,
        showCreate, setShowCreate,
        creating, form, setForm,
        handleCreate, handleStatusChange,
        filtered, getStatusBadge,
    };
}
