"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { api, EventItem, Client } from "@/lib/api";
import { addMonths, subMonths, startOfMonth, endOfMonth, eachDayOfInterval, isSameDay } from "date-fns";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";
import { logError } from "@/lib/logger";

const toLocalDatetime = (d: Date) => d.toISOString().slice(0, 16);

export function useCalendario() {
    const t = useTranslations("crm");
    const toast = useToastStore();
    const [currentMonth, setCurrentMonth] = useState(new Date());
    const [events, setEvents] = useState<EventItem[]>([]);
    const [clients, setClients] = useState<Client[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [showCreate, setShowCreate] = useState(false);
    const [creating, setCreating] = useState(false);
    const [form, setForm] = useState(() => ({
        title: "", description: "", type: "meeting", location_or_link: "", client_id: "",
        start_time: toLocalDatetime(new Date()),
        end_time: toLocalDatetime(new Date(Date.now() + 3600000)),
    }));
    const [selected, setSelected] = useState<EventItem | null>(null);
    const [deleting, setDeleting] = useState(false);

    const loadData = async () => {
        setIsLoading(true);
        try {
            const [evts, clis] = await Promise.all([api.crm.events.list(), api.erp.clients.list()]);
            setEvents(evts);
            setClients(clis);
        } catch (e) { logError("crm/calendario/page", e); }
        finally { setIsLoading(false); }
    };

    useEffect(() => { loadData(); }, []);

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        setCreating(true);
        try {
            await api.crm.events.create({
                ...form,
                client_id: form.client_id || undefined,
                description: form.description || undefined,
                location_or_link: form.location_or_link || undefined,
            } as any);
            setShowCreate(false);
            setForm({ title: "", description: "", type: "meeting", location_or_link: "", client_id: "", start_time: toLocalDatetime(new Date()), end_time: toLocalDatetime(new Date(Date.now() + 3600000)) });
            await loadData();
        } catch { toast.error(t("calendario.createError")); }
        finally { setCreating(false); }
    };

    const handleDelete = async (id: string) => {
        if (!await showConfirm({ message: t("calendario.deleteConfirm"), confirmLabel: t("calendario.deleteLabel"), confirmVariant: "danger" })) return;
        setDeleting(true);
        try { await api.crm.events.delete(id); setSelected(null); await loadData(); }
        catch (e) { logError("crm/calendario/page", e); }
        finally { setDeleting(false); }
    };

    const nextMonth = () => setCurrentMonth(addMonths(currentMonth, 1));
    const prevMonth = () => setCurrentMonth(subMonths(currentMonth, 1));
    const goToToday = () => setCurrentMonth(new Date());

    const days = eachDayOfInterval({ start: startOfMonth(currentMonth), end: endOfMonth(currentMonth) });
    const startWeekday = startOfMonth(currentMonth).getDay();
    const emptyDaysPre = Array(startWeekday === 0 ? 6 : startWeekday - 1).fill(null);

    const getEventsForDay = (day: Date) => events.filter(e => isSameDay(new Date(e.start_time), day));
    const clientName = (id: string | null) => id ? (clients.find(c => c.id === id)?.name ?? id.slice(0, 8)) : null;

    return {
        currentMonth, events, clients, isLoading,
        showCreate, setShowCreate,
        creating, form, setForm,
        selected, setSelected,
        deleting,
        handleCreate, handleDelete,
        nextMonth, prevMonth, goToToday,
        days, emptyDaysPre,
        getEventsForDay, clientName,
    };
}
