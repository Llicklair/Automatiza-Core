"use client";

import { useState } from "react";
import { ChevronLeft, ChevronRight, Clock, Trash2 } from "lucide-react";
import { ScheduledPost } from "@/lib/api/marketing";
import { PLATFORMS } from "./constants";

const WEEKDAYS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"];
const MONTHS = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
];

function postDate(p: ScheduledPost): Date | null {
    const iso = p.scheduled_at ?? p.published_at;
    return iso ? new Date(iso) : null;
}

const plat = (id: string) => PLATFORMS.find((p) => p.id === id);
const hhmm = (p: ScheduledPost) => {
    const d = postDate(p);
    return d ? d.toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" }) : "";
};

/** Vista de calendario mensual de publicaciones programadas/publicadas. */
export function PostsCalendar({
    posts,
    onRemove,
}: {
    posts: ScheduledPost[];
    onRemove: (id: string) => void;
}) {
    const now = new Date();
    const [year, setYear] = useState(now.getFullYear());
    const [month, setMonth] = useState(now.getMonth()); // 0-11
    const [selected, setSelected] = useState<string | null>(null); // YYYY-MM-DD

    const firstDay = new Date(year, month, 1);
    const startOffset = (firstDay.getDay() + 6) % 7; // lunes = 0
    const daysInMonth = new Date(year, month + 1, 0).getDate();

    const byDay = new Map<number, ScheduledPost[]>();
    for (const p of posts) {
        const d = postDate(p);
        if (!d || d.getFullYear() !== year || d.getMonth() !== month) continue;
        const arr = byDay.get(d.getDate()) ?? [];
        arr.push(p);
        byDay.set(d.getDate(), arr);
    }

    const goPrev = () => {
        setSelected(null);
        if (month === 0) { setMonth(11); setYear((y) => y - 1); } else setMonth((m) => m - 1);
    };
    const goNext = () => {
        setSelected(null);
        if (month === 11) { setMonth(0); setYear((y) => y + 1); } else setMonth((m) => m + 1);
    };

    const cells: (number | null)[] = [
        ...Array(startOffset).fill(null),
        ...Array.from({ length: daysInMonth }, (_, i) => i + 1),
    ];
    const dayKey = (d: number) =>
        `${year}-${String(month + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
    const selectedDay = selected ? parseInt(selected.slice(-2), 10) : null;
    const selectedPosts = selectedDay ? (byDay.get(selectedDay) ?? []) : [];

    return (
        <div className="space-y-4">
            {/* Navegación de mes */}
            <div className="flex items-center justify-between">
                <button onClick={goPrev} className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground transition-colors">
                    <ChevronLeft className="w-4 h-4" />
                </button>
                <span className="text-sm font-medium text-foreground">{MONTHS[month]} {year}</span>
                <button onClick={goNext} className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground transition-colors">
                    <ChevronRight className="w-4 h-4" />
                </button>
            </div>

            {/* Cabecera de días */}
            <div className="grid grid-cols-7 gap-1 text-center text-[10px] font-medium text-muted-foreground">
                {WEEKDAYS.map((w) => <div key={w}>{w}</div>)}
            </div>

            {/* Cuadrícula */}
            <div className="grid grid-cols-7 gap-1">
                {cells.map((d, i) => {
                    if (d === null) return <div key={`e${i}`} className="min-h-[72px]" />;
                    const dayPosts = byDay.get(d) ?? [];
                    const isSel = selected === dayKey(d);
                    return (
                        <button
                            key={d}
                            onClick={() => setSelected(isSel ? null : dayKey(d))}
                            className={`min-h-[72px] rounded-lg border p-1 text-left align-top transition-colors ${
                                isSel ? "border-pink-500 bg-pink-500/5" : "border-border hover:border-pink-500/40"
                            }`}
                        >
                            <div className="text-[11px] text-muted-foreground mb-1">{d}</div>
                            <div className="space-y-0.5">
                                {dayPosts.slice(0, 2).map((p) => {
                                    const pc = plat(p.platform);
                                    return (
                                        <div
                                            key={p.id}
                                            className={`truncate text-[9px] px-1 py-0.5 rounded border ${pc?.colorClass ?? "text-muted-foreground border-border"}`}
                                        >
                                            {hhmm(p)} {pc?.name?.split(" ")[0] ?? p.platform}
                                        </div>
                                    );
                                })}
                                {dayPosts.length > 2 && (
                                    <div className="text-[9px] text-muted-foreground">+{dayPosts.length - 2} más</div>
                                )}
                            </div>
                        </button>
                    );
                })}
            </div>

            {/* Detalle del día seleccionado */}
            {selected && selectedPosts.length > 0 && (
                <div className="space-y-2 border-t border-border pt-3">
                    <p className="text-xs text-muted-foreground">
                        {selectedPosts.length} publicación(es)
                    </p>
                    {selectedPosts.map((p) => {
                        const pc = plat(p.platform);
                        return (
                            <div key={p.id} className="bg-card border border-border rounded-lg p-3 space-y-1">
                                <div className="flex items-center justify-between gap-2">
                                    <span className={`text-[10px] px-2 py-0.5 rounded-full border font-medium ${pc?.colorClass ?? "text-muted-foreground border-border"}`}>
                                        {pc?.name ?? p.platform}
                                    </span>
                                    <div className="flex items-center gap-2">
                                        <span className="text-[11px] text-muted-foreground flex items-center gap-1">
                                            <Clock className="w-3 h-3" />{hhmm(p)}
                                        </span>
                                        {p.status !== "published" && (
                                            <button onClick={() => onRemove(p.id)} className="text-muted-foreground hover:text-red-400 transition-colors">
                                                <Trash2 className="w-3.5 h-3.5" />
                                            </button>
                                        )}
                                    </div>
                                </div>
                                <p className="text-sm text-foreground line-clamp-3 leading-relaxed">{p.content}</p>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
