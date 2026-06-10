"use client";

import {
    Users, Briefcase, Building2, Plane, Coins, Timer,
} from "lucide-react";
import type { AnalyticsDashboard } from "@/lib/api";
import { KpiCard } from "./KpiCard";
import { SectionHeader } from "./SectionHeader";
import { fmt, fmtInt } from "./utils";

interface RrhhSectionProps {
    periodLabel: string;
    rrhh: AnalyticsDashboard["rrhh"];
}

export function RrhhSection({ periodLabel, rrhh }: RrhhSectionProps) {
    return (
        <section className="space-y-6">
            <SectionHeader icon={Briefcase} title="RRHH" subtitle="Plantilla, nóminas, jornadas y vacaciones" />
            {/* KPIs RRHH */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
                <KpiCard
                    label="Empleados activos"
                    value={`${fmtInt(rrhh.empleados_activos)}`}
                    sub={`${rrhh.por_departamento.length} departamentos`}
                    icon={Users}
                    color="indigo"
                />
                <KpiCard
                    label="Coste nóminas"
                    value={`${fmt(rrhh.coste_nominas_periodo)}€`}
                    sub={`Media: ${fmt(rrhh.coste_medio_empleado)}€/empleado`}
                    icon={Briefcase}
                    color="red"
                />
                <KpiCard
                    label="Horas extra"
                    value={`${fmt(rrhh.horas_extra_periodo)}h`}
                    sub={`Ordinarias: ${fmt(rrhh.horas_ordinarias_periodo)}h`}
                    icon={Timer}
                    color="amber"
                />
                <KpiCard
                    label="Vacaciones pendientes"
                    value={`${rrhh.vacaciones_pendientes}`}
                    sub={`${rrhh.vacaciones_aprobadas_periodo} aprobadas este periodo`}
                    icon={Plane}
                    color="emerald"
                />
            </div>

            {/* Plantilla por departamento + nóminas */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="bg-card border border-border rounded-2xl p-6">
                    <h2 className="text-sm font-semibold text-foreground mb-1 flex items-center gap-2">
                        <Building2 className="w-4 h-4 text-primary" /> Plantilla por departamento
                    </h2>
                    <p className="text-xs text-muted-foreground mb-5">Empleados activos y coste base anual</p>
                    {rrhh.por_departamento.length === 0 ? (
                        <div className="h-[140px] flex items-center justify-center text-sm text-muted-foreground">
                            Sin empleados activos
                        </div>
                    ) : (
                        <div className="overflow-hidden rounded-xl border border-border">
                            <table className="w-full text-xs">
                                <thead className="bg-muted">
                                    <tr>
                                        <th className="text-left py-2 px-3 text-muted-foreground font-medium">Departamento</th>
                                        <th className="text-right py-2 px-3 text-muted-foreground font-medium">Empleados</th>
                                        <th className="text-right py-2 px-3 text-muted-foreground font-medium">Coste base</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {rrhh.por_departamento.map(d => (
                                        <tr key={d.departamento} className="border-t border-border">
                                            <td className="py-2 px-3 text-foreground font-medium">{d.departamento}</td>
                                            <td className="py-2 px-3 text-right text-foreground">{d.empleados}</td>
                                            <td className="py-2 px-3 text-right text-foreground font-semibold">{fmt(d.coste_base)}€</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>

                <div className="bg-card border border-border rounded-2xl p-6">
                    <h2 className="text-sm font-semibold text-foreground mb-1 flex items-center gap-2">
                        <Briefcase className="w-4 h-4 text-primary" /> Nóminas {periodLabel}
                    </h2>
                    <p className="text-xs text-muted-foreground mb-5">Estado de las nóminas del periodo</p>
                    <div className="grid grid-cols-2 gap-4">
                        <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4">
                            <p className="text-xs text-emerald-400 uppercase tracking-wide">Pagadas</p>
                            <p className="text-2xl font-bold text-emerald-400 mt-1">{rrhh.nominas_pagadas}</p>
                        </div>
                        <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4">
                            <p className="text-xs text-amber-400 uppercase tracking-wide">Pendientes</p>
                            <p className="text-2xl font-bold text-amber-400 mt-1">{rrhh.nominas_pendientes}</p>
                        </div>
                        <div className="rounded-xl border border-border bg-muted p-4 col-span-2">
                            <p className="text-xs text-muted-foreground uppercase tracking-wide">Coste total nóminas</p>
                            <p className="text-2xl font-bold text-foreground mt-1">{fmt(rrhh.coste_nominas_periodo)}€</p>
                            <p className="text-xs text-muted-foreground mt-1">
                                Media por empleado: <span className="text-foreground font-medium">{fmt(rrhh.coste_medio_empleado)}€</span>
                            </p>
                        </div>
                    </div>
                </div>
            </div>

            {/* Horas + Gastos */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="bg-card border border-border rounded-2xl p-6">
                    <h2 className="text-sm font-semibold text-foreground mb-1 flex items-center gap-2">
                        <Timer className="w-4 h-4 text-primary" /> Horas trabajadas
                    </h2>
                    <p className="text-xs text-muted-foreground mb-5">Jornadas registradas en {periodLabel}</p>
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <p className="text-xs text-muted-foreground uppercase tracking-wide">Ordinarias</p>
                            <p className="text-2xl font-bold text-foreground mt-1">{fmt(rrhh.horas_ordinarias_periodo)}h</p>
                        </div>
                        <div>
                            <p className="text-xs text-amber-400 uppercase tracking-wide">Extra</p>
                            <p className="text-2xl font-bold text-amber-400 mt-1">{fmt(rrhh.horas_extra_periodo)}h</p>
                        </div>
                    </div>
                    {rrhh.horas_ordinarias_periodo > 0 && (
                        <div className="mt-4 pt-4 border-t border-border text-xs text-muted-foreground">
                            Ratio horas extra:{" "}
                            <span className="text-foreground font-medium">
                                {((rrhh.horas_extra_periodo / (rrhh.horas_ordinarias_periodo + rrhh.horas_extra_periodo)) * 100).toFixed(1)}%
                            </span>
                        </div>
                    )}
                </div>

                <div className="bg-card border border-border rounded-2xl p-6">
                    <h2 className="text-sm font-semibold text-foreground mb-1 flex items-center gap-2">
                        <Coins className="w-4 h-4 text-primary" /> Gastos pendientes
                    </h2>
                    <p className="text-xs text-muted-foreground mb-5">Gastos de empleados sin aprobar</p>
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <p className="text-xs text-muted-foreground uppercase tracking-wide">Tickets</p>
                            <p className="text-2xl font-bold text-foreground mt-1">{rrhh.gastos_pendientes_count}</p>
                        </div>
                        <div>
                            <p className="text-xs text-red-400 uppercase tracking-wide">Importe</p>
                            <p className="text-2xl font-bold text-red-400 mt-1">{fmt(rrhh.gastos_pendientes_importe)}€</p>
                        </div>
                    </div>
                </div>
            </div>
        </section>
    );
}
