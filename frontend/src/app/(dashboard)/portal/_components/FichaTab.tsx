"use client";
import { Download } from "lucide-react";
import { api } from "@/lib/api";
import type { PortalData } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { DAY_LABELS, fmt, currency } from "./constants";

interface FichaTabProps {
    emp: NonNullable<PortalData["employee"]>;
    data: PortalData | null;
}

export function FichaTab({ emp, data }: FichaTabProps) {
    return (
        <div className="space-y-3">
            <p className="text-xs text-muted-foreground">
                Datos personales y laborales según tu ficha en RRHH. Si algo es incorrecto, avisa al administrador.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {[
                { label: "Nombre completo", value: emp.name },
                { label: "NIF", value: emp.nif ?? "—" },
                { label: "Email", value: emp.email ?? "—" },
                { label: "Departamento", value: emp.department ?? "—" },
                { label: "Rol", value: emp.role ?? "—" },
                { label: "Salario base", value: emp.base_salary ? currency(emp.base_salary) : "—" },
                { label: "Fecha de alta", value: emp.join_date ? fmt(emp.join_date) : "—" },
                { label: "IRPF", value: emp.irpf_rate != null ? `${emp.irpf_rate}%` : "—" },
            ].map(({ label, value }) => (
                <div key={label} className="rounded-xl border border-border bg-card p-4 space-y-1">
                    <p className="text-xs text-muted-foreground">{label}</p>
                    <p className="text-sm font-medium text-foreground">{value}</p>
                </div>
            ))}
            {/* Status */}
            <div className="rounded-xl border border-border bg-card p-4 space-y-1">
                <p className="text-xs text-muted-foreground">Estado</p>
                <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${
                    emp.status === "active" ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" :
                    emp.status === "leave"  ? "bg-amber-500/10 text-amber-400 border-amber-500/20" :
                    "bg-muted text-muted-foreground border-border"
                }`}>
                    {emp.status === "active" ? "Activo" : emp.status === "leave" ? "De baja" : "Inactivo"}
                </span>
            </div>
            </div>

            {/* Horario semanal estipulado */}
            <div className="rounded-xl border border-border bg-card overflow-hidden">
                <div className="px-4 py-3 border-b border-border flex items-center justify-between">
                    <div>
                        <p className="text-sm font-medium text-foreground">Horario estipulado</p>
                        <p className="text-xs text-muted-foreground">
                            Tu jornada semanal según la ficha que configuró RRHH.
                        </p>
                    </div>
                    {(data?.schedule?.length ?? 0) > 0 && (
                        <Button
                            size="sm"
                            variant="outline"
                            onClick={() => api.portal.exportMySchedule("pdf").catch(() => {})}
                        >
                            <Download className="w-3.5 h-3.5 mr-1.5" />
                            Descargar PDF
                        </Button>
                    )}
                </div>
                <table className="w-full text-sm">
                    <thead>
                        <tr className="text-xs uppercase tracking-wider text-muted-foreground border-b border-border">
                            <th className="text-left font-medium px-4 py-2">Día</th>
                            <th className="text-left font-medium px-4 py-2">Entrada</th>
                            <th className="text-left font-medium px-4 py-2">Salida</th>
                            <th className="text-right font-medium px-4 py-2">Estado</th>
                        </tr>
                    </thead>
                    <tbody>
                        {DAY_LABELS.map((label, dayIdx) => {
                            const slots = (data?.schedule ?? []).filter(s => s.day_of_week === dayIdx);
                            if (slots.length === 0) {
                                return (
                                    <tr key={dayIdx} className="border-b border-border last:border-0">
                                        <td className="px-4 py-2 text-foreground">{label}</td>
                                        <td className="px-4 py-2 text-muted-foreground" colSpan={2}>Día libre</td>
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
                                            <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Activo</span>
                                        ) : (
                                            <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs bg-muted text-muted-foreground border border-border">Inactivo</span>
                                        )}
                                    </td>
                                </tr>
                            ));
                        })}
                    </tbody>
                </table>
                {(!data?.schedule || data.schedule.length === 0) && (
                    <div className="px-4 py-3 text-xs text-muted-foreground border-t border-border">
                        Tu ficha aún no tiene horario configurado. Avisa a RRHH para que lo añada.
                    </div>
                )}
            </div>
        </div>
    );
}
