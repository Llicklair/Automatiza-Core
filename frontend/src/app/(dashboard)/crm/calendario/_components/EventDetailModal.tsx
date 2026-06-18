"use client";

import { EventItem } from "@/lib/api";
import { Clock, MapPin, Trash2, X } from "lucide-react";
import { format } from "date-fns";
import { es } from "date-fns/locale";
import { useTranslations } from "next-intl";

interface Props {
    event: EventItem;
    clientName: (id: string | null) => string | null;
    deleting: boolean;
    onDelete: (id: string) => void;
    onClose: () => void;
}

export function EventDetailModal({ event, clientName, deleting, onDelete, onClose }: Props) {
    const t = useTranslations("crm");
    return (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4" onClick={onClose}>
            <div className="bg-card border border-border rounded-2xl w-full max-w-md shadow-2xl" onClick={e => e.stopPropagation()}>
                <div className="p-5 border-b border-border flex justify-between items-start bg-muted">
                    <div>
                        <h2 className="text-lg font-medium text-foreground">{event.title}</h2>
                        <span className="text-xs text-primary capitalize">{event.type}</span>
                    </div>
                    <button onClick={onClose} className="text-muted-foreground hover:text-foreground ml-4" aria-label={t("calendario.detail.close")}><X className="w-5 h-5" aria-hidden="true" /></button>
                </div>
                <div className="p-5 space-y-3">
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Clock className="w-4 h-4 shrink-0" />
                        {format(new Date(event.start_time), "dd MMM yyyy, HH:mm", { locale: es })} - {format(new Date(event.end_time), "HH:mm")}
                    </div>
                    {event.location_or_link && (
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            <MapPin className="w-4 h-4 shrink-0" />
                            {event.location_or_link.startsWith("http")
                                ? <a href={event.location_or_link} target="_blank" rel="noreferrer" className="text-primary hover:underline truncate">{event.location_or_link}</a>
                                : event.location_or_link}
                        </div>
                    )}
                    {clientName(event.client_id) && (
                        <div className="text-sm text-muted-foreground">{t("calendario.detail.clientLabel")} <span className="text-foreground">{clientName(event.client_id)}</span></div>
                    )}
                    {event.description && <p className="text-sm text-muted-foreground pt-2 border-t border-border">{event.description}</p>}
                </div>
                <div className="p-5 border-t border-border flex justify-end">
                    <button onClick={() => onDelete(event.id)} disabled={deleting}
                        className="flex items-center gap-2 text-sm text-red-400 hover:text-red-300 disabled:opacity-50">
                        <Trash2 className="w-4 h-4" /> {deleting ? t("calendario.detail.deleting") : t("calendario.detail.delete")}
                    </button>
                </div>
            </div>
        </div>
    );
}
