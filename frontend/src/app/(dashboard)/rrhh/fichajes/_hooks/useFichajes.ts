"use client";

import { useEffect, useState, useCallback } from "react";
import { useTranslations } from "next-intl";
import { useFormat } from "@/hooks/useFormat";
import { api, Employee, AttendanceRecord } from "@/lib/api";
import type { AttendanceSummaryRow } from "@/lib/api/hr";
import { useToastStore } from "@/stores/toast";
import { logError } from "@/lib/logger";
import { usePolling } from "@/lib/hooks/usePolling";

export function useElapsedTime(clockIn: string | null): string {
    // `now` se actualiza vía intervalo; leerlo (en vez de Date.now() directo en
    // render) mantiene el reloj en vivo sin violar react-hooks/purity.
    const [now, setNow] = useState(() => Date.now());
    useEffect(() => {
        if (!clockIn) return;
        const id = setInterval(() => setNow(Date.now()), 1000);
        return () => clearInterval(id);
    }, [clockIn]);

    if (!clockIn) return "—";
    const diff = Math.floor((now - new Date(clockIn).getTime()) / 1000);
    const h = Math.floor(diff / 3600);
    const m = Math.floor((diff % 3600) / 60);
    const s = diff % 60;
    return h > 0
        ? `${h}h ${String(m).padStart(2, "0")}m`
        : `${String(m).padStart(2, "0")}m ${String(s).padStart(2, "0")}s`;
}

export function useFichajes() {
    const t = useTranslations("rrhh");
    const { fmtTime } = useFormat();
    const toast = useToastStore();
    const [employees, setEmployees] = useState<Employee[]>([]);
    const [working, setWorking] = useState<AttendanceRecord[]>([]);
    const [todayRecords, setTodayRecords] = useState<AttendanceRecord[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);
    const [clockInEmpId, setClockInEmpId] = useState("");
    const [clockInNotes, setClockInNotes] = useState("");
    const [submitting, setSubmitting] = useState(false);
    // Resumen de horas por empleado (registro de jornada): rango por defecto,
    // del día 1 del mes actual a hoy.
    const [sumDesde, setSumDesde] = useState(() => {
        const n = new Date();
        return `${n.getFullYear()}-${String(n.getMonth() + 1).padStart(2, "0")}-01`;
    });
    const [sumHasta, setSumHasta] = useState(() => new Date().toISOString().slice(0, 10));
    const [summary, setSummary] = useState<AttendanceSummaryRow[]>([]);

    const loadData = useCallback(async () => {
        try {
            const [emps, nowRecords, todayList] = await Promise.all([
                api.hr.employees.list(),
                api.hr.attendance.now(),
                api.hr.attendance.list(),
            ]);
            setEmployees(emps.filter((e) => e.status === "active"));
            setWorking(nowRecords);
            setTodayRecords(todayList);
        } catch (err) {
            logError("rrhh/fichajes", err);
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        loadData();
    }, [loadData]);

    usePolling(loadData, 60_000);

    // Recarga el resumen al cambiar el rango y tras cada fichaje (todayRecords
    // cambia de referencia en cada loadData).
    useEffect(() => {
        if (!sumDesde || !sumHasta || sumHasta < sumDesde) return;
        api.hr.attendance
            .summary(sumDesde, sumHasta)
            .then(setSummary)
            .catch((err) => logError("rrhh/fichajes.summary", err));
    }, [sumDesde, sumHasta, todayRecords]);

    const formatHoras = (minutos: number): string => {
        const h = Math.floor(minutos / 60);
        const m = minutos % 60;
        return h > 0 ? `${h}h ${String(m).padStart(2, "0")}m` : `${m}m`;
    };

    const handleClockIn = async () => {
        if (!clockInEmpId) return;
        setSubmitting(true);
        try {
            await api.hr.attendance.clockIn(clockInEmpId, clockInNotes || undefined);
            toast.success(t("toasts.clockInSuccess"));
            setShowModal(false);
            setClockInEmpId("");
            setClockInNotes("");
            await loadData();
        } catch (err) {
            toast.error(err instanceof Error ? err.message : t("toasts.clockInError"));
        } finally {
            setSubmitting(false);
        }
    };

    const handleClockOut = async (attendanceId: string) => {
        try {
            await api.hr.attendance.clockOut(attendanceId);
            toast.success(t("toasts.clockOutSuccess"));
            await loadData();
        } catch (err) {
            toast.error(err instanceof Error ? err.message : t("toasts.clockOutError"));
        }
    };

    const getEmployee = (id: string) => employees.find((e) => e.id === id);

    const isWorking = (empId: string) => working.some((r) => r.employee_id === empId);

    const formatTime = (iso: string | null) =>
        iso ? fmtTime(iso, { hour: "2-digit", minute: "2-digit" }) : "—";

    const formatDuration = (clockIn: string, clockOut: string | null): string => {
        const end = clockOut ? new Date(clockOut).getTime() : Date.now();
        const diff = Math.floor((end - new Date(clockIn).getTime()) / 60000);
        const h = Math.floor(diff / 60);
        const m = diff % 60;
        return h > 0 ? `${h}h ${m}m` : `${m}m`;
    };

    return {
        employees, working, todayRecords, isLoading,
        showModal, setShowModal,
        clockInEmpId, setClockInEmpId,
        clockInNotes, setClockInNotes,
        submitting,
        handleClockIn, handleClockOut,
        getEmployee, isWorking, formatTime, formatDuration,
        summary, sumDesde, setSumDesde, sumHasta, setSumHasta, formatHoras,
    };
}
