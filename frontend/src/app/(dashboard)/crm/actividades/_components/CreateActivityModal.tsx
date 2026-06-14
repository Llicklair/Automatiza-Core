"use client";

import { useTranslations } from "next-intl";
import { Client } from "@/lib/api";
import { Plus, StickyNote, Phone, Mail, CalendarCheck } from "lucide-react";

interface Props {
    clients: Client[];
    selectedClient: string;
    setSelectedClient: (v: string) => void;
    type: string;
    setType: (v: string) => void;
    description: string;
    setDescription: (v: string) => void;
    isSubmitting: boolean;
    onSubmit: (e: React.FormEvent) => void;
    onClose: () => void;
}

export function CreateActivityModal({
    clients, selectedClient, setSelectedClient,
    type, setType, description, setDescription,
    isSubmitting, onSubmit, onClose,
}: Props) {
    const t = useTranslations("crm");
    return (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-card border border-border rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl">
                <div className="p-5 border-b border-border flex justify-between items-center bg-muted">
                    <h2 className="text-lg font-medium text-foreground flex items-center gap-2">
                        <Plus className="w-4 h-4 text-pink-400" />
                        {t("actividades.modal.title")}
                    </h2>
                    <button onClick={onClose} className="text-muted-foreground hover:text-foreground">✕</button>
                </div>

                <form onSubmit={onSubmit} className="p-6 space-y-4">
                    <div>
                        <label className="block text-sm text-muted-foreground mb-1.5">{t("actividades.modal.clientLabel")}</label>
                        <select
                            value={selectedClient}
                            onChange={e => setSelectedClient(e.target.value)}
                            className="w-full bg-background border border-border rounded-lg px-4 py-2.5 text-foreground focus:outline-none focus:border-pink-500"
                        >
                            <option value="">{t("actividades.modal.clientNone")}</option>
                            {clients.map(c => (
                                <option key={c.id} value={c.id}>{c.name}</option>
                            ))}
                        </select>
                    </div>

                    <div>
                        <label className="block text-sm text-muted-foreground mb-1.5">Tipo de interacción</label>
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
                                        : 'bg-background border-border text-muted-foreground hover:border-border hover:text-foreground'
                                        }`}
                                >
                                    <t.icon className="w-5 h-5 mb-1.5" />
                                    <span className="text-xs font-medium">{t.label}</span>
                                </button>
                            ))}
                        </div>
                    </div>

                    <div>
                        <label className="block text-sm text-muted-foreground mb-1.5">Resumen o Descripción</label>
                        <textarea
                            required
                            rows={4}
                            value={description}
                            onChange={e => setDescription(e.target.value)}
                            placeholder="¿De qué hablasteis? ¿Qué se acordó?..."
                            className="w-full bg-background border border-border rounded-lg px-4 py-3 text-foreground focus:outline-none focus:border-pink-500 resize-none"
                        />
                    </div>

                    <div className="pt-4 flex justify-end gap-3 mt-4">
                        <button
                            type="button"
                            onClick={onClose}
                            className="px-5 py-2.5 text-foreground hover:text-foreground transition-colors font-medium border border-transparent hover:border-border rounded-lg"
                        >
                            Cancelar
                        </button>
                        <button
                            type="submit"
                            disabled={isSubmitting || !description}
                            className="bg-pink-600 hover:bg-pink-500 text-foreground px-6 py-2.5 rounded-lg font-medium transition-colors shadow-lg shadow-pink-500/20 disabled:opacity-50"
                        >
                            {isSubmitting ? "Guardando..." : "Registrar"}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
