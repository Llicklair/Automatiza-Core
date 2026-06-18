"use client";

import { Client } from "@/lib/api";
import { Calendar as CalendarIcon, X } from "lucide-react";
import { useTranslations } from "next-intl";

const EVENT_TYPE_IDS = ["meeting", "reminder", "task_deadline"];

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
    const t = useTranslations("crm");
    return (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-card border border-border rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden">
                <div className="p-6 border-b border-border flex justify-between items-center bg-muted">
                    <h2 className="text-lg font-medium text-foreground flex items-center gap-2"><CalendarIcon className="w-5 h-5 text-primary" /> {t("calendario.modal.title")}</h2>
                    <button onClick={onClose} className="text-muted-foreground hover:text-foreground" aria-label={t("calendario.modal.close")}><X className="w-5 h-5" aria-hidden="true" /></button>
                </div>
                <form onSubmit={onSubmit} className="p-6 space-y-4">
                    <div>
                        <label className="block text-sm text-muted-foreground mb-1.5">{t("calendario.modal.titleLabel")}</label>
                        <input required value={form.title} onChange={e => setForm({ ...form, title: e.target.value })}
                            className="w-full bg-background border border-border rounded-lg px-4 py-2.5 text-foreground focus:outline-none focus:border-primary" placeholder={t("calendario.modal.titlePlaceholder")} />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm text-muted-foreground mb-1.5">{t("calendario.modal.startLabel")}</label>
                            <input required type="datetime-local" value={form.start_time} onChange={e => setForm({ ...form, start_time: e.target.value })}
                                className="w-full bg-background border border-border rounded-lg px-4 py-2.5 text-foreground focus:outline-none focus:border-primary" />
                        </div>
                        <div>
                            <label className="block text-sm text-muted-foreground mb-1.5">{t("calendario.modal.endLabel")}</label>
                            <input required type="datetime-local" value={form.end_time} onChange={e => setForm({ ...form, end_time: e.target.value })}
                                className="w-full bg-background border border-border rounded-lg px-4 py-2.5 text-foreground focus:outline-none focus:border-primary" />
                        </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm text-muted-foreground mb-1.5">{t("calendario.modal.typeLabel")}</label>
                            <select value={form.type} onChange={e => setForm({ ...form, type: e.target.value })}
                                className="w-full bg-background border border-border rounded-lg px-4 py-2.5 text-foreground focus:outline-none focus:border-primary">
                                {EVENT_TYPE_IDS.map(id => <option key={id} value={id}>{t(`calendario.modal.types.${id}`)}</option>)}
                            </select>
                        </div>
                        <div>
                            <label className="block text-sm text-muted-foreground mb-1.5">{t("calendario.modal.clientLabel")}</label>
                            <select value={form.client_id} onChange={e => setForm({ ...form, client_id: e.target.value })}
                                className="w-full bg-background border border-border rounded-lg px-4 py-2.5 text-foreground focus:outline-none focus:border-primary">
                                <option value="">{t("calendario.modal.clientNone")}</option>
                                {clients.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                            </select>
                        </div>
                    </div>
                    <div>
                        <label className="block text-sm text-muted-foreground mb-1.5">{t("calendario.modal.linkLabel")}</label>
                        <input value={form.location_or_link} onChange={e => setForm({ ...form, location_or_link: e.target.value })}
                            className="w-full bg-background border border-border rounded-lg px-4 py-2.5 text-foreground focus:outline-none focus:border-primary"
                            placeholder={t("calendario.modal.linkPlaceholder")} />
                    </div>
                    <div>
                        <label className="block text-sm text-muted-foreground mb-1.5">{t("calendario.modal.descriptionLabel")}</label>
                        <textarea value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} rows={2}
                            className="w-full bg-background border border-border rounded-lg px-4 py-2.5 text-foreground focus:outline-none focus:border-primary resize-none"
                            placeholder={t("calendario.modal.descriptionPlaceholder")} />
                    </div>
                    <div className="flex justify-end gap-3 pt-2 border-t border-border">
                        <button type="button" onClick={onClose} className="px-5 py-2.5 text-muted-foreground hover:text-foreground">{t("calendario.modal.cancel")}</button>
                        <button type="submit" disabled={creating} className="bg-primary hover:bg-primary text-foreground px-6 py-2.5 rounded-lg font-medium disabled:opacity-50">
                            {creating ? t("calendario.modal.saving") : t("calendario.modal.submit")}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
