"use client";

import { Search, Plus, Bot, UserCircle, Trash2, Activity as ActivityIcon } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { es } from "date-fns/locale";
import { useActividades } from "./_hooks/useActividades";
import { CreateActivityModal } from "./_components/CreateActivityModal";

export default function ActivitiesPage() {
    const {
        activities, clients, isLoading,
        showModal, setShowModal,
        selectedClient, setSelectedClient,
        type, setType,
        description, setDescription,
        isSubmitting,
        handleCreate, deleteActivity,
        getActivityIcon, getClientName,
    } = useActividades();

    return (
        <div className="min-h-screen bg-background text-foreground p-8">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-8">
                <div>
                    <h1 className="text-3xl font-light text-foreground flex items-center gap-3">
                        <div className="p-2 bg-pink-500/10 rounded-xl">
                            <ActivityIcon className="w-8 h-8 text-pink-400" />
                        </div>
                        Registro de Actividades
                    </h1>
                    <p className="text-muted-foreground mt-2 ml-14 text-sm max-w-2xl">
                        Muro de interacciones. Registra manualmente tus llamadas o revisa los resúmenes automáticos que la IA extrae de tus correos y reuniones.
                    </p>
                </div>

                <div className="flex gap-3">
                    <button
                        onClick={() => setShowModal(true)}
                        className="flex items-center gap-2 bg-pink-600 hover:bg-pink-500 text-foreground shadow-lg shadow-pink-500/20 px-5 py-2.5 rounded-full font-medium transition-colors"
                    >
                        <Plus className="w-4 h-4" />
                        Registrar Interacción
                    </button>
                </div>
            </div>

            <div className="bg-card border border-border rounded-2xl p-6 shadow-xl max-w-5xl">
                <div className="flex items-center gap-3 mb-8 pb-4 border-b border-border">
                    <div className="relative flex-1">
                        <Search className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
                        <input
                            type="text"
                            placeholder="Buscar en el historial (ej. 'presupuesto', 'llamada de seguimiento')..."
                            className="w-full bg-background border border-border text-sm text-foreground rounded-lg pl-10 pr-4 py-2 focus:outline-none focus:border-pink-500 transition-colors"
                        />
                    </div>
                    <select className="bg-background border border-border text-sm text-foreground rounded-lg px-4 py-2 focus:outline-none focus:border-pink-500">
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
                        <ActivityIcon className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                        <h3 className="text-lg font-medium text-foreground">Aún no hay interacciones</h3>
                        <p className="text-muted-foreground mt-2 max-w-md mx-auto">
                            Cuando envíes un correo, llames a un cliente o la IA procese un buzón, aparecerá aquí como un hilo temporal.
                        </p>
                    </div>
                ) : (
                    <div className="relative pl-4 space-y-8 before:absolute before:inset-0 before:ml-[31px] before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-zinc-800 before:to-transparent">
                        {activities.map((act) => {
                            const source = act.metadata_json?.source;
                            return (
                                <div key={act.id} className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
                                    <div className="flex items-center justify-center w-10 h-10 rounded-full border-4 border-border bg-muted shadow shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 z-10 transition-transform hover:scale-110">
                                        {getActivityIcon(act.type, source)}
                                    </div>
                                    <div className="w-[calc(100%-4rem)] md:w-[calc(50%-2.5rem)] p-4 rounded-xl border border-border bg-muted/50 shadow-sm hover:shadow-md hover:bg-muted transition-all">
                                        <div className="flex items-center justify-between mb-2">
                                            <div className="flex items-center gap-2">
                                                <UserCircle className="w-4 h-4 text-muted-foreground" />
                                                <span className="font-medium text-sm text-foreground">{getClientName(act.client_id)}</span>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <time className="text-xs font-mono text-muted-foreground">
                                                    {formatDistanceToNow(new Date(act.created_at), { addSuffix: true, locale: es })}
                                                </time>
                                                <button
                                                    onClick={() => deleteActivity(act.id)}
                                                    className="p-1 rounded text-muted-foreground hover:text-red-400 hover:bg-red-500/10 transition-colors opacity-0 group-hover:opacity-100"
                                                    title="Eliminar"
                                                >
                                                    <Trash2 className="w-3.5 h-3.5" />
                                                </button>
                                            </div>
                                        </div>
                                        <div className="text-sm text-muted-foreground whitespace-pre-wrap leading-relaxed">
                                            {act.description}
                                        </div>
                                        {source === 'ai' && (
                                            <div className="mt-3 pt-3 border-t border-border flex items-center gap-2 text-xs text-primary font-medium">
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

            {showModal && (
                <CreateActivityModal
                    clients={clients}
                    selectedClient={selectedClient}
                    setSelectedClient={setSelectedClient}
                    type={type}
                    setType={setType}
                    description={description}
                    setDescription={setDescription}
                    isSubmitting={isSubmitting}
                    onSubmit={handleCreate}
                    onClose={() => setShowModal(false)}
                />
            )}
        </div>
    );
}
