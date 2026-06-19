"use client";

import Link from "next/link";
import { Users, Timer, BedDouble, ArrowRight } from "lucide-react";
import { useTranslations } from "next-intl";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { Employee, AttendanceRecord } from "@/lib/api";

interface RrhhWidgetProps {
    employees: Employee[];
    working: AttendanceRecord[];
    loading: boolean;
}

const LEAVE_LABEL_KEY: Record<string, string> = {
    baja_medica: "rrhh.leaveMedical",
    vacaciones: "rrhh.leaveVacation",
    excedencia: "rrhh.leaveSabbatical",
};

export function RrhhWidget({ employees, working, loading }: RrhhWidgetProps) {
    const t = useTranslations("dashboard");
    if (loading) return null;

    const active = employees.filter((e) => e.status === "active");
    const onLeave = employees.filter((e) => e.status === "leave");

    return (
        <Card>
            <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                    <CardTitle className="text-sm font-medium flex items-center gap-2">
                        <Users className="w-4 h-4 text-muted-foreground" />
                        {t("rrhh.title")}
                    </CardTitle>
                    <Link href="/rrhh" className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1 transition-colors">
                        {t("rrhh.viewHr")} <ArrowRight className="w-3 h-3" />
                    </Link>
                </div>
            </CardHeader>
            <CardContent className="space-y-4">
                {/* Summary row */}
                <div className="grid grid-cols-3 gap-3 text-center">
                    <div className="bg-muted/50 rounded-lg p-3">
                        <p className="text-xl font-bold text-foreground">{active.length}</p>
                        <p className="text-xs text-muted-foreground mt-0.5">{t("rrhh.active")}</p>
                    </div>
                    <div className="bg-emerald-500/10 rounded-lg p-3">
                        <p className="text-xl font-bold text-emerald-400">{working.length}</p>
                        <p className="text-xs text-muted-foreground mt-0.5">{t("rrhh.working")}</p>
                    </div>
                    <div className="bg-amber-500/10 rounded-lg p-3">
                        <p className="text-xl font-bold text-amber-400">{onLeave.length}</p>
                        <p className="text-xs text-muted-foreground mt-0.5">{t("rrhh.onLeave")}</p>
                    </div>
                </div>

                {/* Currently working */}
                {working.length > 0 && (
                    <div>
                        <p className="text-xs font-medium text-muted-foreground mb-2 flex items-center gap-1.5">
                            <span className="relative flex h-1.5 w-1.5">
                                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                                <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-500" />
                            </span>
                            {t("rrhh.rightNow")}
                        </p>
                        <div className="space-y-1.5">
                            {working.slice(0, 4).map((r) => {
                                const emp = employees.find((e) => e.id === r.employee_id);
                                return (
                                    <div key={r.id} className="flex items-center gap-2">
                                        <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-muted text-[10px] font-medium text-foreground border border-border">
                                            {emp ? emp.name.substring(0, 2).toUpperCase() : "??"}
                                        </div>
                                        <span className="text-xs text-foreground truncate flex-1">{emp?.name ?? "—"}</span>
                                        <span className="text-[10px] text-muted-foreground">
                                            {new Date(r.clock_in).toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" })}
                                        </span>
                                    </div>
                                );
                            })}
                            {working.length > 4 && (
                                <p className="text-xs text-muted-foreground pl-8">{t("rrhh.more", { count: working.length - 4 })}</p>
                            )}
                        </div>
                    </div>
                )}

                {/* On leave */}
                {onLeave.length > 0 && (
                    <div>
                        <p className="text-xs font-medium text-muted-foreground mb-2 flex items-center gap-1.5">
                            <BedDouble className="w-3 h-3" /> {t("rrhh.onLeave")}
                        </p>
                        <div className="space-y-1.5">
                            {onLeave.slice(0, 3).map((emp) => (
                                <div key={emp.id} className="flex items-center gap-2">
                                    <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-muted text-[10px] font-medium text-foreground border border-border">
                                        {emp.name.substring(0, 2).toUpperCase()}
                                    </div>
                                    <span className="text-xs text-foreground truncate flex-1">{emp.name}</span>
                                    <Badge variant="outline" className="text-[10px] px-1.5 py-0 bg-amber-500/10 text-amber-400 border-amber-500/20">
                                        {LEAVE_LABEL_KEY[emp.leave_type ?? ""] ? t(LEAVE_LABEL_KEY[emp.leave_type ?? ""]) : t("rrhh.leaveGeneric")}
                                    </Badge>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {working.length === 0 && onLeave.length === 0 && (
                    <Link href="/rrhh/fichajes" className="flex items-center justify-center gap-2 text-xs text-muted-foreground hover:text-foreground transition-colors py-2">
                        <Timer className="w-3.5 h-3.5" /> {t("rrhh.clockIn")}
                    </Link>
                )}
            </CardContent>
        </Card>
    );
}
