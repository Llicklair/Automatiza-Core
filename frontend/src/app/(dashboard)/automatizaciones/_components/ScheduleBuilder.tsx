"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Loader2, Sparkles, Clock } from "lucide-react";
import { api } from "@/lib/api";
import {
    buildDays, MONTHS_DAYS, HOURS, MINUTES_OPTIONS,
    parseCron, buildCron, cronToHuman,
    type FreqKey,
} from "./constants";

interface ScheduleBuilderProps {
    value: string;
    onChange: (cron: string) => void;
}

export default function ScheduleBuilder({ value, onChange }: ScheduleBuilderProps) {
    const t = useTranslations("automatizaciones");
    const DAYS = buildDays(t);
    const parsed = parseCron(value);
    const [freq, setFreq] = useState<FreqKey>(parsed.freq);
    const [minute, setMinute] = useState(parsed.minute);
    const [hour, setHour] = useState(parsed.hour);
    const [day, setDay] = useState(parsed.day);
    const [weekday, setWeekday] = useState(parsed.weekday);
    const [nlText, setNlText] = useState("");
    const [nlParsing, setNlParsing] = useState(false);
    const [nlError, setNlError] = useState("");

    const update = (f: FreqKey, m: number, h: number, d: number, wd: number) => {
        onChange(buildCron(f, m, h, d, wd));
    };

    const setF = (f: FreqKey) => { setFreq(f); update(f, minute, hour, day, weekday); };
    const setM = (m: number) => { setMinute(m); update(freq, m, hour, day, weekday); };
    const setH = (h: number) => { setHour(h); update(freq, minute, h, day, weekday); };
    const setD = (d: number) => { setDay(d); update(freq, minute, hour, d, weekday); };
    const setWd = (wd: number) => { setWeekday(wd); update(freq, minute, hour, day, wd); };

    const handleNlParse = async () => {
        if (!nlText.trim()) return;
        setNlParsing(true);
        setNlError("");
        try {
            const result = await api.workflows.parse(nlText);
            const cron = result?.trigger_config?.cron;
            if (cron) {
                const p = parseCron(cron);
                setFreq(p.freq); setMinute(p.minute); setHour(p.hour); setDay(p.day); setWeekday(p.weekday);
                onChange(cron);
                setNlText("");
            } else {
                setNlError(t("schedule.noFreqDetected"));
            }
        } catch {
            setNlError(t("schedule.processError"));
        } finally {
            setNlParsing(false);
        }
    };

    const FREQS: { key: FreqKey; label: string }[] = [
        { key: "minutes", label: t("schedule.freqMinutes") },
        { key: "hourly",  label: t("schedule.freqHourly") },
        { key: "daily",   label: t("schedule.freqDaily") },
        { key: "weekly",  label: t("schedule.freqWeekly") },
        { key: "monthly", label: t("schedule.freqMonthly") },
    ];

    const sel = "border-blue-500/50 bg-blue-500/10 text-blue-300";
    const unsel = "border-border bg-background text-muted-foreground hover:border-border";

    return (
        <div className="space-y-3">
            {/* NL input */}
            <div className="flex gap-2">
                <input
                    type="text"
                    value={nlText}
                    onChange={e => { setNlText(e.target.value); setNlError(""); }}
                    onKeyDown={e => e.key === "Enter" && handleNlParse()}
                    placeholder={t("schedule.nlPlaceholder")}
                    className="flex-1 bg-background border border-border rounded-lg px-3 py-2 text-foreground text-xs focus:outline-none focus:border-blue-500 transition placeholder:text-muted-foreground/60"
                />
                <button type="button" onClick={handleNlParse} disabled={nlParsing || !nlText.trim()}
                    className="px-3 py-2 bg-blue-600 hover:bg-blue-500 text-foreground rounded-lg text-xs font-medium transition disabled:opacity-40 flex items-center gap-1">
                    {nlParsing ? <Loader2 className="w-3 h-3 animate-spin" /> : <Sparkles className="w-3 h-3" />}
                    {nlParsing ? t("schedule.applying") : t("schedule.apply")}
                </button>
            </div>
            {nlError && <p className="text-[10px] text-red-400">{nlError}</p>}

            <label className="block text-xs text-muted-foreground uppercase tracking-wider">{t("schedule.configureManually")}</label>
            <div className="flex flex-wrap gap-2">
                {FREQS.map(f => (
                    <button key={f.key} type="button" onClick={() => setF(f.key)}
                        className={`px-3 py-1.5 rounded-lg border text-xs font-medium transition-all ${freq === f.key ? sel : unsel}`}>
                        {f.label}
                    </button>
                ))}
            </div>

            <div className="flex flex-wrap gap-3 items-end">
                {freq === "minutes" && (
                    <div>
                        <label className="block text-[10px] text-muted-foreground mb-1">{t("schedule.every")}</label>
                        <select value={minute} onChange={e => setM(Number(e.target.value))}
                            className="bg-background border border-border rounded-lg px-3 py-2 text-foreground text-sm focus:outline-none focus:border-blue-500">
                            {[1,2,5,10,15,20,30].map(v => <option key={v} value={v}>{t("schedule.minutesOption", { n: v })}</option>)}
                        </select>
                    </div>
                )}
                {freq === "hourly" && (
                    <div>
                        <label className="block text-[10px] text-muted-foreground mb-1">{t("schedule.atMinute")}</label>
                        <select value={minute} onChange={e => setM(Number(e.target.value))}
                            className="bg-background border border-border rounded-lg px-3 py-2 text-foreground text-sm focus:outline-none focus:border-blue-500">
                            {MINUTES_OPTIONS.map(v => <option key={v} value={v}>{String(v).padStart(2,"0")}</option>)}
                        </select>
                    </div>
                )}
                {(freq === "daily" || freq === "weekly" || freq === "monthly") && (
                    <>
                        <div>
                            <label className="block text-[10px] text-muted-foreground mb-1">{t("schedule.hour")}</label>
                            <select value={hour} onChange={e => setH(Number(e.target.value))}
                                className="bg-background border border-border rounded-lg px-3 py-2 text-foreground text-sm focus:outline-none focus:border-blue-500">
                                {HOURS.map(h => <option key={h} value={h}>{String(h).padStart(2,"0")}:00</option>)}
                            </select>
                        </div>
                        <div>
                            <label className="block text-[10px] text-muted-foreground mb-1">{t("schedule.minute")}</label>
                            <select value={minute} onChange={e => setM(Number(e.target.value))}
                                className="bg-background border border-border rounded-lg px-3 py-2 text-foreground text-sm focus:outline-none focus:border-blue-500">
                                {MINUTES_OPTIONS.map(v => <option key={v} value={v}>{String(v).padStart(2,"0")}</option>)}
                            </select>
                        </div>
                    </>
                )}
                {freq === "weekly" && (
                    <div>
                        <label className="block text-[10px] text-muted-foreground mb-1">{t("schedule.day")}</label>
                        <div className="flex gap-1">
                            {DAYS.map((d, i) => (
                                <button key={i} type="button" onClick={() => setWd(i)}
                                    className={`w-8 h-8 rounded-lg text-xs font-medium border transition-all ${weekday === i ? sel : unsel}`}>
                                    {d}
                                </button>
                            ))}
                        </div>
                    </div>
                )}
                {freq === "monthly" && (
                    <div>
                        <label className="block text-[10px] text-muted-foreground mb-1">{t("schedule.dayOfMonth")}</label>
                        <select value={day} onChange={e => setD(Number(e.target.value))}
                            className="bg-background border border-border rounded-lg px-3 py-2 text-foreground text-sm focus:outline-none focus:border-blue-500">
                            {MONTHS_DAYS.map(d => <option key={d} value={d}>{t("schedule.dayOption", { d })}</option>)}
                        </select>
                    </div>
                )}
            </div>

            <p className="text-[11px] text-blue-400 flex items-center gap-1.5">
                <Clock className="w-3 h-3" />
                {cronToHuman(value, t)}
            </p>
        </div>
    );
}
