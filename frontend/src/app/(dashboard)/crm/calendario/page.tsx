"use client";

import { Calendar as CalendarIcon, ChevronLeft, ChevronRight, Plus } from "lucide-react";
import { format, isSameMonth, isToday } from "date-fns";
import { es } from "date-fns/locale";
import { useCalendario } from "./_hooks/useCalendario";
import { CreateEventModal } from "./_components/CreateEventModal";
import { EventDetailModal } from "./_components/EventDetailModal";

export default function CalendarPage() {
    const {
        currentMonth, clients, isLoading,
        showCreate, setShowCreate,
        creating, form, setForm,
        selected, setSelected,
        deleting,
        handleCreate, handleDelete,
        nextMonth, prevMonth, goToToday,
        days, emptyDaysPre,
        getEventsForDay, clientName,
    } = useCalendario();

    return (
        <div className="min-h-screen bg-background text-foreground p-6 md:p-8">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-8">
                <div>
                    <h1 className="text-3xl font-light text-foreground flex items-center gap-3">
                        <div className="p-2 bg-primary/10 rounded-xl"><CalendarIcon className="w-8 h-8 text-primary" /></div>
                        Calendario
                    </h1>
                    <p className="text-muted-foreground mt-2 ml-14 text-sm">Visualiza tus reuniones, demostraciones y recordatorios.</p>
                </div>
                <div className="flex items-center gap-3">
                    <div className="flex items-center gap-1 bg-card border border-border rounded-lg p-1 mr-4">
                        <button onClick={prevMonth} className="p-1.5 hover:bg-muted rounded-md transition-colors"><ChevronLeft className="w-4 h-4 text-muted-foreground" /></button>
                        <button onClick={goToToday} className="px-3 py-1.5 text-sm font-medium hover:bg-muted rounded-md transition-colors text-foreground">Hoy</button>
                        <button onClick={nextMonth} className="p-1.5 hover:bg-muted rounded-md transition-colors"><ChevronRight className="w-4 h-4 text-muted-foreground" /></button>
                    </div>
                    <button onClick={() => setShowCreate(true)} className="flex items-center gap-2 bg-primary hover:bg-primary text-foreground px-5 py-2.5 rounded-full font-medium transition-colors">
                        <Plus className="w-4 h-4" /> Agendar Cita
                    </button>
                </div>
            </div>

            <div className="bg-card border border-border rounded-2xl overflow-hidden shadow-2xl flex flex-col h-[75vh]">
                <div className="px-6 py-4 border-b border-border bg-muted">
                    <h2 className="text-xl font-medium text-foreground capitalize">{format(currentMonth, "MMMM yyyy", { locale: es })}</h2>
                </div>
                <div className="grid grid-cols-7 border-b border-border bg-background">
                    {["Lun","Mar","Mie","Jue","Vie","Sab","Dom"].map(d => (
                        <div key={d} className="py-3 text-center text-xs font-medium text-muted-foreground uppercase tracking-wider">{d}</div>
                    ))}
                </div>
                <div className="flex-1 overflow-y-auto">
                    {isLoading ? (
                        <div className="flex justify-center items-center h-full"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div></div>
                    ) : (
                        <div className="grid grid-cols-7 auto-rows-fr h-full min-h-[600px] border-l border-border">
                            {emptyDaysPre.map((_, i) => <div key={`e-${i}`} className="border-b border-r border-border bg-background/50 p-2 opacity-50"></div>)}
                            {days.map(day => {
                                const dayEvents = getEventsForDay(day);
                                const inMonth = isSameMonth(day, currentMonth);
                                return (
                                    <div key={day.toISOString()} className={`border-b border-r border-border p-2 transition-colors hover:bg-muted/50 min-h-[120px] ${inMonth ? "bg-card" : "bg-background/50"}`}>
                                        <div className="flex justify-between items-start mb-2">
                                            <span className={`w-7 h-7 flex items-center justify-center rounded-full text-sm font-medium ${isToday(day) ? "bg-primary text-foreground" : inMonth ? "text-foreground" : "text-muted-foreground"}`}>{format(day, "d")}</span>
                                            {dayEvents.length > 0 && <span className="text-[10px] bg-muted text-muted-foreground px-1.5 py-0.5 rounded">{dayEvents.length}</span>}
                                        </div>
                                        <div className="space-y-1.5 overflow-y-auto max-h-[100px]">
                                            {dayEvents.map(evt => (
                                                <div key={evt.id} onClick={() => setSelected(evt)}
                                                    className={`px-2 py-1.5 rounded text-xs border truncate cursor-pointer transition-colors ${evt.type === "meeting" ? "bg-primary/10 border-primary/20 text-primary hover:bg-primary/20" : "bg-emerald-500/10 border-emerald-500/20 text-emerald-300 hover:bg-emerald-500/20"}`}>
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
                <CreateEventModal
                    clients={clients}
                    form={form}
                    setForm={setForm}
                    creating={creating}
                    onSubmit={handleCreate}
                    onClose={() => setShowCreate(false)}
                />
            )}

            {selected && (
                <EventDetailModal
                    event={selected}
                    clientName={clientName}
                    deleting={deleting}
                    onDelete={handleDelete}
                    onClose={() => setSelected(null)}
                />
            )}
        </div>
    );
}
