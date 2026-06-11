"use client";

import { Calendar as CalendarIcon, ChevronLeft, ChevronRight, Plus } from "lucide-react";
import { format, isSameMonth, isToday } from "date-fns";
import { es } from "date-fns/locale";
import { useCalendario } from "./_hooks/useCalendario";
import { CreateEventModal } from "./_components/CreateEventModal";
import { EventDetailModal } from "./_components/EventDetailModal";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/ui/button";

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
        <div className="p-8 max-w-[1400px] mx-auto space-y-6">
            <PageHeader
                title="Calendario"
                description="Visualiza tus reuniones, demostraciones y recordatorios."
                icon={CalendarIcon}
                actions={
                    <div className="flex items-center gap-3">
                        <div className="flex items-center gap-1 bg-card border border-border rounded-lg p-1">
                            <Button variant="ghost" size="icon" className="h-8 w-8" onClick={prevMonth} aria-label="Mes anterior">
                                <ChevronLeft className="w-4 h-4" aria-hidden="true" />
                            </Button>
                            <Button variant="ghost" className="h-8 px-3 text-sm" onClick={goToToday}>Hoy</Button>
                            <Button variant="ghost" size="icon" className="h-8 w-8" onClick={nextMonth} aria-label="Mes siguiente">
                                <ChevronRight className="w-4 h-4" aria-hidden="true" />
                            </Button>
                        </div>
                        <Button onClick={() => setShowCreate(true)}>
                            <Plus className="w-4 h-4 mr-2" /> Agendar Cita
                        </Button>
                    </div>
                }
            />

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
