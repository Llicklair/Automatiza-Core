"use client";
import { Umbrella, Plus, Check, Clock, X } from "lucide-react";
import { useTranslations } from "next-intl";
import type { LeaveRequest } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { STATUS_BADGE, fmt } from "./constants";

interface VacacionesTabProps {
    leaveRequests: LeaveRequest[];
    readOnly: boolean;
    onNewRequest: () => void;
}

export function VacacionesTab({ leaveRequests, readOnly, onNewRequest }: VacacionesTabProps) {
    const t = useTranslations("portal");
    return (
        <div className="space-y-4">
            <div className="flex items-start justify-between gap-4">
                <p className="text-xs text-muted-foreground max-w-xl">
                    {t("vacaciones.intro")}
                </p>
                <Button size="sm" className="gap-2 shrink-0" disabled={readOnly} onClick={onNewRequest}>
                    <Plus className="w-4 h-4" /> {t("vacaciones.newRequest")}
                </Button>
            </div>
            {leaveRequests.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-40 gap-2 text-muted-foreground">
                    <Umbrella className="w-8 h-8 opacity-30" />
                    <p className="text-sm">{t("vacaciones.emptyTitle")}</p>
                    <p className="text-xs max-w-xs text-center">
                        {t.rich("vacaciones.emptyHint", { strong: (chunks) => <strong>{chunks}</strong> })}
                    </p>
                </div>
            ) : (
                <div className="rounded-xl border border-border overflow-hidden">
                    <table className="w-full text-sm">
                        <thead className="bg-muted/30 text-muted-foreground">
                            <tr>
                                <th className="text-left px-4 py-3 font-medium">{t("vacaciones.colType")}</th>
                                <th className="text-left px-4 py-3 font-medium">{t("vacaciones.colFrom")}</th>
                                <th className="text-left px-4 py-3 font-medium">{t("vacaciones.colTo")}</th>
                                <th className="text-left px-4 py-3 font-medium">{t("vacaciones.colDays")}</th>
                                <th className="text-left px-4 py-3 font-medium">{t("vacaciones.colStatus")}</th>
                                <th className="text-left px-4 py-3 font-medium">{t("vacaciones.colNotes")}</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-border">
                            {leaveRequests.map((lr: LeaveRequest) => {
                                const days = Math.round((new Date(lr.end_date).getTime() - new Date(lr.start_date).getTime()) / 86400000) + 1;
                                return (
                                    <tr key={lr.id} className="bg-card hover:bg-muted/20 transition-colors">
                                        <td className="px-4 py-3 font-medium text-foreground capitalize">
                                            {t.has(`leaveTypes.${lr.leave_type}`) ? t(`leaveTypes.${lr.leave_type}`) : lr.leave_type.replace("_", " ")}
                                        </td>
                                        <td className="px-4 py-3 text-muted-foreground">{fmt(lr.start_date)}</td>
                                        <td className="px-4 py-3 text-muted-foreground">{fmt(lr.end_date)}</td>
                                        <td className="px-4 py-3 text-muted-foreground">{t("vacaciones.days", { count: days })}</td>
                                        <td className="px-4 py-3">
                                            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${STATUS_BADGE[lr.status] ?? ""}`}>
                                                {lr.status === "approved" && <Check className="w-3 h-3" />}
                                                {lr.status === "rejected" && <X className="w-3 h-3" />}
                                                {lr.status === "pending" && <Clock className="w-3 h-3" />}
                                                {t.has(`leaveStatus.${lr.status}`) ? t(`leaveStatus.${lr.status}`) : lr.status}
                                            </span>
                                        </td>
                                        <td className="px-4 py-3 text-xs text-muted-foreground max-w-[140px] truncate">{lr.notes ?? "—"}</td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}
