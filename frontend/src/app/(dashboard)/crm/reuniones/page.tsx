"use client";

import { Video, Plus, Search, Clock, MapPin, ArrowUpRight, VideoOff, Trash2 } from "lucide-react";
import { format } from "date-fns";
import { es } from "date-fns/locale";
import { EventItem } from "@/lib/api";
import { useReuniones } from "./_hooks/useReuniones";
import { CreateMeetingModal } from "./_components/CreateMeetingModal";

export default function MeetingsPage() {
    const {
        meetings, clients, isLoading,
        search, setSearch,
        showCreate, setShowCreate,
        creating, form, setForm,
        handleCreate, handleDelete,
        upcoming, past,
    } = useReuniones();

    const renderCard = (m: EventItem, isPastMeeting: boolean) => (
        <div key={m.id} className={`p-5 rounded-2xl border transition-all ${isPastMeeting ? "bg-background/40 border-border opacity-70" : "bg-muted border-border hover:border-blue-500/30"}`}>
            <div className="flex justify-between items-start mb-4">
                <div className="flex items-center gap-3">
                    <div className={`p-2.5 rounded-xl ${isPastMeeting ? "bg-muted" : "bg-blue-500/10"}`}>
                        <Video className={`w-5 h-5 ${isPastMeeting ? "text-muted-foreground" : "text-blue-400"}`} />
                    </div>
                    <div>
                        <h3 className={`font-medium ${isPastMeeting ? "text-muted-foreground" : "text-foreground"}`}>{m.title}</h3>
                        <p className="text-xs text-muted-foreground flex items-center gap-1.5 mt-0.5">
                            <Clock className="w-3 h-3" />
                            {format(new Date(m.start_time), "dd MMM, HH:mm", { locale: es })} - {format(new Date(m.end_time), "HH:mm")}
                        </p>
                    </div>
                </div>
                <button onClick={() => handleDelete(m.id)} className="text-muted-foreground hover:text-red-400 p-1 transition-colors">
                    <Trash2 className="w-4 h-4" />
                </button>
            </div>
            {m.description && <p className="text-sm text-muted-foreground mb-4 line-clamp-2">{m.description}</p>}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <MapPin className="w-3.5 h-3.5" />
                    <span className="truncate max-w-[150px]">{m.location_or_link || "Ubicación no especificada"}</span>
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
        <div className="min-h-screen bg-background text-foreground p-8">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-8">
                <div>
                    <h1 className="text-3xl font-light text-foreground flex items-center gap-3">
                        <div className="p-2 bg-blue-500/10 rounded-xl"><Video className="w-8 h-8 text-blue-400" /></div>
                        Reuniones (Meet)
                    </h1>
                    <p className="text-muted-foreground mt-2 ml-14 text-sm">Gestiona tus videollamadas con clientes.</p>
                </div>
                <button onClick={() => setShowCreate(true)} className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-foreground px-5 py-2.5 rounded-full font-medium transition-colors">
                    <Plus className="w-4 h-4" /> Programar Reunión
                </button>
            </div>

            <div className="bg-card border border-border rounded-2xl p-6 shadow-xl">
                <div className="flex items-center gap-4 mb-8">
                    <div className="relative flex-1 max-w-md">
                        <Search className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
                        <input type="text" placeholder="Buscar reuniones..." value={search} onChange={e => setSearch(e.target.value)}
                            className="w-full bg-background border border-border text-sm text-foreground rounded-lg pl-10 pr-4 py-2 focus:outline-none focus:border-blue-500" />
                    </div>
                </div>

                {isLoading ? (
                    <div className="flex justify-center p-12"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div></div>
                ) : meetings.length === 0 ? (
                    <div className="text-center py-20 border-2 border-dashed border-border rounded-2xl">
                        <VideoOff className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                        <h3 className="text-lg font-medium text-foreground">Despejado</h3>
                        <p className="text-muted-foreground mt-2">No tienes reuniones agendadas.</p>
                    </div>
                ) : (
                    <div className="space-y-10">
                        {upcoming.length > 0 && (
                            <div>
                                <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-4 flex items-center gap-2">
                                    <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse"></div>
                                    Próximas y Hoy ({upcoming.length})
                                </h2>
                                <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">{upcoming.map(m => renderCard(m, false))}</div>
                            </div>
                        )}
                        {past.length > 0 && (
                            <div>
                                <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-4">Finalizadas ({past.length})</h2>
                                <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">{past.map(m => renderCard(m, true))}</div>
                            </div>
                        )}
                    </div>
                )}
            </div>

            {showCreate && (
                <CreateMeetingModal
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
