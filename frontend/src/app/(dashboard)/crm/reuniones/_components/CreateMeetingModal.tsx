"use client";

import { Client } from "@/lib/api";
import { Video, X } from "lucide-react";

interface FormState {
    title: string;
    description: string;
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

export function CreateMeetingModal({ clients, form, setForm, creating, onSubmit, onClose }: Props) {
    return (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-card border border-border rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden">
                <div className="p-6 border-b border-border flex justify-between items-center bg-muted">
                    <h2 className="text-lg font-medium text-foreground flex items-center gap-2"><Video className="w-5 h-5 text-blue-400" /> Programar Reunión</h2>
                    <button onClick={onClose} className="text-muted-foreground hover:text-foreground" aria-label="Cerrar formulario de reunión"><X className="w-5 h-5" aria-hidden="true" /></button>
                </div>
                <form onSubmit={onSubmit} className="p-6 space-y-4">
                    <div>
                        <label className="block text-sm text-muted-foreground mb-1.5">Título *</label>
                        <input required value={form.title} onChange={e => setForm({ ...form, title: e.target.value })}
                            className="w-full bg-background border border-border rounded-lg px-4 py-2.5 text-foreground focus:outline-none focus:border-blue-500"
                            placeholder="Ej: Llamada de seguimiento con ACME" />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm text-muted-foreground mb-1.5">Inicio *</label>
                            <input required type="datetime-local" value={form.start_time} onChange={e => setForm({ ...form, start_time: e.target.value })}
                                className="w-full bg-background border border-border rounded-lg px-4 py-2.5 text-foreground focus:outline-none focus:border-blue-500" />
                        </div>
                        <div>
                            <label className="block text-sm text-muted-foreground mb-1.5">Fin *</label>
                            <input required type="datetime-local" value={form.end_time} onChange={e => setForm({ ...form, end_time: e.target.value })}
                                className="w-full bg-background border border-border rounded-lg px-4 py-2.5 text-foreground focus:outline-none focus:border-blue-500" />
                        </div>
                    </div>
                    <div>
                        <label className="block text-sm text-muted-foreground mb-1.5">Enlace (Meet/Zoom/Teams)</label>
                        <input value={form.location_or_link} onChange={e => setForm({ ...form, location_or_link: e.target.value })}
                            className="w-full bg-background border border-border rounded-lg px-4 py-2.5 text-foreground focus:outline-none focus:border-blue-500"
                            placeholder="https://meet.google.com/..." />
                    </div>
                    <div>
                        <label className="block text-sm text-muted-foreground mb-1.5">Cliente</label>
                        <select value={form.client_id} onChange={e => setForm({ ...form, client_id: e.target.value })}
                            className="w-full bg-background border border-border rounded-lg px-4 py-2.5 text-foreground focus:outline-none focus:border-blue-500">
                            <option value="">Sin cliente</option>
                            {clients.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                        </select>
                    </div>
                    <div>
                        <label className="block text-sm text-muted-foreground mb-1.5">Descripción</label>
                        <textarea value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} rows={2}
                            className="w-full bg-background border border-border rounded-lg px-4 py-2.5 text-foreground focus:outline-none focus:border-blue-500 resize-none"
                            placeholder="Agenda de la reunión..." />
                    </div>
                    <div className="flex justify-end gap-3 pt-2 border-t border-border">
                        <button type="button" onClick={onClose} className="px-5 py-2.5 text-muted-foreground hover:text-foreground">Cancelar</button>
                        <button type="submit" disabled={creating} className="bg-blue-600 hover:bg-blue-500 text-foreground px-6 py-2.5 rounded-lg font-medium disabled:opacity-50">
                            {creating ? "Guardando..." : "Programar"}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
