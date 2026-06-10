"use client";

import type { Dispatch, SetStateAction } from "react";
import { Mail, Loader2, Inbox, RefreshCw, Flame, FileSpreadsheet, MessageSquare, Truck, Users, Megaphone, Trash2 } from "lucide-react";
import type { InboxMessage, EmailDetail, EmailClassification, EmailCategory } from "@/lib/api/messaging";
import { formatDate } from "../format";
import { MessageDetailModal } from "./MessageDetailModal";

const CATEGORY_META: Record<EmailCategory, { label: string; icon: typeof Mail; tone: string }> = {
    urgente:   { label: "Urgente",    icon: Flame,           tone: "bg-rose-500/15 text-rose-500 border-rose-500/30" },
    factura:   { label: "Factura",    icon: FileSpreadsheet, tone: "bg-emerald-500/15 text-emerald-500 border-emerald-500/30" },
    consulta:  { label: "Consulta",   icon: MessageSquare,   tone: "bg-primary/15 text-primary border-primary/30" },
    proveedor: { label: "Proveedor",  icon: Truck,           tone: "bg-amber-500/15 text-amber-500 border-amber-500/30" },
    rrhh:      { label: "RRHH",       icon: Users,           tone: "bg-violet-500/15 text-violet-500 border-violet-500/30" },
    marketing: { label: "Marketing",  icon: Megaphone,       tone: "bg-muted text-muted-foreground border-border" },
    spam:      { label: "Spam",       icon: Trash2,          tone: "bg-muted/40 text-muted-foreground/70 border-border line-through" },
    otro:      { label: "Otro",       icon: Mail,            tone: "bg-muted text-muted-foreground border-border" },
};

interface InboxTabProps {
    inboxMessages: InboxMessage[] | null;
    inboxLoading: boolean;
    inboxProvider: "gmail" | "outlook" | null;
    classMap: Record<string, EmailClassification>;
    loadInbox: () => void;
    openMessage: (id: string) => void;
    selectedMsg: EmailDetail | null;
    bodyLoading: boolean;
    setSelectedMsg: Dispatch<SetStateAction<EmailDetail | null>>;
    setBodyLoading: Dispatch<SetStateAction<boolean>>;
    draftLoading: boolean;
    draftError: string | null;
    handleDraftReply: () => void;
}

export function InboxTab({
    inboxMessages,
    inboxLoading,
    inboxProvider,
    classMap,
    loadInbox,
    openMessage,
    selectedMsg,
    bodyLoading,
    setSelectedMsg,
    setBodyLoading,
    draftLoading,
    draftError,
    handleDraftReply,
}: InboxTabProps) {
    return (
        <div className="space-y-3">
            <div className="flex items-center justify-between">
                <p className="text-xs text-muted-foreground">
                    {inboxProvider === "gmail" && "Bandeja de Gmail"}
                    {inboxProvider === "outlook" && "Bandeja de Outlook"}
                    {inboxProvider === null && !inboxLoading && "Sin proveedor configurado"}
                    {inboxLoading && "Cargando bandeja…"}
                </p>
                <button
                    type="button"
                    onClick={loadInbox}
                    disabled={inboxLoading}
                    className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground disabled:opacity-50"
                >
                    {inboxLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
                    Refrescar
                </button>
            </div>

            {!inboxLoading && inboxProvider === null && (
                <div className="flex flex-col items-center justify-center h-40 gap-2 text-muted-foreground border border-dashed border-border rounded-lg">
                    <Inbox className="w-8 h-8 opacity-30" />
                    <p className="text-sm">No hay proveedor de correo configurado</p>
                    <p className="text-xs max-w-xs text-center">
                        Conecta Gmail u Outlook en <strong>Configuración &rsaquo; Mensajería</strong>
                        para ver tu bandeja aquí.
                    </p>
                </div>
            )}

            {!inboxLoading && inboxMessages?.length === 0 && inboxProvider !== null && (
                <div className="flex flex-col items-center justify-center h-40 gap-2 text-muted-foreground border border-dashed border-border rounded-lg">
                    <Inbox className="w-8 h-8 opacity-30" />
                    <p className="text-sm">Bandeja vacía</p>
                </div>
            )}

            {inboxMessages && inboxMessages.length > 0 && (
                <ul className="rounded-lg border border-border overflow-hidden divide-y divide-border">
                    {inboxMessages.map((m) => {
                        const cls = classMap[m.id];
                        const meta = cls ? CATEGORY_META[cls.category] : null;
                        const CatIcon = meta?.icon;
                        return (
                            <li key={m.id}>
                                <button
                                    type="button"
                                    onClick={() => openMessage(m.id)}
                                    className="w-full text-left px-4 py-3 hover:bg-muted/30 transition-colors flex items-start gap-3"
                                >
                                    {m.unread && <span className="mt-1.5 w-2 h-2 rounded-full bg-violet-500 shrink-0" aria-label="No leído" />}
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2">
                                            <span className={`text-sm truncate ${m.unread ? "font-semibold text-foreground" : "text-foreground"}`}>
                                                {m.from || "(sin remitente)"}
                                            </span>
                                            {meta && CatIcon && (
                                                <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-medium rounded border uppercase tracking-wider ${meta.tone}`}>
                                                    <CatIcon className="w-3 h-3" />
                                                    {meta.label}
                                                    {cls.urgency >= 4 && <span className="ml-0.5">·{cls.urgency}/5</span>}
                                                </span>
                                            )}
                                            <span className="text-[11px] text-muted-foreground ml-auto shrink-0 tabular-nums">
                                                {formatDate(m.date)}
                                            </span>
                                        </div>
                                        <p className={`text-sm truncate ${m.unread ? "text-foreground" : "text-muted-foreground"}`}>
                                            {m.subject || "(sin asunto)"}
                                        </p>
                                        <p className="text-xs text-muted-foreground truncate mt-0.5">
                                            {cls?.suggested_action ? `🤖 ${cls.suggested_action}` : m.snippet}
                                        </p>
                                    </div>
                                </button>
                            </li>
                        );
                    })}
                </ul>
            )}

            {/* Detail modal */}
            {(selectedMsg || bodyLoading) && (
                <MessageDetailModal
                    selectedMsg={selectedMsg}
                    bodyLoading={bodyLoading}
                    setSelectedMsg={setSelectedMsg}
                    setBodyLoading={setBodyLoading}
                    draftLoading={draftLoading}
                    draftError={draftError}
                    handleDraftReply={handleDraftReply}
                />
            )}
        </div>
    );
}
