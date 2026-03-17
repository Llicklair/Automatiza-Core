"use client";

import { useEffect, useState } from "react";
import { api, Activity, Client } from "@/lib/api";
import {
    Phone, Mail, StickyNote, Bot, Search, Plus,
    CalendarCheck, UserCircle, Activity as ActivityIcon, Trash2
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { es } from "date-fns/locale";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";
import { logError } from "@/lib/logger";

export default function ActivitiesPage() {
    const toast = useToastStore();
    const [activities, setActivities] = useState<Activity[]>([]);
    const [clients, setClients] = useState<Client[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);

    // Formulario Nueva Actividad
    const [selectedClient, setSelectedClient] = useState("");
    const [type, setType] = useState("note");
    const [description, setDescription] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        setIsLoading(true);
        try {
            const [actRes, cliRes] = await Promise.all([
                api.crm.activities.list(),
                api.erp.clients.list()
            ]);
            setActivities(actRes);
            setClients(cliRes);
        } catch (error) {
            logError("crm/actividades/page", error);
        } finally {
            setIsLoading(false);
        }
    };

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsSubmitting(true);
        try {
            await api.crm.activities.create({
                client_id: selectedClient || null,
                type: type,
                description: description,
                metadata_json: { source: "manual" }
            });
            setShowModal(false);
            setDescription("");
            setType("note");
            setSelectedClient("");
            await loadData();
        } catch (error) {
            logError("crm/actividades/page", error);
            toast.error("Error al registrar actividad");
        } finally {
            setIsSubmitting(false);
        }
    };

    const deleteActivity = async (id: string) => {
        if (!await showConfirm({ message: "¿Eliminar esta actividad del historial?", confirmLabel: "Eliminar", confirmVariant: "danger" })) return;
        try {
            await api.crm.activities.delete(id);
            setActivities(prev => prev.filter(a => a.id !== id));
        } catch {
            toast.error("Error al eliminar la actividad");
        }
    };

    const getActivityIcon = (actType: string, source?: string) => {
        if (source === "ai") return <Bot className="w-5 h-5 text-indigo-400" />;

        switch (actType) {
            case "call": return <Phone className="w-5 h-5 text-emerald-400" />;
            case "email": return <Mail className="w-5 h-5 text-blue-400" />;
            case "meeting_log": return <CalendarCheck className="w-5 h-5 text-purple-400" />;
            default: return <StickyNote className="w-5 h-5 text-amber-400" />; // note
        }
    };

    const getClientName = (clientId: string | null) => {
        if (!clientId) return "Sin asignar";
        const c = clients.find(c => c.id === clientId);
        return c ? c.name : "Cliente Desconocido";
    };

    return (
        <div className="min-h-screen bg-[#09090b] text-white p-8">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-8">
                <div>
                    <h1 className="text-3xl font-light text-white flex items-center gap-3">
                        <div className="p-2 bg-pink-500/10 rounded-xl">
                            <ActivityIcon className="w-8 h-8 text-pink-400" />
                        </div>
                        Registro de Actividades
                    </h1>
                    <p className="text-zinc-400 mt-2 ml-14 text-sm max-w-2xl">
                        Muro de interacciones. Registra manualmente tus llamadas o revisa los resúmenes automáticos que la IA extrae de tus correos y reuniones.
                    </p>
                </div>

                <div className="flex gap-3">
                    <button
                        onClick={() => setShowModal(true)}
                        className="flex items-center gap-2 bg-pink-600 hover:bg-pink-500 text-white shadow-lg shadow-pink-500/20 px-5 py-2.5 rounded-full font-medium transition-colors"
                    >
                        <Plus className="w-4 h-4" />
                        Registrar Interacción
                    </button>
                </div>
            </div>

            <div className="bg-[#111113] border border-zinc-800 rounded-2xl p-6 shadow-xl max-w-5xl">
                <div className="flex items-center gap-3 mb-8 pb-4 border-b border-zinc-800">
                    <div className="relative flex-1">
                        <Search className="w-4 h-4 text-zinc-500 absolute left-3 top-1/2 -translate-y-1/2" />
                        <input
                            type="text"
                            placeholder="Buscar en el historial (ej. 'presupuesto', 'llamada de seguimiento')..."
                            className="w-full bg-[#09090b] border border-zinc-800 text-sm text-white rounded-lg pl-10 pr-4 py-2 focus:outline-none focus:border-pink-500 transition-colors"
                        />
                    </div>
                    <select className="bg-[#09090b] border border-zinc-800 text-sm text-zinc-300 rounded-lg px-4 py-2 focus:outline-none focus:border-pink-500">
                        <option value="all">Todos los clientes</option>
                        {clients.map(c => (
                            <option key={c.id} value={c.id}>{c.name}</option>
                        ))}
                    </select>
                </div>

                {isLoading ? (
                    <div className="flex justify-center p-12">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-pink-500"></div>
                    </div>
                ) : activities.length === 0 ? (
                    <div className="text-center py-20">
                        <ActivityIcon className="w-12 h-12 text-zinc-700 mx-auto mb-4" />
                        <h3 className="text-lg font-medium text-zinc-300">Aún no hay interacciones</h3>
                        <p className="text-zinc-500 mt-2 max-w-md mx-auto">
                            Cuando envíes un correo, llames a un cliente o la IA procese un buzón, aparecerá aquí como un hilo temporal.
                        </p>
                    </div>
                ) : (
                    <div className="relative pl-4 space-y-8 before:absolute before:inset-0 before:ml-[31px] before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-zinc-800 before:to-transparent">
                        {activities.map((act, index) => {
                            const source = act.metadata_json?.source;
                            return (
                                <div key={act.id} className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
                                    <div className="flex items-center justify-center w-10 h-10 rounded-full border-4 border-[#111113] bg-[#161618] shadow shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 z-10 transition-transform hover:scale-110">
                                        {getActivityIcon(act.type, source)}
                                    </div>
                                    <div className="w-[calc(100%-4rem)] md:w-[calc(50%-2.5rem)] p-4 rounded-xl border border-zinc-800/60 bg-[#161618]/50 shadow-sm hover:shadow-md hover:bg-[#161618] transition-all">
                                        <div className="flex items-center justify-between mb-2">
                                            <div className="flex items-center gap-2">
                                                <UserCircle className="w-4 h-4 text-zinc-500" />
                                                <span className="font-medium text-sm text-zinc-200">{getClientName(act.client_id)}</span>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <time className="text-xs font-mono text-zinc-500">
                                                    {formatDistanceToNow(new Date(act.created_at), { addSuffix: true, locale: es })}
                                                </time>
                                                <button
                                                    onClick={() => deleteActivity(act.id)}
                                                    className="p-1 rounded text-zinc-600 hover:text-red-400 hover:bg-red-500/10 transition-colors opacity-0 group-hover:opacity-100"
                                                    title="Eliminar"
                                                >
                                                    <Trash2 className="w-3.5 h-3.5" />
                                                </button>
                                            </div>
                                        </div>
                                        <div className="text-sm text-zinc-400 whitespace-pre-wrap leading-relaxed">
                                            {act.description}
                                        </div>
                                        {source === 'ai' && (
                                            <div className="mt-3 pt-3 border-t border-zinc-800/50 flex items-center gap-2 text-xs text-indigo-400 font-medium">
                                                <Bot className="w-3.5 h-3.5" /> Generado automáticamente por IA
                                            </div>
                                        )}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>

            {/* Modal */}
            {showModal && (
                <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                    <div className="bg-[#111113] border border-zinc-800 rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl">
                        <div className="p-5 border-b border-zinc-800 flex justify-between items-center bg-[#161618]">
                            <h2 className="text-lg font-medium text-white flex items-center gap-2">
                                <Plus className="w-4 h-4 text-pink-400" />
                                Registrar Actividad
                            </h2>
                            <button onClick={() => setShowModal(false)} className="text-zinc-400 hover:text-white">✕</button>
                        </div>

                        <form onSubmit={handleCreate} className="p-6 space-y-4">
                            <div>
                                <label className="block text-sm text-zinc-400 mb-1.5">Cliente (Opcional)</label>
                                <select
                                    value={selectedClient}
                                    onChange={e => setSelectedClient(e.target.value)}
                                    className="w-full bg-[#09090b] border border-zinc-800 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-pink-500"
                                >
                                    <option value="">Ninguno / General</option>
                                    {clients.map(c => (
                                        <option key={c.id} value={c.id}>{c.name}</option>
                                    ))}
                                </select>
                            </div>

                            <div>
                                <label className="block text-sm text-zinc-400 mb-1.5">Tipo de interacción</label>
                                <div className="grid grid-cols-4 gap-2">
                                    {[
                                        { id: 'note', icon: StickyNote, label: 'Nota' },
                                        { id: 'call', icon: Phone, label: 'Llamada' },
                                        { id: 'email', icon: Mail, label: 'Email' },
                                        { id: 'meeting_log', icon: CalendarCheck, label: 'Reunión' }
                                    ].map(t => (
                                        <button
                                            key={t.id}
                                            type="button"
                                            onClick={() => setType(t.id)}
                                            className={`flex flex-col items-center justify-center p-3 rounded-xl border transition-colors ${type === t.id
                                                ? 'bg-pink-500/10 border-pink-500/50 text-pink-400'
                                                : 'bg-[#09090b] border-zinc-800 text-zinc-500 hover:border-zinc-700 hover:text-zinc-300'
                                                }`}
                                        >
                                            <t.icon className="w-5 h-5 mb-1.5" />
                                            <span className="text-xs font-medium">{t.label}</span>
                                        </button>
                                    ))}
                                </div>
                            </div>

                            <div>
                                <label className="block text-sm text-zinc-400 mb-1.5">Resumen o Descripción</label>
                                <textarea
                                    required
                                    rows={4}
                                    value={description}
                                    onChange={e => setDescription(e.target.value)}
                                    placeholder="¿De qué hablasteis? ¿Qué se acordó?..."
                                    className="w-full bg-[#09090b] border border-zinc-800 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-pink-500 resize-none"
                                />
                            </div>

                            <div className="pt-4 flex justify-end gap-3 mt-4">
                                <button
                                    type="button"
                                    onClick={() => setShowModal(false)}
                                    className="px-5 py-2.5 text-zinc-300 hover:text-white transition-colors font-medium border border-transparent hover:border-zinc-700 rounded-lg"
                                >
                                    Cancelar
                                </button>
                                <button
                                    type="submit"
                                    disabled={isSubmitting || !description}
                                    className="bg-pink-600 hover:bg-pink-500 text-white px-6 py-2.5 rounded-lg font-medium transition-colors shadow-lg shadow-pink-500/20 disabled:opacity-50"
                                >
                                    {isSubmitting ? "Guardando..." : "Registrar"}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
