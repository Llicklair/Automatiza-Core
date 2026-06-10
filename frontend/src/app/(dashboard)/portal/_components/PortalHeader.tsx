"use client";
import { User, Clock, Loader2, Eye, Play, StopCircle } from "lucide-react";
import type { PortalData, Employee } from "@/lib/api";
import { formatClockTime } from "./constants";

interface PortalHeaderProps {
    emp: PortalData["employee"] | undefined;
    data: PortalData | null;
    isAdmin: boolean;
    readOnly: boolean;
    employeesList: Employee[];
    selectedEmployeeId: string;
    clockBusy: boolean;
    clockError: string | null;
    onSelectEmployee: (empId: string) => void;
    onClockIn: () => void;
    onClockOut: () => void;
}

export function PortalHeader({
    emp, data, isAdmin, readOnly, employeesList, selectedEmployeeId,
    clockBusy, clockError, onSelectEmployee, onClockIn, onClockOut,
}: PortalHeaderProps) {
    return (
        <div className="space-y-3">
            <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-full bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center">
                    <User className="w-6 h-6 text-indigo-400" />
                </div>
                <div>
                    <h1 className="text-2xl font-bold text-foreground">{emp?.name ?? "Mi portal"}</h1>
                    <p className="text-xs text-muted-foreground">
                        {emp ? [emp.role, emp.department].filter(Boolean).join(" · ") : "Autoservicio del empleado"}
                    </p>
                </div>
            </div>
            <p className="text-sm text-muted-foreground max-w-2xl">
                Tu zona personal. Aquí consultas tu ficha, descargas tus nóminas,
                solicitas vacaciones y reportas gastos para reembolso. Todo lo que envías
                queda registrado y pasa por la aprobación de RRHH.
            </p>

            {isAdmin && (
                <div className="flex items-center gap-3 p-3 bg-card border border-border rounded-xl">
                    <Eye className="w-4 h-4 text-muted-foreground shrink-0" />
                    <div className="flex-1">
                        <p className="text-xs font-medium text-foreground mb-1">Vista de admin</p>
                        <p className="text-xs text-muted-foreground">
                            Como admin no tienes ficha aquí. Selecciona un empleado para previsualizar Mi portal en modo lectura.
                        </p>
                    </div>
                    <select
                        value={selectedEmployeeId}
                        onChange={(e) => onSelectEmployee(e.target.value)}
                        className="bg-muted border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:border-primary/20 outline-none min-w-[220px]"
                    >
                        <option value="">— Mi propio portal —</option>
                        {employeesList.map((e) => (
                            <option key={e.id} value={e.id}>
                                {e.name}{e.email ? ` · ${e.email}` : ""}
                            </option>
                        ))}
                    </select>
                </div>
            )}

            {readOnly && (
                <div className="flex items-center gap-2 p-3 bg-amber-500/10 border border-amber-500/20 rounded-xl text-xs text-amber-300">
                    <Eye className="w-4 h-4 shrink-0" />
                    <span>Estás viendo Mi portal de otro empleado en <strong>modo lectura</strong>. No puedes solicitar vacaciones ni gastos en su nombre.</span>
                </div>
            )}

            {emp && (
                <div className="flex items-center gap-3 p-3 bg-card border border-border rounded-xl">
                    <Clock className={`w-5 h-5 shrink-0 ${data?.active_attendance ? "text-emerald-400" : "text-muted-foreground"}`} />
                    <div className="flex-1">
                        <p className="text-xs font-medium text-foreground">
                            {data?.active_attendance
                                ? `Trabajando desde las ${formatClockTime(data.active_attendance.clock_in)}`
                                : "No tienes ningún fichaje activo"}
                        </p>
                        <p className="text-xs text-muted-foreground">
                            {data?.active_attendance
                                ? "Recuerda fichar la salida al terminar tu jornada."
                                : "Pulsa para registrar tu entrada cuando empieces a trabajar."}
                        </p>
                    </div>
                    {data?.active_attendance ? (
                        <button
                            onClick={onClockOut}
                            disabled={readOnly || clockBusy}
                            className="flex items-center gap-2 bg-red-500/10 border border-red-500/30 text-red-400 hover:bg-red-500/20 px-4 py-2 rounded-xl text-sm font-medium disabled:opacity-50"
                        >
                            {clockBusy ? <Loader2 className="w-4 h-4 animate-spin" /> : <StopCircle className="w-4 h-4" />}
                            Fichar salida
                        </button>
                    ) : (
                        <button
                            onClick={onClockIn}
                            disabled={readOnly || clockBusy}
                            className="flex items-center gap-2 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/20 px-4 py-2 rounded-xl text-sm font-medium disabled:opacity-50"
                        >
                            {clockBusy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                            Fichar entrada
                        </button>
                    )}
                </div>
            )}

            {clockError && (
                <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-xl text-xs text-destructive">
                    {clockError}
                </div>
            )}
        </div>
    );
}
