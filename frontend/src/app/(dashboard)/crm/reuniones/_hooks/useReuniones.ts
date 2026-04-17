"use client";

import { useEffect, useState } from "react";
import { api, EventItem, Client } from "@/lib/api";
import { isPast, isToday } from "date-fns";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";
import { logError } from "@/lib/logger";

const toLocalDatetime = (d: Date) => d.toISOString().slice(0, 16);

export function useReuniones() {
    const toast = useToastStore();
    const [meetings, setMeetings] = useState<EventItem[]>([]);
    const [clients, setClients] = useState<Client[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [search, setSearch] = useState("");

    const [showCreate, setShowCreate] = useState(false);
    const [creating, setCreating] = useState(false);
    const [form, setForm] = useState({
        title: "", description: "", location_or_link: "", client_id: "",
        start_time: toLocalDatetime(new Date()),
        end_time: toLocalDatetime(new Date(Date.now() + 3600000)),
    });

    useEffect(() => { loadData(); }, []);

    const loadData = async () => {
        setIsLoading(true);
        try {
            const [evts, clis] = await Promise.all([api.crm.events.list(), api.erp.clients.list()]);
            setMeetings(evts.filter(e => e.type === "meeting"));
            setClients(clis);
        } catch (e) { logError("crm/reuniones/page", e); }
        finally { setIsLoading(false); }
    };

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        setCreating(true);
        try {
            await api.crm.events.create({
                ...form, type: "meeting",
                client_id: form.client_id || undefined,
                description: form.description || undefined,
                location_or_link: form.location_or_link || undefined,
            } as any);
            setShowCreate(false);
            setForm({ title: "", description: "", location_or_link: "", client_id: "", start_time: toLocalDatetime(new Date()), end_time: toLocalDatetime(new Date(Date.now() + 3600000)) });
            await loadData();
        } catch { toast.error("Error al programar la reunión"); }
        finally { setCreating(false); }
    };

    const handleDelete = async (id: string) => {
        if (!await showConfirm({ message: "¿Eliminar esta reunión?", confirmLabel: "Eliminar", confirmVariant: "danger" })) return;
        try { await api.crm.events.delete(id); await loadData(); }
        catch (e) { logError("crm/reuniones/page", e); }
    };

    const filtered = meetings.filter(m => m.title.toLowerCase().includes(search.toLowerCase()) || (m.description ?? "").toLowerCase().includes(search.toLowerCase()));
    const upcoming = filtered.filter(m => !isPast(new Date(m.start_time)) || isToday(new Date(m.start_time)));
    const past = filtered.filter(m => isPast(new Date(m.start_time)) && !isToday(new Date(m.start_time)));

    return {
        meetings, clients, isLoading,
        search, setSearch,
        showCreate, setShowCreate,
        creating, form, setForm,
        handleCreate, handleDelete,
        filtered, upcoming, past,
    };
}
