"use client";

import { useEffect, useRef, useState } from "react";
import { Bell, CheckCircle2, AlertCircle, AlertTriangle, Info, X, Trash2 } from "lucide-react";
import { useNotificationStore, type NotifType } from "@/stores/notifications";

function timeAgo(ts: number): string {
    const diff = Math.floor((Date.now() - ts) / 1000);
    if (diff < 60) return "ahora";
    if (diff < 3600) return `hace ${Math.floor(diff / 60)}m`;
    if (diff < 86400) return `hace ${Math.floor(diff / 3600)}h`;
    return `hace ${Math.floor(diff / 86400)}d`;
}

const typeStyles: Record<NotifType, { bg: string; icon: React.ReactNode }> = {
    success: { bg: "text-emerald-400", icon: <CheckCircle2 className="w-3.5 h-3.5" /> },
    error:   { bg: "text-red-400",     icon: <AlertCircle className="w-3.5 h-3.5" /> },
    warning: { bg: "text-amber-400",   icon: <AlertTriangle className="w-3.5 h-3.5" /> },
    info:    { bg: "text-indigo-400",   icon: <Info className="w-3.5 h-3.5" /> },
};

export default function NotificationBell() {
    const [open, setOpen] = useState(false);
    const ref = useRef<HTMLDivElement>(null);
    const items = useNotificationStore((s) => s.items);
    const unreadCount = useNotificationStore((s) => s.unreadCount);
    const markAllRead = useNotificationStore((s) => s.markAllRead);
    const clear = useNotificationStore((s) => s.clear);

    // Close on click outside
    useEffect(() => {
        function handleClick(e: MouseEvent) {
            if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
        }
        document.addEventListener("mousedown", handleClick);
        return () => document.removeEventListener("mousedown", handleClick);
    }, []);

    function handleOpen() {
        setOpen((o) => !o);
        if (!open && unreadCount > 0) markAllRead();
    }

    return (
        <div ref={ref} className="relative">
            <button
                onClick={handleOpen}
                className="relative p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-white/5 transition-colors"
                aria-label="Notificaciones"
                title="Notificaciones"
            >
                <Bell className="w-4 h-4" />
                {unreadCount > 0 && (
                    <span aria-live="polite" className="absolute -top-0.5 -right-0.5 min-w-[16px] h-4 flex items-center justify-center rounded-full bg-indigo-600 text-[10px] font-bold text-foreground px-1">
                        {unreadCount > 99 ? "99+" : unreadCount}
                    </span>
                )}
            </button>

            {open && (
                <div
                    className="fixed right-16 top-12 w-80 max-h-[28rem] bg-card border border-border rounded-xl shadow-2xl shadow-black/50 flex flex-col overflow-hidden"
                    style={{ zIndex: 2147483647 }}
                >
                    {/* Header */}
                    <div className="flex items-center justify-between px-4 py-2.5 border-b border-border">
                        <span className="text-xs font-semibold text-foreground">Notificaciones</span>
                        <div className="flex items-center gap-1">
                            {items.length > 0 && (
                                <button
                                    onClick={clear}
                                    className="p-1 rounded text-muted-foreground hover:text-foreground hover:bg-white/5 transition-colors"
                                    title="Limpiar todo"
                                 aria-label="Limpiar todo">
                                    <Trash2 className="w-3.5 h-3.5" aria-hidden="true" />
                                </button>
                            )}
                            <button
                                onClick={() => setOpen(false)}
                                className="p-1 rounded text-muted-foreground hover:text-foreground hover:bg-white/5 transition-colors"
                             aria-label="Cerrar">
                                <X className="w-3.5 h-3.5" aria-hidden="true" />
                            </button>
                        </div>
                    </div>

                    {/* List */}
                    <div className="flex-1 overflow-y-auto custom-scrollbar">
                        {items.length === 0 ? (
                            <div className="flex flex-col items-center justify-center py-10 text-muted-foreground">
                                <Bell className="w-6 h-6 mb-2 opacity-40" />
                                <span className="text-xs">Sin notificaciones</span>
                            </div>
                        ) : (
                            items.map((n) => {
                                const style = typeStyles[n.type];
                                return (
                                    <div
                                        key={n.id}
                                        className={`flex items-start gap-2.5 px-4 py-2.5 border-b border-border/50 last:border-b-0 ${
                                            !n.read ? "bg-white/[0.02]" : ""
                                        }`}
                                    >
                                        <span className={`mt-0.5 flex-shrink-0 ${style.bg}`}>
                                            {style.icon}
                                        </span>
                                        <div className="flex-1 min-w-0">
                                            <p className="text-xs text-foreground leading-relaxed break-words">
                                                {n.message}
                                            </p>
                                            <span className="text-[10px] text-muted-foreground mt-0.5 block">
                                                {timeAgo(n.timestamp)}
                                            </span>
                                        </div>
                                        {!n.read && (
                                            <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 mt-1.5 flex-shrink-0" />
                                        )}
                                    </div>
                                );
                            })
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
