"use client";

import { useEffect, useState } from "react";
import { api, EventItem, Client } from "@/lib/api";
import { Video, Plus, Search, Clock, MapPin, MoreVertical, ArrowUpRight, VideoOff, X, Trash2 } from "lucide-react";
import { format, isPast, isToday } from "date-fns";
import { es } from "date-fns/locale";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";
import { logError } from "@/lib/logger";

const toLocalDatetime = (d: Date) => d.toISOString().slice(0, 16);

export default function MeetingsPage() {
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

    const renderCard = (m: EventItem, isPastMeeting: boolean) => (
        <div key={m.id} className={`p-5 rounded-2xl border transition-all ${isPastMeeting ? "bg-[#09090b]/40 border-zinc-800/40 opacity-70" : "bg-[#161618] border-zinc-800 hover:border-blue-500/30"}`}>
            <div className="flex justify-between items-start mb-4">
                <div className="flex items-center gap-3">
                    <div className={`p-2.5 rounded-xl ${isPastMeeting ? "bg-zinc-800/50" : "bg-blue-500/10"}`}>
                        <Video className={`w-5 h-5 ${isPastMeeting ? "text-zinc-500" : "text-blue-400"}`} />
                    </div>
                    <div>
                        <h3 className={`font-medium ${isPastMeeting ? "text-zinc-400" : "text-zinc-100"}`}>{m.title}</h3>
                        <p className="text-xs text-zinc-500 flex items-center gap-1.5 mt-0.5">
                            <Clock className="w-3 h-3" />
                            {format(new Date(m.start_time), "dd MMM, HH:mm", { locale: es })} - {format(new Date(m.end_time), "HH:mm")}
                        </p>
                    </div>
                </div>
                <button onClick={() => handleDelete(m.id)} className="text-zinc-600 hover:text-red-400 p-1 transition-colors">
                    <Trash2 className="w-4 h-4" />
                </button>
            </div>
            {m.description && <p className="text-sm text-zinc-400 mb-4 line-clamp-2">{m.description}</p>}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-xs text-zinc-500">
                    <MapPin className="w-3.5 h-3.5" />
                    <span className="truncate max-w-[150px]">{m.location_or_link || "Ubicaci\u00f3n no especificada"}</span>
                </div>
                {!isPastMeeting && m.location_or_link && m.location_or_link.startsWith("http") && (
                    <a href={m.location_or_link} target="_blank" rel="noreferrer"
                        className="flex items-center gap-1 text-xs font-medium text-blue-400 hover:text-blue-300 bg-blue-500/10 px-3 py-1.5 rounded-lg">
                        Unirse <ArrowUpRight className="w-3 h-3" />
                    </a>
                )}
            </div>
        </div>
    );

    return (
        <div className="min-h-screen bg-[#09090b] text-white p-8">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-8">
                <div>
                    <h1 className="text-3xl font-light text-white flex items-center gap-3">
                        <div className="p-2 bg-blue-500/10 rounded-xl"><Video className="w-8 h-8 text-blue-400" /></div>
                        Reuniones (Meet)
                    </h1>
                    <p className="text-zinc-400 mt-2 ml-14 text-sm">Gestiona tus videollamadas con clientes.</p>
                </div>
                <button onClick={() => setShowCreate(true)} className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white px-5 py-2.5 rounded-full font-medium transition-colors">
                    <Plus className="w-4 h-4" /> Programar Reuni\u00f3n
                </button>
            </div>

            <div className="bg-[#111113] border border-zinc-800 rounded-2xl p-6 shadow-xl">
                <div className="flex items-center gap-4 mb-8">
                    <div className="relative flex-1 max-w-md">
                        <Search className="w-4 h-4 text-zinc-500 absolute left-3 top-1/2 -translate-y-1/2" />
                        <input type="text" placeholder="Buscar reuniones..." value={search} onChange={e => setSearch(e.target.value)}
                            className="w-full bg-[#09090b] border border-zinc-800 text-sm text-white rounded-lg pl-10 pr-4 py-2 focus:outline-none focus:border-blue-500" />
                    </div>
                </div>

                {isLoading ? (
                    <div className="flex justify-center p-12"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div></div>
                ) : meetings.length === 0 ? (
                    <div className="text-center py-20 border-2 border-dashed border-zinc-800 rounded-2xl">
                        <VideoOff className="w-12 h-12 text-zinc-700 mx-auto mb-4" />
                        <h3 className="text-lg font-medium text-zinc-300">Despejado</h3>
                        <p className="text-zinc-500 mt-2">No tienes reuniones agendadas.</p>
                    </div>
                ) : (
                    <div className="space-y-10">
                        {upcoming.length > 0 && (
                            <div>
                                <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-4 flex items-center gap-2">
                                    <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse"></div>
                                    Pr\u00f3ximas y Hoy ({upcoming.length})
                                </h2>
                                <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">{upcoming.map(m => renderCard(m, false))}</div>
                            </div>
                        )}
                        {past.length > 0 && (
                            <div>
                                <h2 className="text-sm font-semibold text-zinc-500 uppercase tracking-wider mb-4">Finalizadas ({past.length})</h2>
                                <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">{past.map(m => renderCard(m, true))}</div>
                            </div>
                        )}
                    </div>
                )}
            </div>

            {showCreate && (
                <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                    <div className="bg-[#111113] border border-zinc-800 rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden">
                        <div className="p-6 border-b border-zinc-800 flex justify-between items-center bg-[#161618]">
                            <h2 className="text-lg font-medium text-white flex items-center gap-2"><Video className="w-5 h-5 text-blue-400" /> Programar Reuni\u00f3n</h2>
                            <button onClick={() => setShowCreate(false)} className="text-zinc-500 hover:text-white"><X className="w-5 h-5" /></button>
                        </div>
                        <form onSubmit={handleCreate} className="p-6 space-y-4">
                            <div>
                                <label className="block text-sm text-zinc-400 mb-1.5">T\u00edtulo *</label>
                                <input required value={form.title} onChange={e => setForm({ ...form, title: e.target.value })}
                                    className="w-full bg-[#09090b] border border-zinc-800 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-blue-500"
                                    placeholder="Ej: Llamada de seguimiento con ACME" />
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm text-zinc-400 mb-1.5">Inicio *</label>
                                    <input required type="datetime-local" value={form.start_time} onChange={e => setForm({ ...form, start_time: e.target.value })}
                                        className="w-full bg-[#09090b] border border-zinc-800 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-blue-500" />
                                </div>
                                <div>
                                    <label className="block text-sm text-zinc-400 mb-1.5">Fin *</label>
                                    <input required type="datetime-local" value={form.end_time} onChange={e => setForm({ ...form, end_time: e.target.value })}
                                        className="w-full bg-[#09090b] border border-zinc-800 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-blue-500" />
                                </div>
                            </div>
                            <div>
                                <label className="block text-sm text-zinc-400 mb-1.5">Enlace (Meet/Zoom/Teams)</label>
                                <input value={form.location_or_link} onChange={e => setForm({ ...form, location_or_link: e.target.value })}
                                    className="w-full bg-[#09090b] border border-zinc-800 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-blue-500"
                                    placeholder="https://meet.google.com/..." />
                            </div>
                            <div>
                                <label className="block text-sm text-zinc-400 mb-1.5">Cliente</label>
                                <select value={form.client_id} onChange={e => setForm({ ...form, client_id: e.target.value })}
                                    className="w-full bg-[#09090b] border border-zinc-800 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-blue-500">
                                    <option value="">Sin cliente</option>
                                    {clients.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                                </select>
                            </div>
                            <div>
                                <label className="block text-sm text-zinc-400 mb-1.5">Descripci\u00f3n</label>
                                <textarea value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} rows={2}
                                    className="w-full bg-[#09090b] border border-zinc-800 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-blue-500 resize-none"
                                    placeholder="Agenda de la reuni\u00f3n..." />
                            </div>
                            <div className="flex justify-end gap-3 pt-2 border-t border-zinc-800">
                                <button type="button" onClick={() => setShowCreate(false)} className="px-5 py-2.5 text-zinc-400 hover:text-white">Cancelar</button>
                                <button type="submit" disabled={creating} className="bg-blue-600 hover:bg-blue-500 text-white px-6 py-2.5 rounded-lg font-medium disabled:opacity-50">
                                    {creating ? "Guardando..." : "Programar"}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
