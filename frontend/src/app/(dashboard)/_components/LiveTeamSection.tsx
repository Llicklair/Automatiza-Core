"use client";

import { useMemo, useState } from "react";
import {
    Activity, Loader2, Calculator, Users, Mail, Briefcase, Wallet,
    Scale, FolderOpen, BarChart3, Megaphone, UserPlus, User,
} from "lucide-react";
import { useLiveTeam } from "../_hooks/useLiveTeam";
import type { AIEmployee } from "@/lib/api/ai_employees";

// ─── Mapeo dominio → colores y icono ────────────────────────────────────────
type DomainStyle = { from: string; to: string; ring: string; stroke: string; icon: React.ReactNode };
const DOMAIN: Record<string, DomainStyle> = {
    billing:     { from: "from-emerald-400",   to: "to-emerald-600",   ring: "ring-emerald-400",   stroke: "#34d399", icon: <Calculator className="w-5 h-5" /> },
    hr:          { from: "from-violet-400",    to: "to-violet-600",    ring: "ring-violet-400",    stroke: "#a78bfa", icon: <Users className="w-5 h-5" /> },
    email:       { from: "from-rose-400",      to: "to-rose-600",      ring: "ring-rose-400",      stroke: "#fb7185", icon: <Mail className="w-5 h-5" /> },
    crm:         { from: "from-amber-400",     to: "to-amber-600",     ring: "ring-amber-400",     stroke: "#fbbf24", icon: <Briefcase className="w-5 h-5" /> },
    banking:     { from: "from-sky-400",       to: "to-sky-600",       ring: "ring-sky-400",       stroke: "#38bdf8", icon: <Wallet className="w-5 h-5" /> },
    compliance:  { from: "from-cyan-400",      to: "to-cyan-600",      ring: "ring-cyan-400",      stroke: "#22d3ee", icon: <Scale className="w-5 h-5" /> },
    documents:   { from: "from-orange-400",    to: "to-orange-600",    ring: "ring-orange-400",    stroke: "#fb923c", icon: <FolderOpen className="w-5 h-5" /> },
    excel:       { from: "from-lime-400",      to: "to-lime-600",      ring: "ring-lime-400",      stroke: "#a3e635", icon: <BarChart3 className="w-5 h-5" /> },
    marketing:   { from: "from-fuchsia-400",   to: "to-fuchsia-600",   ring: "ring-fuchsia-400",   stroke: "#e879f9", icon: <Megaphone className="w-5 h-5" /> },
    recruitment: { from: "from-teal-400",      to: "to-teal-600",      ring: "ring-teal-400",      stroke: "#2dd4bf", icon: <UserPlus className="w-5 h-5" /> },
    custom:      { from: "from-slate-400",     to: "to-slate-600",     ring: "ring-slate-400",     stroke: "#94a3b8", icon: <User className="w-5 h-5" /> },
};

const FALLBACK: DomainStyle = DOMAIN.custom;

// ─── Componente: Nodo de empleado ────────────────────────────────────────────
function EmployeeNode({
    emp, x, y, isWorking, isHovered, onHover,
}: {
    emp: AIEmployee; x: number; y: number; isWorking: boolean;
    isHovered: boolean; onHover: (id: string | null) => void;
}) {
    const style = DOMAIN[emp.domain] ?? FALLBACK;
    return (
        <div
            className="absolute pointer-events-auto"
            style={{
                left: `calc(50% + ${x}px - 32px)`,
                top: `calc(50% + ${y}px - 32px)`,
                zIndex: isHovered ? 30 : 10,
            }}
            onMouseEnter={() => onHover(emp.id)}
            onMouseLeave={() => onHover(null)}
        >
            {/* Halo pulsante cuando working */}
            {isWorking && (
                <>
                    <span
                        className={`absolute inset-0 w-16 h-16 rounded-full bg-gradient-to-br ${style.from} ${style.to} opacity-40 blur-xl animate-pulse`}
                    />
                    <span
                        className={`absolute -inset-1 w-[72px] h-[72px] rounded-full ring-2 ${style.ring} opacity-70`}
                        style={{ animation: "ping 1.8s cubic-bezier(0,0,0.2,1) infinite" }}
                    />
                </>
            )}
            {/* Avatar circular */}
            <div
                className={`relative w-16 h-16 rounded-full bg-gradient-to-br ${style.from} ${style.to} flex items-center justify-center text-white shadow-2xl transition-transform hover:scale-110 cursor-pointer ${isWorking ? "ring-2 ring-white/40" : "opacity-90"}`}
            >
                {style.icon}
                {/* Status dot */}
                <span
                    className={`absolute -bottom-0.5 -right-0.5 w-3.5 h-3.5 rounded-full border-2 border-card ${
                        isWorking ? "bg-emerald-400 animate-pulse" : emp.status === "paused" ? "bg-amber-400" : emp.status === "blocked" ? "bg-red-500" : "bg-slate-500"
                    }`}
                />
            </div>
            {/* Tooltip al hover */}
            {isHovered && (
                <div className="absolute top-full left-1/2 -translate-x-1/2 mt-2 px-3 py-1.5 rounded-lg bg-card/95 backdrop-blur border border-border shadow-xl text-xs whitespace-nowrap z-40">
                    <div className="font-semibold text-foreground">{emp.name}</div>
                    <div className="text-muted-foreground text-[10px]">{emp.role}</div>
                    <div className={`text-[10px] mt-0.5 ${isWorking ? "text-emerald-400" : "text-muted-foreground"}`}>
                        {isWorking ? "● trabajando" : `○ ${emp.status}`}
                    </div>
                </div>
            )}
        </div>
    );
}

// ─── Componente principal ────────────────────────────────────────────────────
export function LiveTeamSection() {
    const { employees, recentActivity, recentResults, activeDomains, loading } = useLiveTeam();
    const [hoveredId, setHoveredId] = useState<string | null>(null);
    void recentActivity;

    // Filtra builtins primero, customs después (al final del círculo).
    const sortedEmps = useMemo(
        () => [...employees].sort((a, b) => Number(b.is_builtin) - Number(a.is_builtin) || a.name.localeCompare(b.name)),
        [employees],
    );

    // Posiciones circulares
    const RADIUS = 200;
    const nodes = useMemo(() => {
        const n = sortedEmps.length || 1;
        return sortedEmps.map((emp, i) => {
            const angle = (i / n) * 2 * Math.PI - Math.PI / 2; // empieza arriba
            return {
                emp,
                x: Math.cos(angle) * RADIUS,
                y: Math.sin(angle) * RADIUS,
                style: DOMAIN[emp.domain] ?? FALLBACK,
            };
        });
    }, [sortedEmps]);

    const workingCount = employees.filter(
        (e) => e.status === "working" || activeDomains.has(e.domain),
    ).length;
    const totalCount = employees.length;
    const hubActive = activeDomains.has("__hub__") || workingCount > 0;

    return (
        <section className="rounded-2xl border border-border bg-card/40 backdrop-blur p-6 relative overflow-hidden">
            <div className="flex items-center justify-between mb-2 relative z-20">
                <div>
                    <h2 className="text-lg font-semibold text-foreground flex items-center gap-2">
                        <Activity className={`w-5 h-5 ${workingCount > 0 ? "text-emerald-400 animate-pulse" : "text-primary"}`} /> Equipo IA en vivo
                    </h2>
                    <p className="text-xs text-muted-foreground mt-1">
                        {workingCount > 0
                            ? `${workingCount} de ${totalCount} agentes trabajando — actividad en tiempo real`
                            : `${totalCount} agentes en standby — listos para recibir tareas`}
                    </p>
                </div>
            </div>

            {/* Contenedor del mapa de nodos */}
            <div className="relative w-full h-[520px] mt-4">
                {loading ? (
                    <div className="absolute inset-0 flex items-center justify-center">
                        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
                    </div>
                ) : (
                    <>
                        {/* Grid futurista de fondo */}
                        <div
                            className="absolute inset-0 opacity-[0.06] pointer-events-none"
                            style={{
                                backgroundImage:
                                    "linear-gradient(rgba(255,255,255,1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,1) 1px, transparent 1px)",
                                backgroundSize: "40px 40px",
                            }}
                        />
                        {/* Glow radial */}
                        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                            <div className={`w-[400px] h-[400px] rounded-full blur-3xl transition-opacity duration-1000 ${workingCount > 0 ? "bg-emerald-500/15 opacity-100" : "bg-primary/10 opacity-60"}`} />
                        </div>

                        {/* Líneas SVG hub→nodo */}
                        <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ overflow: "visible" }}>
                            <defs>
                                {nodes.map(({ emp, style }) => (
                                    <linearGradient
                                        key={`grad-${emp.id}`}
                                        id={`grad-${emp.id}`}
                                        x1="0%" y1="0%" x2="100%" y2="0%"
                                    >
                                        <stop offset="0%" stopColor={style.stroke} stopOpacity="0.05" />
                                        <stop offset="50%" stopColor={style.stroke} stopOpacity="1" />
                                        <stop offset="100%" stopColor={style.stroke} stopOpacity="0.05" />
                                        <animate attributeName="x1" values="-100%;100%" dur="1.8s" repeatCount="indefinite" />
                                        <animate attributeName="x2" values="0%;200%" dur="1.8s" repeatCount="indefinite" />
                                    </linearGradient>
                                ))}
                            </defs>
                            <g transform="translate(50%, 50%)">
                                {nodes.map(({ emp, x, y, style }) => {
                                    const isWorking = emp.status === "working" || activeDomains.has(emp.domain);
                                    const isHover = hoveredId === emp.id;
                                    return (
                                        <g key={emp.id}>
                                            <line
                                                x1={0} y1={0}
                                                x2={x} y2={y}
                                                stroke={isWorking ? style.stroke : style.stroke}
                                                strokeOpacity={isWorking ? 0.4 : isHover ? 0.3 : 0.08}
                                                strokeWidth={isWorking ? 1.5 : 1}
                                                strokeDasharray={isWorking ? "4 6" : "2 6"}
                                                style={isWorking ? { animation: `dashflow 1.2s linear infinite` } : undefined}
                                            />
                                            {/* Partícula que viaja por la línea */}
                                            {isWorking && (
                                                <>
                                                    <circle r={4} fill={style.stroke}>
                                                        <animateMotion
                                                            dur="1.6s"
                                                            repeatCount="indefinite"
                                                            path={`M 0 0 L ${x} ${y}`}
                                                        />
                                                        <animate
                                                            attributeName="opacity"
                                                            values="0;1;1;0"
                                                            dur="1.6s"
                                                            repeatCount="indefinite"
                                                        />
                                                    </circle>
                                                    <circle r={8} fill={style.stroke} opacity="0.3">
                                                        <animateMotion
                                                            dur="1.6s"
                                                            repeatCount="indefinite"
                                                            path={`M 0 0 L ${x} ${y}`}
                                                        />
                                                    </circle>
                                                </>
                                            )}
                                        </g>
                                    );
                                })}
                            </g>
                        </svg>
                        <style jsx global>{`
                            @keyframes dashflow {
                                to { stroke-dashoffset: -20; }
                            }
                        `}</style>

                        {/* HUB central */}
                        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-20 pointer-events-none">
                            <div className="relative">
                                {/* Anillos concéntricos animados */}
                                <div className={`absolute -inset-8 rounded-full border border-primary/20 ${hubActive ? "animate-ping" : ""}`} style={{ animationDuration: "3s" }} />
                                <div className={`absolute -inset-4 rounded-full border border-primary/30 ${hubActive ? "animate-ping" : ""}`} style={{ animationDuration: "2s" }} />
                                {/* Cuerpo del hub */}
                                <div className="relative w-36 h-36 rounded-full bg-gradient-to-br from-primary/30 to-violet-600/30 backdrop-blur-xl border-2 border-primary/40 flex flex-col items-center justify-center shadow-2xl">
                                    <div className="text-5xl font-bold text-foreground leading-none">
                                        {workingCount}
                                    </div>
                                    <div className="text-[11px] text-muted-foreground uppercase tracking-widest mt-1">
                                        {workingCount === 1 ? "agente activo" : "agentes activos"}
                                    </div>
                                    <div className="text-[10px] text-muted-foreground/70 mt-2">
                                        de {totalCount} disponibles
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Nodos de empleados */}
                        {nodes.map(({ emp, x, y }) => (
                            <EmployeeNode
                                key={emp.id}
                                emp={emp}
                                x={x}
                                y={y}
                                isWorking={emp.status === "working" || activeDomains.has(emp.domain)}
                                isHovered={hoveredId === emp.id}
                                onHover={setHoveredId}
                            />
                        ))}
                    </>
                )}
            </div>

            {/* Feed compacto de últimas actividades */}
            {!loading && recentResults.length > 0 && (
                <div className="mt-2 pt-3 border-t border-border/50">
                    <div className="text-[10px] uppercase tracking-widest text-muted-foreground mb-2">Últimas acciones</div>
                    <div className="space-y-1 max-h-24 overflow-hidden">
                        {recentResults.slice(0, 4).map((r, i) => {
                            const style = DOMAIN[r.domain] ?? FALLBACK;
                            return (
                                <div
                                    key={`${r.taskId}-${i}`}
                                    className="flex items-center gap-2 text-xs text-muted-foreground animate-in slide-in-from-top-1 fade-in duration-500"
                                >
                                    <span className={`inline-block w-2 h-2 rounded-full ${r.success ? "bg-emerald-400" : "bg-rose-400"}`} style={{ boxShadow: `0 0 8px ${style.stroke}` }} />
                                    <span className="font-medium text-foreground/80 capitalize">{r.domain}</span>
                                    <span className="truncate flex-1">{r.summary || "—"}</span>
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}
        </section>
    );
}
