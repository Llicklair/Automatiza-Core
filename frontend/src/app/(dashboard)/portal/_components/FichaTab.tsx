"use client";
import { Download } from "lucide-react";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api";
import type { PortalData } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { DAY_KEYS, fmt, currency } from "./constants";

interface FichaTabProps {
    emp: NonNullable<PortalData["employee"]>;
    data: PortalData | null;
}

export function FichaTab({ emp, data }: FichaTabProps) {
    const t = useTranslations("portal");
    return (
        <div className="space-y-3">
            <p className="text-xs text-muted-foreground">
                {t("ficha.intro")}
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {[
                { label: t("ficha.fullName"), value: emp.name },
                { label: t("ficha.nif"), value: emp.nif ?? "—" },
                { label: t("ficha.email"), value: emp.email ?? "—" },
                { label: t("ficha.department"), value: emp.department ?? "—" },
                { label: t("ficha.role"), value: emp.role ?? "—" },
                { label: t("ficha.baseSalary"), value: emp.base_salary ? currency(emp.base_salary) : "—" },
                { label: t("ficha.joinDate"), value: emp.join_date ? fmt(emp.join_date) : "—" },
                { label: t("ficha.irpf"), value: emp.irpf_rate != null ? `${emp.irpf_rate}%` : "—" },
            ].map(({ label, value }) => (
                <div key={label} className="rounded-xl border border-border bg-card p-4 space-y-1">
                    <p className="text-xs text-muted-foreground">{label}</p>
                    <p className="text-sm font-medium text-foreground">{value}</p>
                </div>
            ))}
            {/* Status */}
            <div className="rounded-xl border border-border bg-card p-4 space-y-1">
                <p className="text-xs text-muted-foreground">{t("ficha.status")}</p>
                <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${
                    emp.status === "active" ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" :
                    emp.status === "leave"  ? "bg-amber-500/10 text-amber-400 border-amber-500/20" :
                    "bg-muted text-muted-foreground border-border"
                }`}>
                    {emp.status === "active" ? t("ficha.statusActive") : emp.status === "leave" ? t("ficha.statusLeave") : t("ficha.statusInactive")}
                </span>
            </div>
            </div>

            {/* Horario semanal estipulado */}
            <div className="rounded-xl border border-border bg-card overflow-hidden">
                <div className="px-4 py-3 border-b border-border flex items-center justify-between">
                    <div>
                        <p className="text-sm font-medium text-foreground">{t("ficha.scheduleTitle")}</p>
                        <p className="text-xs text-muted-foreground">
                            {t("ficha.scheduleHint")}
                        </p>
                    </div>
                    {(data?.schedule?.length ?? 0) > 0 && (
                        <Button
                            size="sm"
                            variant="outline"
                            onClick={() => api.portal.exportMySchedule("pdf").catch(() => {})}
                        >
                            <Download className="w-3.5 h-3.5 mr-1.5" />
                            {t("ficha.downloadPdf")}
                        </Button>
                    )}
                </div>
                <table className="w-full text-sm">
                    <thead>
                        <tr className="text-xs uppercase tracking-wider text-muted-foreground border-b border-border">
                            <th className="text-left font-medium px-4 py-2">{t("ficha.colDay")}</th>
                            <th className="text-left font-medium px-4 py-2">{t("ficha.colClockIn")}</th>
                            <th className="text-left font-medium px-4 py-2">{t("ficha.colClockOut")}</th>
                            <th className="text-right font-medium px-4 py-2">{t("ficha.colStatus")}</th>
                        </tr>
                    </thead>
                    <tbody>
                        {DAY_KEYS.map((dayKey, dayIdx) => {
                            const label = t(`days.${dayKey}`);
                            const slots = (data?.schedule ?? []).filter(s => s.day_of_week === dayIdx);
                            if (slots.length === 0) {
                                return (
                                    <tr key={dayIdx} className="border-b border-border last:border-0">
                                        <td className="px-4 py-2 text-foreground">{label}</td>
                                        <td className="px-4 py-2 text-muted-foreground" colSpan={2}>{t("ficha.dayOff")}</td>
                                        <td className="px-4 py-2 text-right text-muted-foreground text-xs">—</td>
                                    </tr>
                                );
                            }
                            return slots.map((s, idx) => (
                                <tr key={s.id ?? `${dayIdx}-${idx}`} className="border-b border-border last:border-0">
                                    <td className="px-4 py-2 text-foreground">{idx === 0 ? label : ""}</td>
                                    <td className="px-4 py-2 text-muted-foreground font-mono">{s.start_time}</td>
                                    <td className="px-4 py-2 text-muted-foreground font-mono">{s.end_time}</td>
                                    <td className="px-4 py-2 text-right">
                                        {s.active ? (
                                            <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">{t("ficha.slotActive")}</span>
                                        ) : (
                                            <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs bg-muted text-muted-foreground border border-border">{t("ficha.slotInactive")}</span>
                                        )}
                                    </td>
                                </tr>
                            ));
                        })}
                    </tbody>
                </table>
                {(!data?.schedule || data.schedule.length === 0) && (
                    <div className="px-4 py-3 text-xs text-muted-foreground border-t border-border">
                        {t("ficha.noSchedule")}
                    </div>
                )}
            </div>
        </div>
    );
}
