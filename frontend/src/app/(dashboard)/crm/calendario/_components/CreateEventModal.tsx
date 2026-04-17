"use client";

import { Client } from "@/lib/api";
import { Calendar as CalendarIcon, X } from "lucide-react";

const EVENT_TYPES = [
    { id: "meeting", label: "Reunión" },
    { id: "reminder", label: "Recordatorio" },
    { id: "task_deadline", label: "Vencimiento" },
];

interface FormState {
    title: string;
    description: string;
    type: string;
    location_or_link: string;
    client_id: string;
    start_time: string;
    end_time: string;
}

interface Props {
    clients: Client[];
    form: FormState;
    setForm: (f: FormState) => void;
    creating: boolean;
    onSubmit: (e: React.FormEvent) => void;
    onClose: () => void;
}

export function CreateEventModal({ clients, form, setForm, creating, onSubmit, onClose }: Props) {
    return (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-card border border-border rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden">
                <div className="p-6 border-b border-border flex justify-between items-center bg-muted">
                    <h2 className="text-lg font-medium text-foreground flex items-center gap-2"><CalendarIcon className="w-5 h-5 text-primary" /> Agendar Cita</h2>
                    <button onClick={onClose} className="text-muted-foreground hover:text-foreground"><X className="w-5 h-5" /></button>
                </div>
                <form onSubmit={onSubmit} className="p-6 space-y-4">
                    <div>
                        <label className="block text-sm text-muted-foreground mb-1.5">Título *</label>
                        <input required value={form.title} onChange={e => setForm({ ...form, title: e.target.value })}
                            className="w-full bg-background border border-border rounded-lg px-4 py-2.5 text-foreground focus:outline-none focus:border-primary" placeholder="Ej: Demo con Cliente XYZ" />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm text-muted-foreground mb-1.5">Inicio *</label>
                            <input required type="datetime-local" value={form.start_time} onChange={e => setForm({ ...form, start_time: e.target.value })}
                                className="w-full bg-background border border-border rounded-lg px-4 py-2.5 text-foreground focus:outline-none focus:border-primary" />
                        </div>
                        <div>
                            <label className="block text-sm text-muted-foreground mb-1.5">Fin *</label>
                            <input required type="datetime-local" value={form.end_time} onChange={e => setForm({ ...form, end_time: e.target.value })}
                                className="w-full bg-background border border-border rounded-lg px-4 py-2.5 text-foreground focus:outline-none focus:border-primary" />
                        </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm text-muted-foreground mb-1.5">Tipo</label>
                            <select value={form.type} onChange={e => setForm({ ...form, type: e.target.value })}
                                className="w-full bg-background border border-border rounded-lg px-4 py-2.5 text-foreground focus:outline-none focus:border-primary">
                                {EVENT_TYPES.map(t => <option key={t.id} value={t.id}>{t.label}</option>)}
                            </select>
                        </div>
                        <div>
                            <label className="block text-sm text-muted-foreground mb-1.5">Cliente</label>
                            <select value={form.client_id} onChange={e => setForm({ ...form, client_id: e.target.value })}
                                className="w-full bg-background border border-border rounded-lg px-4 py-2.5 text-foreground focus:outline-none focus:border-primary">
                                <option value="">Sin cliente</option>
                                {clients.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                            </select>
                        </div>
                    </div>
                    <div>
                        <label className="block text-sm text-muted-foreground mb-1.5">Enlace / Ubicación</label>
                        <input value={form.location_or_link} onChange={e => setForm({ ...form, location_or_link: e.target.value })}
                            className="w-full bg-background border border-border rounded-lg px-4 py-2.5 text-foreground focus:outline-none focus:border-primary"
                            placeholder="https://meet.google.com/... o dirección" />
                    </div>
                    <div>
                        <label className="block text-sm text-muted-foreground mb-1.5">Descripción</label>
                        <textarea value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} rows={2}
                            className="w-full bg-background border border-border rounded-lg px-4 py-2.5 text-foreground focus:outline-none focus:border-primary resize-none"
                            placeholder="Notas del evento..." />
                    </div>
                    <div className="flex justify-end gap-3 pt-2 border-t border-border">
                        <button type="button" onClick={onClose} className="px-5 py-2.5 text-muted-foreground hover:text-foreground">Cancelar</button>
                        <button type="submit" disabled={creating} className="bg-primary hover:bg-primary text-foreground px-6 py-2.5 rounded-lg font-medium disabled:opacity-50">
                            {creating ? "Guardando..." : "Agendar"}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
