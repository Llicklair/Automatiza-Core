"use client";

import { useEffect, useState } from "react";
import { api, EventItem, Client } from "@/lib/api";
import { Calendar as CalendarIcon, ChevronLeft, ChevronRight, Plus, X, Trash2, MapPin, Clock } from "lucide-react";
import { format, addMonths, subMonths, startOfMonth, endOfMonth, eachDayOfInterval, isSameMonth, isSameDay, isToday } from "date-fns";
import { es } from "date-fns/locale";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";
import { logError } from "@/lib/logger";

const EVENT_TYPES = [
    { id: "meeting", label: "Reuni\u00f3n" },
    { id: "reminder", label: "Recordatorio" },
    { id: "task_deadline", label: "Vencimiento" },
];

const toLocalDatetime = (d: Date) => d.toISOString().slice(0, 16);

export default function CalendarPage() {
    const toast = useToastStore();
    const [currentMonth, setCurrentMonth] = useState(new Date());
    const [events, setEvents] = useState<EventItem[]>([]);
    const [clients, setClients] = useState<Client[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [showCreate, setShowCreate] = useState(false);
    const [creating, setCreating] = useState(false);
    const [form, setForm] = useState({
        title: "", description: "", type: "meeting", location_or_link: "", client_id: "",
        start_time: toLocalDatetime(new Date()),
        end_time: toLocalDatetime(new Date(Date.now() + 3600000)),
    });
    const [selected, setSelected] = useState<EventItem | null>(null);
    const [deleting, setDeleting] = useState(false);

    useEffect(() => { loadData(); }, []);

    const loadData = async () => {
        setIsLoading(true);
        try {
            const [evts, clis] = await Promise.all([api.crm.events.list(), api.erp.clients.list()]);
            setEvents(evts);
            setClients(clis);
        } catch (e) { logError("crm/calendario/page", e); }
        finally { setIsLoading(false); }
    };

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
        } catch { toast.error("Error al crear el evento"); }
        finally { setCreating(false); }
    };

    const handleDelete = async (id: string) => {
        if (!await showConfirm({ message: "¿Eliminar este evento?", confirmLabel: "Eliminar", confirmVariant: "danger" })) return;
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

    return (
        <div className="min-h-screen bg-[#09090b] text-white p-6 md:p-8">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-8">
                <div>
                    <h1 className="text-3xl font-light text-white flex items-center gap-3">
                        <div className="p-2 bg-indigo-500/10 rounded-xl"><CalendarIcon className="w-8 h-8 text-indigo-400" /></div>
                        Calendario
                    </h1>
                    <p className="text-zinc-400 mt-2 ml-14 text-sm">Visualiza tus reuniones, demostraciones y recordatorios.</p>
                </div>
                <div className="flex items-center gap-3">
                    <div className="flex items-center gap-1 bg-[#111113] border border-zinc-800 rounded-lg p-1 mr-4">
                        <button onClick={prevMonth} className="p-1.5 hover:bg-zinc-800 rounded-md transition-colors"><ChevronLeft className="w-4 h-4 text-zinc-400" /></button>
                        <button onClick={goToToday} className="px-3 py-1.5 text-sm font-medium hover:bg-zinc-800 rounded-md transition-colors text-zinc-300">Hoy</button>
                        <button onClick={nextMonth} className="p-1.5 hover:bg-zinc-800 rounded-md transition-colors"><ChevronRight className="w-4 h-4 text-zinc-400" /></button>
                    </div>
                    <button onClick={() => setShowCreate(true)} className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2.5 rounded-full font-medium transition-colors">
                        <Plus className="w-4 h-4" /> Agendar Cita
                    </button>
                </div>
            </div>

            <div className="bg-[#111113] border border-zinc-800 rounded-2xl overflow-hidden shadow-2xl flex flex-col h-[75vh]">
                <div className="px-6 py-4 border-b border-zinc-800 bg-[#161618]">
                    <h2 className="text-xl font-medium text-white capitalize">{format(currentMonth, "MMMM yyyy", { locale: es })}</h2>
                </div>
                <div className="grid grid-cols-7 border-b border-zinc-800 bg-[#09090b]">
                    {["Lun","Mar","Mie","Jue","Vie","Sab","Dom"].map(d => (
                        <div key={d} className="py-3 text-center text-xs font-medium text-zinc-500 uppercase tracking-wider">{d}</div>
                    ))}
                </div>
                <div className="flex-1 overflow-y-auto">
                    {isLoading ? (
                        <div className="flex justify-center items-center h-full"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500"></div></div>
                    ) : (
                        <div className="grid grid-cols-7 auto-rows-fr h-full min-h-[600px] border-l border-zinc-800/50">
                            {emptyDaysPre.map((_, i) => <div key={`e-${i}`} className="border-b border-r border-zinc-800/50 bg-[#09090b]/50 p-2 opacity-50"></div>)}
                            {days.map(day => {
                                const dayEvents = getEventsForDay(day);
                                const inMonth = isSameMonth(day, currentMonth);
                                return (
                                    <div key={day.toISOString()} className={`border-b border-r border-zinc-800/50 p-2 transition-colors hover:bg-[#161618]/50 min-h-[120px] ${inMonth ? "bg-[#111113]" : "bg-[#09090b]/50"}`}>
                                        <div className="flex justify-between items-start mb-2">
                                            <span className={`w-7 h-7 flex items-center justify-center rounded-full text-sm font-medium ${isToday(day) ? "bg-indigo-600 text-white" : inMonth ? "text-zinc-300" : "text-zinc-600"}`}>{format(day, "d")}</span>
                                            {dayEvents.length > 0 && <span className="text-[10px] bg-zinc-800 text-zinc-400 px-1.5 py-0.5 rounded">{dayEvents.length}</span>}
                                        </div>
                                        <div className="space-y-1.5 overflow-y-auto max-h-[100px]">
                                            {dayEvents.map(evt => (
                                                <div key={evt.id} onClick={() => setSelected(evt)}
                                                    className={`px-2 py-1.5 rounded text-xs border truncate cursor-pointer transition-colors ${evt.type === "meeting" ? "bg-indigo-500/10 border-indigo-500/20 text-indigo-300 hover:bg-indigo-500/20" : "bg-emerald-500/10 border-emerald-500/20 text-emerald-300 hover:bg-emerald-500/20"}`}>
                                                    <div className="font-semibold">{format(new Date(evt.start_time), "HH:mm")}</div>
                                                    <div className="truncate">{evt.title}</div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>
            </div>

            {showCreate && (
                <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                    <div className="bg-[#111113] border border-zinc-800 rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden">
                        <div className="p-6 border-b border-zinc-800 flex justify-between items-center bg-[#161618]">
                            <h2 className="text-lg font-medium text-white flex items-center gap-2"><CalendarIcon className="w-5 h-5 text-indigo-400" /> Agendar Cita</h2>
                            <button onClick={() => setShowCreate(false)} className="text-zinc-500 hover:text-white"><X className="w-5 h-5" /></button>
                        </div>
                        <form onSubmit={handleCreate} className="p-6 space-y-4">
                            <div>
                                <label className="block text-sm text-zinc-400 mb-1.5">T\u00edtulo *</label>
                                <input required value={form.title} onChange={e => setForm({ ...form, title: e.target.value })}
                                    className="w-full bg-[#09090b] border border-zinc-800 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-indigo-500" placeholder="Ej: Demo con Cliente XYZ" />
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm text-zinc-400 mb-1.5">Inicio *</label>
                                    <input required type="datetime-local" value={form.start_time} onChange={e => setForm({ ...form, start_time: e.target.value })}
                                        className="w-full bg-[#09090b] border border-zinc-800 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-indigo-500" />
                                </div>
                                <div>
                                    <label className="block text-sm text-zinc-400 mb-1.5">Fin *</label>
                                    <input required type="datetime-local" value={form.end_time} onChange={e => setForm({ ...form, end_time: e.target.value })}
                                        className="w-full bg-[#09090b] border border-zinc-800 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-indigo-500" />
                                </div>
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm text-zinc-400 mb-1.5">Tipo</label>
                                    <select value={form.type} onChange={e => setForm({ ...form, type: e.target.value })}
                                        className="w-full bg-[#09090b] border border-zinc-800 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-indigo-500">
                                        {EVENT_TYPES.map(t => <option key={t.id} value={t.id}>{t.label}</option>)}
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-sm text-zinc-400 mb-1.5">Cliente</label>
                                    <select value={form.client_id} onChange={e => setForm({ ...form, client_id: e.target.value })}
                                        className="w-full bg-[#09090b] border border-zinc-800 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-indigo-500">
                                        <option value="">Sin cliente</option>
                                        {clients.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                                    </select>
                                </div>
                            </div>
                            <div>
                                <label className="block text-sm text-zinc-400 mb-1.5">Enlace / Ubicaci\u00f3n</label>
                                <input value={form.location_or_link} onChange={e => setForm({ ...form, location_or_link: e.target.value })}
                                    className="w-full bg-[#09090b] border border-zinc-800 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-indigo-500"
                                    placeholder="https://meet.google.com/... o direcci\u00f3n" />
                            </div>
                            <div>
                                <label className="block text-sm text-zinc-400 mb-1.5">Descripci\u00f3n</label>
                                <textarea value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} rows={2}
                                    className="w-full bg-[#09090b] border border-zinc-800 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-indigo-500 resize-none"
                                    placeholder="Notas del evento..." />
                            </div>
                            <div className="flex justify-end gap-3 pt-2 border-t border-zinc-800">
                                <button type="button" onClick={() => setShowCreate(false)} className="px-5 py-2.5 text-zinc-400 hover:text-white">Cancelar</button>
                                <button type="submit" disabled={creating} className="bg-indigo-600 hover:bg-indigo-500 text-white px-6 py-2.5 rounded-lg font-medium disabled:opacity-50">
                                    {creating ? "Guardando..." : "Agendar"}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {selected && (
                <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4" onClick={() => setSelected(null)}>
                    <div className="bg-[#111113] border border-zinc-800 rounded-2xl w-full max-w-md shadow-2xl" onClick={e => e.stopPropagation()}>
                        <div className="p-5 border-b border-zinc-800 flex justify-between items-start bg-[#161618]">
                            <div>
                                <h2 className="text-lg font-medium text-white">{selected.title}</h2>
                                <span className="text-xs text-indigo-400 capitalize">{selected.type}</span>
                            </div>
                            <button onClick={() => setSelected(null)} className="text-zinc-500 hover:text-white ml-4"><X className="w-5 h-5" /></button>
                        </div>
                        <div className="p-5 space-y-3">
                            <div className="flex items-center gap-2 text-sm text-zinc-400">
                                <Clock className="w-4 h-4 shrink-0" />
                                {format(new Date(selected.start_time), "dd MMM yyyy, HH:mm", { locale: es })} - {format(new Date(selected.end_time), "HH:mm")}
                            </div>
                            {selected.location_or_link && (
                                <div className="flex items-center gap-2 text-sm text-zinc-400">
                                    <MapPin className="w-4 h-4 shrink-0" />
                                    {selected.location_or_link.startsWith("http")
                                        ? <a href={selected.location_or_link} target="_blank" rel="noreferrer" className="text-indigo-400 hover:underline truncate">{selected.location_or_link}</a>
                                        : selected.location_or_link}
                                </div>
                            )}
                            {clientName(selected.client_id) && (
                                <div className="text-sm text-zinc-400">Cliente: <span className="text-white">{clientName(selected.client_id)}</span></div>
                            )}
                            {selected.description && <p className="text-sm text-zinc-400 pt-2 border-t border-zinc-800">{selected.description}</p>}
                        </div>
                        <div className="p-5 border-t border-zinc-800 flex justify-end">
                            <button onClick={() => handleDelete(selected.id)} disabled={deleting}
                                className="flex items-center gap-2 text-sm text-red-400 hover:text-red-300 disabled:opacity-50">
                                <Trash2 className="w-4 h-4" /> {deleting ? "Eliminando..." : "Eliminar evento"}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
