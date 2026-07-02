"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import {
    CalendarDays, ChevronLeft, ChevronRight, Loader2, ReceiptText,
    Users, Wallet, CalendarCheck, Plus, Plane,
} from "lucide-react";
import { api } from "@/lib/api";
import type { UnifiedCalendarEvent } from "@/lib/api";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/ui/button";
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { useToastStore } from "@/stores/toast";

// ── Helpers ──────────────────────────────────────────────────────────────────

function padDate(d: Date): string {
    return d.toISOString().slice(0, 10);
}

function daysInMonth(year: number, month: number) {
    return new Date(year, month + 1, 0).getDate();
}

function firstWeekday(year: number, month: number) {
    // 0 = Monday ... 6 = Sunday
    const d = new Date(year, month, 1).getDay();
    return (d + 6) % 7;
}

function toDateKey(iso: string) {
    return iso.slice(0, 10);
}

// ── Color maps ────────────────────────────────────────────────────────────────

const COLOR_BG: Record<string, string> = {
    blue:   "bg-blue-500/20 text-blue-300 border-blue-500/30",
    purple: "bg-purple-500/20 text-purple-300 border-purple-500/30",
    red:    "bg-red-500/20 text-red-300 border-red-500/30",
    amber:  "bg-amber-500/20 text-amber-300 border-amber-500/30",
    green:  "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
    teal:   "bg-teal-500/20 text-teal-300 border-teal-500/30",
};

const SOURCE_ICON: Record<string, React.ElementType> = {
    event:        CalendarCheck,
    reservation:  Users,
    invoice_due:  ReceiptText,
    payroll:      Wallet,
    leave:        Plane,
};

const buildSourceLabel = (t: ReturnType<typeof useTranslations>): Record<string, string> => ({
    event:        t("sources.event"),
    reservation:  t("sources.reservation"),
    invoice_due:  t("sources.invoiceDue"),
    payroll:      t("sources.payroll"),
    leave:        t("sources.leave"),
});

// ── Component ─────────────────────────────────────────────────────────────────

export default function CalendarioPage() {
    const t = useTranslations("calendario");
    const SOURCE_LABEL = buildSourceLabel(t);
    const WEEKDAYS = [
        t("weekdays.mon"), t("weekdays.tue"), t("weekdays.wed"),
        t("weekdays.thu"), t("weekdays.fri"), t("weekdays.sat"), t("weekdays.sun"),
    ];
    const MONTHS = [
        t("months.jan"), t("months.feb"), t("months.mar"), t("months.apr"),
        t("months.may"), t("months.jun"), t("months.jul"), t("months.aug"),
        t("months.sep"), t("months.oct"), t("months.nov"), t("months.dec"),
    ];
    const toast = useToastStore();
    const today = new Date();

    const [year, setYear] = useState(today.getFullYear());
    const [month, setMonth] = useState(today.getMonth());
    const [events, setEvents] = useState<UnifiedCalendarEvent[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [selectedDay, setSelectedDay] = useState<string | null>(null);

    // ── New event modal ─────────────────────────────────────────────────────
    const [showNew, setShowNew] = useState(false);
    const [creating, setCreating] = useState(false);
    const todayKeyInit = padDate(today);
    const [newForm, setNewForm] = useState({
        title: "",
        type: "meeting",
        start_date: todayKeyInit,
        start_time: "09:00",
        end_date: todayKeyInit,
        end_time: "10:00",
        location_or_link: "",
        description: "",
    });

    function openNewEvent(dayKey?: string) {
        const baseDate = dayKey ?? selectedDay ?? padDate(today);
        setNewForm({
            title: "",
            type: "meeting",
            start_date: baseDate,
            start_time: "09:00",
            end_date: baseDate,
            end_time: "10:00",
            location_or_link: "",
            description: "",
        });
        setShowNew(true);
    }

    const load = useCallback(async (y: number, m: number) => {
        setIsLoading(true);
        try {
            const start = padDate(new Date(y, m, 1));
            const end = padDate(new Date(y, m + 1, 0));
            setEvents(await api.calendarUnified.list(start, end));
        } catch {
            toast.error(t("toasts.loadError"));
        } finally {
            setIsLoading(false);
        }
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    useEffect(() => { load(year, month); }, [year, month, load]);

    const goMonth = (delta: number) => {
        const d = new Date(year, month + delta, 1);
        setYear(d.getFullYear());
        setMonth(d.getMonth());
        setSelectedDay(null);
    };

    async function handleCreate(e: React.FormEvent) {
        e.preventDefault();
        if (!newForm.title.trim()) {
            toast.error(t("toasts.missingTitle"));
            return;
        }
        const startISO = new Date(`${newForm.start_date}T${newForm.start_time}:00`).toISOString();
        const endISO = new Date(`${newForm.end_date}T${newForm.end_time}:00`).toISOString();
        if (new Date(endISO) <= new Date(startISO)) {
            toast.error(t("toasts.endBeforeStart"));
            return;
        }
        setCreating(true);
        try {
            await api.crm.events.create({
                title: newForm.title.trim(),
                type: newForm.type,
                description: newForm.description.trim() || null,
                location_or_link: newForm.location_or_link.trim() || null,
                start_time: startISO,
                end_time: endISO,
            });
            toast.success(t("toasts.created"));
            setShowNew(false);
            await load(year, month);
        } catch {
            toast.error(t("toasts.createError"));
        } finally {
            setCreating(false);
        }
    }

    // Group events by date key
    const byDay = useMemo(() => {
        const map: Record<string, UnifiedCalendarEvent[]> = {};
        for (const ev of events) {
            const key = toDateKey(ev.start);
            if (!map[key]) map[key] = [];
            map[key].push(ev);
        }
        return map;
    }, [events]);

    // Build grid cells
    const firstOffset = firstWeekday(year, month);
    const totalDays = daysInMonth(year, month);
    const cells: (number | null)[] = [
        ...Array(firstOffset).fill(null),
        ...Array.from({ length: totalDays }, (_, i) => i + 1),
    ];
    while (cells.length % 7 !== 0) cells.push(null);

    const todayKey = padDate(today);

    const selectedEvents = selectedDay ? (byDay[selectedDay] ?? []) : [];

    return (
        <div className="p-6 space-y-5">
            <PageHeader
                title={t("header.title")}
                description={t("header.description")}
                icon={CalendarDays}
            />

            {/* Navigation */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <Button variant="outline" size="sm" onClick={() => goMonth(-1)}>
                        <ChevronLeft className="h-4 w-4" />
                    </Button>
                    <h2 className="text-base font-semibold text-foreground w-44 text-center">
                        {MONTHS[month]} {year}
                    </h2>
                    <Button variant="outline" size="sm" onClick={() => goMonth(1)}>
                        <ChevronRight className="h-4 w-4" />
                    </Button>
                    <Button
                        variant="ghost" size="sm"
                        className="text-xs text-muted-foreground"
                        onClick={() => { setYear(today.getFullYear()); setMonth(today.getMonth()); setSelectedDay(todayKey); }}
                    >
                        {t("nav.today")}
                    </Button>
                    <Button size="sm" onClick={() => openNewEvent()}>
                        <Plus className="h-3.5 w-3.5 mr-1.5" />
                        {t("nav.newEvent")}
                    </Button>
                </div>

                {/* Legend */}
                <div className="hidden md:flex items-center gap-3 text-xs text-muted-foreground">
                    {Object.entries(SOURCE_LABEL).map(([src, lbl]) => {
                        const colorKey = src === "event" ? "blue" : src === "reservation" ? "purple" : src === "invoice_due" ? "amber" : src === "leave" ? "teal" : "green";
                        return (
                            <span key={src} className={`flex items-center gap-1 px-2 py-0.5 rounded-full border ${COLOR_BG[colorKey]}`}>
                                {lbl}
                            </span>
                        );
                    })}
                </div>
            </div>

            <div className="flex gap-4">
                {/* Calendar grid */}
                <div className="flex-1 min-w-0">
                    {isLoading ? (
                        <div className="flex items-center justify-center h-64 text-muted-foreground gap-2">
                            <Loader2 className="w-4 h-4 animate-spin" /> {t("grid.loading")}
                        </div>
                    ) : (
                        <div className="rounded-xl border border-border bg-card overflow-hidden">
                            {/* Weekday headers */}
                            <div className="grid grid-cols-7 border-b border-border">
                                {WEEKDAYS.map((d) => (
                                    <div key={d} className="py-2 text-center text-xs font-medium text-muted-foreground">
                                        {d}
                                    </div>
                                ))}
                            </div>

                            {/* Day cells */}
                            <div className="grid grid-cols-7">
                                {cells.map((day, i) => {
                                    if (!day) {
                                        return (
                                            <div
                                                key={`empty-${i}`}
                                                className="min-h-[90px] border-b border-r border-border/50 bg-muted/10 last:border-r-0"
                                            />
                                        );
                                    }
                                    const key = `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
                                    const dayEvents = byDay[key] ?? [];
                                    const isToday = key === todayKey;
                                    const isSelected = key === selectedDay;
                                    const visible = dayEvents.slice(0, 3);
                                    const overflow = dayEvents.length - visible.length;

                                    return (
                                        <div
                                            key={key}
                                            onClick={() => setSelectedDay(isSelected ? null : key)}
                                            className={`min-h-[90px] border-b border-r border-border/50 last:border-r-0 p-1.5 cursor-pointer transition-colors
                                                ${isSelected ? "bg-primary/10" : "hover:bg-muted/20"}
                                                ${(i + 1) % 7 === 0 ? "border-r-0" : ""}`}
                                        >
                                            <div className={`text-xs font-medium mb-1 w-6 h-6 flex items-center justify-center rounded-full
                                                ${isToday ? "bg-primary text-primary-foreground" : "text-foreground"}`}>
                                                {day}
                                            </div>
                                            <div className="space-y-0.5">
                                                {visible.map((ev) => (
                                                    <div
                                                        key={ev.id}
                                                        className={`text-[10px] truncate px-1 py-0.5 rounded border ${COLOR_BG[ev.color]}`}
                                                        title={ev.title}
                                                    >
                                                        {ev.title}
                                                    </div>
                                                ))}
                                                {overflow > 0 && (
                                                    <div className="text-[10px] text-muted-foreground px-1">
                                                        {t("grid.more", { count: overflow })}
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    )}
                </div>

                {/* Day detail panel */}
                {selectedDay && (
                    <div className="w-72 shrink-0">
                        <div className="rounded-xl border border-border bg-card p-4 space-y-3 sticky top-6">
                            <div className="flex items-center justify-between">
                                <h3 className="text-sm font-semibold text-foreground capitalize">
                                    {new Date(selectedDay + "T12:00:00").toLocaleDateString("es-ES", {
                                        weekday: "long", day: "numeric", month: "long",
                                    })}
                                </h3>
                                <button onClick={() => setSelectedDay(null)} className="text-xs text-muted-foreground hover:text-foreground" aria-label={t("detail.closeAria")}>✕</button>
                            </div>

                            <Button
                                size="sm"
                                variant="outline"
                                className="w-full text-xs"
                                onClick={() => openNewEvent(selectedDay)}
                            >
                                <Plus className="h-3.5 w-3.5 mr-1.5" />
                                {t("detail.createThisDay")}
                            </Button>

                            {selectedEvents.length === 0 ? (
                                <p className="text-xs text-muted-foreground italic">{t("detail.empty")}</p>
                            ) : (
                                <div className="space-y-2">
                                    {selectedEvents.map((ev) => {
                                        const Icon = SOURCE_ICON[ev.source] ?? CalendarDays;
                                        const timeStr = ev.start.length > 10
                                            ? new Date(ev.start).toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" })
                                            : null;
                                        return (
                                            <a
                                                key={ev.id}
                                                href={ev.href}
                                                className={`block rounded-lg border px-3 py-2 hover:opacity-80 transition-opacity ${COLOR_BG[ev.color]}`}
                                            >
                                                <div className="flex items-center gap-2">
                                                    <Icon className="w-3.5 h-3.5 shrink-0" />
                                                    <span className="text-xs font-medium truncate">{ev.title}</span>
                                                    {timeStr && <span className="text-[10px] ml-auto shrink-0 opacity-70">{timeStr}</span>}
                                                </div>
                                                {ev.subtitle && (
                                                    <p className="text-[10px] opacity-70 mt-0.5 truncate pl-5">{ev.subtitle}</p>
                                                )}
                                                <p className="text-[10px] opacity-50 mt-0.5 pl-5">{SOURCE_LABEL[ev.source]}</p>
                                            </a>
                                        );
                                    })}
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </div>

            {/* New event modal */}
            <Dialog open={showNew} onOpenChange={setShowNew}>
                <DialogContent className="max-w-md">
                    <DialogHeader>
                        <DialogTitle>{t("modal.title")}</DialogTitle>
                    </DialogHeader>
                    <form onSubmit={handleCreate} className="space-y-4">
                        <div className="space-y-1.5">
                            <Label htmlFor="ev-title">{t("modal.fieldTitle")}</Label>
                            <Input
                                id="ev-title"
                                required
                                value={newForm.title}
                                onChange={(e) => setNewForm((f) => ({ ...f, title: e.target.value }))}
                                placeholder={t("modal.titlePlaceholder")}
                            />
                        </div>

                        <div className="space-y-1.5">
                            <Label>{t("modal.type")}</Label>
                            <Select
                                value={newForm.type}
                                onValueChange={(v) => setNewForm((f) => ({ ...f, type: v }))}
                            >
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="meeting">{t("eventTypes.meeting")}</SelectItem>
                                    <SelectItem value="call">{t("eventTypes.call")}</SelectItem>
                                    <SelectItem value="task">{t("eventTypes.task")}</SelectItem>
                                    <SelectItem value="other">{t("eventTypes.other")}</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>

                        <div className="grid grid-cols-2 gap-3">
                            <div className="space-y-1.5">
                                <Label htmlFor="ev-start-date">{t("modal.start")}</Label>
                                <Input
                                    id="ev-start-date"
                                    type="date"
                                    required
                                    value={newForm.start_date}
                                    onChange={(e) => setNewForm((f) => ({
                                        ...f,
                                        start_date: e.target.value,
                                        end_date: f.end_date < e.target.value ? e.target.value : f.end_date,
                                    }))}
                                />
                            </div>
                            <div className="space-y-1.5">
                                <Label htmlFor="ev-start-time" className="invisible">.</Label>
                                <Input
                                    id="ev-start-time"
                                    type="time"
                                    required
                                    value={newForm.start_time}
                                    onChange={(e) => setNewForm((f) => ({ ...f, start_time: e.target.value }))}
                                />
                            </div>
                        </div>

                        <div className="grid grid-cols-2 gap-3">
                            <div className="space-y-1.5">
                                <Label htmlFor="ev-end-date">{t("modal.end")}</Label>
                                <Input
                                    id="ev-end-date"
                                    type="date"
                                    required
                                    min={newForm.start_date}
                                    value={newForm.end_date}
                                    onChange={(e) => setNewForm((f) => ({ ...f, end_date: e.target.value }))}
                                />
                            </div>
                            <div className="space-y-1.5">
                                <Label htmlFor="ev-end-time" className="invisible">.</Label>
                                <Input
                                    id="ev-end-time"
                                    type="time"
                                    required
                                    value={newForm.end_time}
                                    onChange={(e) => setNewForm((f) => ({ ...f, end_time: e.target.value }))}
                                />
                            </div>
                        </div>

                        <div className="space-y-1.5">
                            <Label htmlFor="ev-loc">{t("modal.location")}</Label>
                            <Input
                                id="ev-loc"
                                value={newForm.location_or_link}
                                onChange={(e) => setNewForm((f) => ({ ...f, location_or_link: e.target.value }))}
                                placeholder={t("modal.locationPlaceholder")}
                            />
                        </div>

                        <div className="space-y-1.5">
                            <Label htmlFor="ev-desc">{t("modal.notes")}</Label>
                            <textarea
                                id="ev-desc"
                                rows={3}
                                value={newForm.description}
                                onChange={(e) => setNewForm((f) => ({ ...f, description: e.target.value }))}
                                placeholder={t("modal.notesPlaceholder")}
                                className="w-full bg-background border border-input rounded-md px-3 py-2 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-ring"
                            />
                        </div>

                        <DialogFooter>
                            <Button type="button" variant="outline" onClick={() => setShowNew(false)} disabled={creating}>
                                {t("modal.cancel")}
                            </Button>
                            <Button type="submit" disabled={creating}>
                                {creating ? <Loader2 className="w-3.5 h-3.5 animate-spin mr-1.5" /> : <Plus className="w-3.5 h-3.5 mr-1.5" />}
                                {t("modal.create")}
                            </Button>
                        </DialogFooter>
                    </form>
                </DialogContent>
            </Dialog>
        </div>
    );
}
