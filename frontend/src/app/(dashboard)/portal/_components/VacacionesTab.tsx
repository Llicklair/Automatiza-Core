"use client";
import { Umbrella, Plus, Check, Clock, X } from "lucide-react";
import type { LeaveRequest } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { STATUS_BADGE, LEAVE_LABEL, fmt } from "./constants";

interface VacacionesTabProps {
    leaveRequests: LeaveRequest[];
    readOnly: boolean;
    onNewRequest: () => void;
}

export function VacacionesTab({ leaveRequests, readOnly, onNewRequest }: VacacionesTabProps) {
    return (
        <div className="space-y-4">
            <div className="flex items-start justify-between gap-4">
                <p className="text-xs text-muted-foreground max-w-xl">
                    Solicita vacaciones, bajas u otras ausencias. Cada petición pasa por aprobación
                    y verás aquí su estado en cualquier momento.
                </p>
                <Button size="sm" className="gap-2 shrink-0" disabled={readOnly} onClick={onNewRequest}>
                    <Plus className="w-4 h-4" /> Nueva solicitud
                </Button>
            </div>
            {leaveRequests.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-40 gap-2 text-muted-foreground">
                    <Umbrella className="w-8 h-8 opacity-30" />
                    <p className="text-sm">No tienes solicitudes de ausencia</p>
                    <p className="text-xs max-w-xs text-center">
                        Pulsa <strong>Nueva solicitud</strong> arriba para pedir vacaciones, baja médica o excedencia.
                    </p>
                </div>
            ) : (
                <div className="rounded-xl border border-border overflow-hidden">
                    <table className="w-full text-sm">
                        <thead className="bg-muted/30 text-muted-foreground">
                            <tr>
                                <th className="text-left px-4 py-3 font-medium">Tipo</th>
                                <th className="text-left px-4 py-3 font-medium">Desde</th>
                                <th className="text-left px-4 py-3 font-medium">Hasta</th>
                                <th className="text-left px-4 py-3 font-medium">Días</th>
                                <th className="text-left px-4 py-3 font-medium">Estado</th>
                                <th className="text-left px-4 py-3 font-medium">Notas</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-border">
                            {leaveRequests.map((lr: LeaveRequest) => {
                                const days = Math.round((new Date(lr.end_date).getTime() - new Date(lr.start_date).getTime()) / 86400000) + 1;
                                return (
                                    <tr key={lr.id} className="bg-card hover:bg-muted/20 transition-colors">
                                        <td className="px-4 py-3 font-medium text-foreground capitalize">
                                            {lr.leave_type.replace("_", " ")}
                                        </td>
                                        <td className="px-4 py-3 text-muted-foreground">{fmt(lr.start_date)}</td>
                                        <td className="px-4 py-3 text-muted-foreground">{fmt(lr.end_date)}</td>
                                        <td className="px-4 py-3 text-muted-foreground">{days}d</td>
                                        <td className="px-4 py-3">
                                            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${STATUS_BADGE[lr.status] ?? ""}`}>
                                                {lr.status === "approved" && <Check className="w-3 h-3" />}
                                                {lr.status === "rejected" && <X className="w-3 h-3" />}
                                                {lr.status === "pending" && <Clock className="w-3 h-3" />}
                                                {LEAVE_LABEL[lr.status] ?? lr.status}
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
