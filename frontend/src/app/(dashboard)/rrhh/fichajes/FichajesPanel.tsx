"use client";

import { useTranslations } from "next-intl";
import { Timer, Plus, LogOut, Loader2, UserCheck } from "lucide-react";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
    Select,
    SelectTrigger,
    SelectValue,
    SelectContent,
    SelectItem,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { useFichajes, useElapsedTime } from "./_hooks/useFichajes";

function ElapsedCell({ clockIn }: { clockIn: string }) {
    const elapsed = useElapsedTime(clockIn);
    return <span className="tabular-nums text-emerald-400 font-medium">{elapsed}</span>;
}

export function FichajesPanel() {
    const t = useTranslations("rrhh");
    const tc = useTranslations("common");
    const {
        employees, working, todayRecords, isLoading,
        showModal, setShowModal,
        clockInEmpId, setClockInEmpId,
        clockInNotes, setClockInNotes,
        submitting,
        handleClockIn, handleClockOut,
        getEmployee, formatTime, formatDuration,
    } = useFichajes();

    if (isLoading) {
        return (
            <div className="p-8 flex items-center justify-center text-muted-foreground gap-2">
                <Loader2 className="w-4 h-4 animate-spin" /> {t("fichajes.loading")}
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <PageHeader
                title={t("fichajes.title")}
                description={t("fichajes.description")}
                icon={Timer}
                actions={
                    <Button onClick={() => setShowModal(true)}>
                        <Plus className="w-4 h-4 mr-2" /> {t("fichajes.clockIn")}
                    </Button>
                }
            />

            {/* Currently working */}
            <div>
                <h2 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
                    <span className="relative flex h-2 w-2">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                        <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
                    </span>
                    {t("fichajes.workingNow", { n: working.length })}
                </h2>

                {working.length === 0 ? (
                    <div className="text-sm text-muted-foreground border-2 border-dashed border-border rounded-xl p-6 text-center">
                        {t("fichajes.nobodyWorking")}
                    </div>
                ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                        {working.map((record) => {
                            const emp = getEmployee(record.employee_id);
                            return (
                                <Card key={record.id} className="border-emerald-500/20 bg-emerald-500/5">
                                    <CardContent className="p-4">
                                        <div className="flex items-start justify-between mb-3">
                                            <div className="flex items-center gap-2.5">
                                                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-emerald-500/20 text-xs font-medium text-emerald-400 border border-emerald-500/30">
                                                    {emp ? emp.name.substring(0, 2).toUpperCase() : "??"}
                                                </div>
                                                <div>
                                                    <p className="text-sm font-medium text-foreground">{emp?.name ?? "—"}</p>
                                                    <p className="text-xs text-muted-foreground">{emp?.role || emp?.department || "—"}</p>
                                                </div>
                                            </div>
                                        </div>
                                        <div className="flex items-center justify-between">
                                            <div>
                                                <p className="text-xs text-muted-foreground">{t("fichajes.since", { time: formatTime(record.clock_in) })}</p>
                                                <ElapsedCell clockIn={record.clock_in} />
                                            </div>
                                            <Button
                                                size="sm"
                                                variant="outline"
                                                className="text-xs h-7 border-emerald-500/30 hover:bg-emerald-500/10"
                                                onClick={() => handleClockOut(record.id)}
                                            >
                                                <LogOut className="w-3 h-3 mr-1" /> {t("fichajes.clockOut")}
                                            </Button>
                                        </div>
                                        {record.notes && (
                                            <p className="text-xs text-muted-foreground mt-2 italic truncate">{record.notes}</p>
                                        )}
                                    </CardContent>
                                </Card>
                            );
                        })}
                    </div>
                )}
            </div>

            {/* Today's records */}
            <Card>
                <CardHeader className="pb-3">
                    <CardTitle className="text-sm font-medium flex items-center gap-2">
                        <UserCheck className="w-4 h-4 text-muted-foreground" />
                        {t("fichajes.todayLog", { n: todayRecords.length })}
                    </CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                    {todayRecords.length === 0 ? (
                        <p className="text-sm text-muted-foreground px-6 pb-6">{t("fichajes.noRecordsToday")}</p>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                                <thead>
                                    <tr className="border-b border-border text-xs text-muted-foreground">
                                        <th className="px-6 py-3 text-left font-medium">{t("fichajes.table.employee")}</th>
                                        <th className="px-4 py-3 text-left font-medium">{t("fichajes.table.clockIn")}</th>
                                        <th className="px-4 py-3 text-left font-medium">{t("fichajes.table.clockOut")}</th>
                                        <th className="px-4 py-3 text-left font-medium">{t("fichajes.table.duration")}</th>
                                        <th className="px-4 py-3 text-left font-medium">{t("fichajes.table.note")}</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {todayRecords.map((r) => {
                                        const emp = getEmployee(r.employee_id);
                                        return (
                                            <tr key={r.id} className="border-b border-border last:border-0 hover:bg-muted/30">
                                                <td className="px-6 py-3 text-foreground font-medium">{emp?.name ?? "—"}</td>
                                                <td className="px-4 py-3 text-foreground tabular-nums">{formatTime(r.clock_in)}</td>
                                                <td className="px-4 py-3 tabular-nums">
                                                    {r.clock_out
                                                        ? <span className="text-foreground">{formatTime(r.clock_out)}</span>
                                                        : <span className="text-emerald-400 text-xs">{t("fichajes.inProgress")}</span>}
                                                </td>
                                                <td className="px-4 py-3 text-muted-foreground tabular-nums">
                                                    {formatDuration(r.clock_in, r.clock_out)}
                                                </td>
                                                <td className="px-4 py-3 text-muted-foreground text-xs">{r.notes || "—"}</td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Clock-in modal */}
            {showModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
                    <div className="bg-card border border-border rounded-2xl p-6 w-full max-w-sm shadow-2xl mx-4">
                        <h2 className="text-lg font-semibold text-foreground mb-4">{t("fichajes.modal.title")}</h2>
                        <div className="space-y-4">
                            <div>
                                <label className="text-sm text-muted-foreground mb-1.5 block">{t("fichajes.table.employee")}</label>
                                <Select value={clockInEmpId} onValueChange={setClockInEmpId}>
                                    <SelectTrigger>
                                        <SelectValue placeholder={t("fichajes.modal.selectEmployee")} />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {employees.map((e) => (
                                            <SelectItem key={e.id} value={e.id}>{e.name}</SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                            <div>
                                <label className="text-sm text-muted-foreground mb-1.5 block">{t("fichajes.modal.noteOptional")}</label>
                                <Input
                                    value={clockInNotes}
                                    onChange={(e) => setClockInNotes(e.target.value)}
                                    placeholder={t("fichajes.modal.notePlaceholder")}
                                />
                            </div>
                        </div>
                        <div className="flex justify-end gap-2 mt-6">
                            <Button variant="ghost" onClick={() => setShowModal(false)}>{tc("cancel")}</Button>
                            <Button disabled={!clockInEmpId || submitting} onClick={handleClockIn}>
                                {submitting ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                                {t("fichajes.clockIn")}
                            </Button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
