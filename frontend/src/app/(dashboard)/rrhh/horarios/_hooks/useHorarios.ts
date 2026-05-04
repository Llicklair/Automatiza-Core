"use client";

import { useEffect, useState, useCallback } from "react";
import { api, Employee, WorkSchedule } from "@/lib/api";
import { useToastStore } from "@/stores/toast";
import { logError } from "@/lib/logger";

export const DAYS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"];
export const DAYS_FULL = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];

export type DaySchedule = { start_time: string; end_time: string; active: boolean };
export type EmployeeSchedule = Record<number, DaySchedule>;

function parseMinutes(time: string): number {
    const [h, m] = time.split(":").map(Number);
    return h * 60 + m;
}

export function calcWeeklyHours(sched: EmployeeSchedule): number {
    return DAYS.reduce((total, _, i) => {
        const day = sched[i];
        if (!day?.active || !day.start_time || !day.end_time) return total;
        return total + Math.max(0, parseMinutes(day.end_time) - parseMinutes(day.start_time)) / 60;
    }, 0);
}

const DEFAULT_DAY: DaySchedule = { start_time: "09:00", end_time: "17:00", active: false };

function buildGrid(schedules: WorkSchedule[]): EmployeeSchedule {
    const grid: EmployeeSchedule = {};
    for (let i = 0; i < 7; i++) grid[i] = { ...DEFAULT_DAY };
    for (const s of schedules) {
        grid[s.day_of_week] = { start_time: s.start_time, end_time: s.end_time, active: s.active };
    }
    return grid;
}

export function useHorarios() {
    const toast = useToastStore();
    const [employees, setEmployees] = useState<Employee[]>([]);
    const [grids, setGrids] = useState<Record<string, EmployeeSchedule>>({});
    const [saving, setSaving] = useState<Record<string, boolean>>({});
    const [isLoading, setIsLoading] = useState(true);

    const loadData = useCallback(async () => {
        setIsLoading(true);
        try {
            const [emps, allSchedules] = await Promise.all([
                api.hr.employees.list(),
                api.hr.schedules.list(),
            ]);
            const activeEmps = emps.filter((e) => e.status !== "inactive");
            setEmployees(activeEmps);
            const initialGrids: Record<string, EmployeeSchedule> = {};
            for (const emp of activeEmps) {
                const rows: WorkSchedule[] = allSchedules[emp.id] ?? [];
                initialGrids[emp.id] = buildGrid(rows);
            }
            setGrids(initialGrids);
        } catch (err) {
            logError("rrhh/horarios", err);
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => { loadData(); }, [loadData]);

    const updateCell = (empId: string, day: number, field: keyof DaySchedule, value: string | boolean) => {
        setGrids((prev) => ({
            ...prev,
            [empId]: { ...prev[empId], [day]: { ...prev[empId][day], [field]: value } },
        }));
    };

    const handleSave = async (empId: string) => {
        setSaving((s) => ({ ...s, [empId]: true }));
        try {
            const grid = grids[empId];
            const schedules = Object.entries(grid).map(([day, d]) => ({
                day_of_week: Number(day),
                start_time: d.start_time,
                end_time: d.end_time,
                active: d.active,
            }));
            await api.hr.schedules.upsert(empId, schedules);
            toast.success("Horario guardado");
        } catch (err) {
            toast.error(err instanceof Error ? err.message : "Error al guardar");
        } finally {
            setSaving((s) => ({ ...s, [empId]: false }));
        }
    };

    type AISuggestion = {
        employee_id: string;
        schedule: Record<string, { start_time: string; end_time: string; active: boolean }>;
    };

    const applyAISuggestions = useCallback((suggestions: AISuggestion[]) => {
        setGrids((prev) => {
            const next = { ...prev };
            for (const s of suggestions) {
                const newGrid: EmployeeSchedule = {};
                for (let i = 0; i < 7; i++) {
                    const day = s.schedule[String(i)] ?? s.schedule[i] ?? DEFAULT_DAY;
                    newGrid[i] = {
                        start_time: day.start_time || "09:00",
                        end_time: day.end_time || "17:00",
                        active: !!day.active,
                    };
                }
                next[s.employee_id] = newGrid;
            }
            return next;
        });
    }, []);

    return { employees, grids, saving, isLoading, updateCell, handleSave, applyAISuggestions };
}

// ── Export helpers ────────────────────────────────────────────────────────────

export function buildScheduleCSV(
    employees: Employee[],
    grids: Record<string, EmployeeSchedule>
): string {
    const header = ["Empleado", "Rol", "Departamento", ...DAYS_FULL, "Horas/semana"];
    const rows = employees.map((emp) => {
        const grid = grids[emp.id] ?? {};
        const cells = DAYS_FULL.map((_, i) => {
            const day = grid[i];
            return day?.active ? `${day.start_time}-${day.end_time}` : "";
        });
        return [
            emp.name,
            emp.role || "",
            emp.department || "",
            ...cells,
            calcWeeklyHours(grid).toFixed(1),
        ];
    });

    const escape = (v: string) => {
        if (/[",\n;]/.test(v)) return `"${v.replace(/"/g, '""')}"`;
        return v;
    };
    const lines = [header, ...rows].map((row) => row.map(escape).join(";"));
    // Use UTF-8 BOM so Excel detects the encoding correctly
    return "﻿" + lines.join("\r\n");
}

export function buildScheduleHTML(
    employees: Employee[],
    grids: Record<string, EmployeeSchedule>
): string {
    const headerCells = ["Empleado", ...DAYS_FULL, "h/sem"]
        .map((h) => `<th style="background:#f3f4f6;border:1px solid #d1d5db;padding:6px 10px;font-size:12px;text-align:left;">${h}</th>`)
        .join("");
    const bodyRows = employees.map((emp) => {
        const grid = grids[emp.id] ?? {};
        const cells = DAYS_FULL.map((_, i) => {
            const day = grid[i];
            const value = day?.active ? `${day.start_time}–${day.end_time}` : "—";
            return `<td style="border:1px solid #e5e7eb;padding:5px 8px;font-size:12px;color:#374151;">${value}</td>`;
        }).join("");
        const weekly = calcWeeklyHours(grid).toFixed(1);
        const role = emp.role || emp.department || "";
        return `<tr>
            <td style="border:1px solid #e5e7eb;padding:5px 8px;font-size:12px;color:#111827;font-weight:500;">
                ${emp.name}${role ? `<br/><span style="color:#6b7280;font-size:11px;font-weight:400;">${role}</span>` : ""}
            </td>
            ${cells}
            <td style="border:1px solid #e5e7eb;padding:5px 8px;font-size:12px;color:#374151;text-align:right;">${weekly}h</td>
        </tr>`;
    }).join("");

    return `<table style="border-collapse:collapse;font-family:Arial,sans-serif;">
        <thead><tr>${headerCells}</tr></thead>
        <tbody>${bodyRows}</tbody>
    </table>`;
}

export function downloadCSV(filename: string, csv: string) {
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}
