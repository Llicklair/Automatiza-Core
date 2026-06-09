"use client";

import Link from "next/link";
import {
    Flag, CheckCircle2, ChevronRight, ChevronDown,
    Users2, FileText, Package, Zap,
    ShoppingCart, BookOpen, BarChart3, ArrowRight, Sparkles,
    Play, Lock
} from "lucide-react";
import { usePrimerosPassos, STEPS, COLOR_MAP, IA_EXAMPLES } from "./_hooks/usePrimerosPassos";

export default function PrimerosPassPage() {
    const { completed, expanded, iaExample, toggle, expand, completedCount, totalSteps, pct, isLocked } = usePrimerosPassos();

    return (
        <div className="min-h-screen bg-background text-foreground p-8 max-w-4xl mx-auto">

            {/* Header */}
            <div className="mb-10">
                <div className="flex items-center gap-3 mb-4">
                    <div className="w-12 h-12 rounded-2xl bg-primary flex items-center justify-center shadow-lg shadow-primary/20">
                        <Flag className="w-6 h-6 text-foreground" />
                    </div>
                    <div>
                        <h1 className="text-3xl font-bold text-foreground tracking-tight">Primeros Pasos</h1>
                        <p className="text-muted-foreground text-sm mt-0.5">Tu guía para poner en marcha AutomatizaCore</p>
                    </div>
                </div>

                {/* Barra de progreso */}
                <div className="bg-card border border-border rounded-2xl p-5">
                    <div className="flex items-center justify-between mb-3">
                        <span className="text-sm font-medium text-foreground">
                            {completedCount === totalSteps
                                ? "¡Enhorabuena! Todo configurado 🎉"
                                : `${completedCount} de ${totalSteps} pasos completados`}
                        </span>
                        <span className="text-sm font-bold text-primary">{pct}%</span>
                    </div>
                    <div className="w-full bg-muted rounded-full h-2.5 overflow-hidden">
                        <div
                            className="h-full bg-gradient-to-r from-indigo-600 to-violet-500 rounded-full transition-all duration-700"
                            style={{ width: `${pct}%` }}
                        />
                    </div>
                    <div className="flex gap-1.5 mt-3">
                        {STEPS.map(s => (
                            <div
                                key={s.id}
                                className={`flex-1 h-1 rounded-full transition-all duration-500 ${completed.has(s.id) ? COLOR_MAP[s.color].dot : "bg-muted"}`}
                            />
                        ))}
                    </div>
                </div>
            </div>

            {/* IA Quick Demo */}
            <div className="mb-8 bg-gradient-to-br from-indigo-600/10 via-violet-600/5 to-transparent border border-primary/20 rounded-2xl p-5 relative overflow-hidden">
                <div className="absolute top-0 right-0 w-64 h-64 bg-primary/20 rounded-full blur-3xl pointer-events-none" />
                <div className="relative z-10">
                    <div className="flex items-center gap-2 mb-3">
                        <Sparkles className="w-4 h-4 text-primary" />
                        <span className="text-xs font-semibold text-primary uppercase tracking-wider">Asistente IA — puedes pedirle cosas como:</span>
                    </div>
                    <div className="font-mono text-sm text-foreground bg-muted/70 border border-border rounded-xl px-4 py-3 min-h-[44px] flex items-center transition-all duration-500">
                        <span className="text-primary mr-2">▸</span>
                        <span key={iaExample} className="animate-in fade-in duration-500">
                            &ldquo;{IA_EXAMPLES[iaExample]}&rdquo;
                        </span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-2">
                        El agente IA actúa en tiempo real — ejecuta, crea y consulta sin que tengas que tocar un formulario.
                    </p>
                </div>
            </div>

            {/* Qué puede hacer la IA */}
            <div className="mb-8 grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="bg-card border border-emerald-500/20 rounded-2xl p-5">
                    <h3 className="text-xs font-semibold text-emerald-400 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                        <CheckCircle2 className="w-3.5 h-3.5" /> La IA puede hacer
                    </h3>
                    <ul className="space-y-2">
                        {[
                            "Crear facturas, albaranes y presupuestos",
                            "Generar nóminas y calcular IRPF/SS",
                            "Responder preguntas sobre tus datos",
                            "Registrar cobros, pagos y asientos contables",
                            "Buscar clientes, productos y empleados",
                            "Ejecutar automatizaciones programadas",
                            "Generar informes y exportaciones Excel",
                        ].map(item => (
                            <li key={item} className="flex items-start gap-2 text-xs text-foreground">
                                <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 flex-shrink-0 mt-1.5" />
                                {item}
                            </li>
                        ))}
                    </ul>
                </div>
                <div className="bg-card border border-border rounded-2xl p-5">
                    <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3 flex items-center gap-1.5">
                        <Lock className="w-3.5 h-3.5" /> Requiere confirmación o datos previos
                    </h3>
                    <ul className="space-y-2">
                        {[
                            "Eliminar registros (siempre pide confirmación)",
                            "Enviar emails (necesita integración Gmail/Outlook)",
                            "Facturas: el cliente debe existir en Contactos",
                            "Nóminas: los empleados deben estar dados de alta",
                            "No accede a sistemas externos sin integración",
                            "No toma decisiones financieras por ti",
                            "No puede acceder a datos de otros tenants",
                        ].map(item => (
                            <li key={item} className="flex items-start gap-2 text-xs text-muted-foreground">
                                <div className="w-1.5 h-1.5 rounded-full bg-accent flex-shrink-0 mt-1.5" />
                                {item}
                            </li>
                        ))}
                    </ul>
                </div>
            </div>

            {/* Pasos */}
            <div className="space-y-3">
                {STEPS.map((step, idx) => {
                    const done = completed.has(step.id);
                    const locked = isLocked(step);
                    const open = expanded === step.id;
                    const c = COLOR_MAP[step.color];
                    const Icon = step.icon;

                    return (
                        <div
                            key={step.id}
                            className={`rounded-2xl border transition-all duration-300 overflow-hidden ${
                                locked
                                    ? "border-border bg-background opacity-60"
                                    : done
                                    ? `border-border bg-card`
                                    : open
                                    ? `border-[${c.border}] bg-card ring-1 ${c.ring}`
                                    : "border-border bg-card hover:border-border"
                            }`}
                        >
                            <button
                                onClick={() => !locked && expand(step.id)}
                                disabled={locked}
                                className="w-full flex items-center gap-4 p-5 text-left transition-colors"
                            >
                                <div className="flex-shrink-0">
                                    {done ? (
                                        <div className="w-8 h-8 rounded-full bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center">
                                            <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                                        </div>
                                    ) : locked ? (
                                        <div className="w-8 h-8 rounded-full bg-muted border border-border flex items-center justify-center">
                                            <Lock className="w-4 h-4 text-muted-foreground" />
                                        </div>
                                    ) : (
                                        <div className={`w-8 h-8 rounded-full ${c.bg} border ${c.border} flex items-center justify-center`}>
                                            <span className={`text-xs font-bold ${c.text}`}>{idx + 1}</span>
                                        </div>
                                    )}
                                </div>

                                <div className={`w-10 h-10 rounded-xl ${c.bg} border ${c.border} flex items-center justify-center flex-shrink-0`}>
                                    <Icon className={`w-5 h-5 ${c.text}`} />
                                </div>

                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2">
                                        <h3 className={`font-semibold text-sm ${done ? "line-through text-muted-foreground" : "text-foreground"}`}>
                                            {step.title}
                                        </h3>
                                        {done && <span className="text-[10px] text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-full font-medium">Hecho</span>}
                                        {locked && <span className="text-[10px] text-muted-foreground bg-muted border border-border px-2 py-0.5 rounded-full font-medium">Bloqueado</span>}
                                    </div>
                                    <p className="text-xs text-muted-foreground mt-0.5 truncate">{step.description}</p>
                                </div>

                                {!locked && (
                                    <div className="flex-shrink-0 text-muted-foreground">
                                        {open ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                                    </div>
                                )}
                            </button>

                            {open && !locked && (
                                <div className={`px-5 pb-5 border-t ${c.border} bg-muted/50`}>
                                    <div className="pt-4 space-y-4">
                                        <p className="text-sm text-foreground leading-relaxed">{step.detail}</p>

                                        <div className="space-y-2">
                                            {step.tips.map((tip, i) => (
                                                <div key={i} className="flex items-start gap-2.5">
                                                    <div className={`w-1.5 h-1.5 rounded-full ${c.dot} flex-shrink-0 mt-1.5`} />
                                                    <p className="text-xs text-muted-foreground">{tip}</p>
                                                </div>
                                            ))}
                                        </div>

                                        <div className="flex items-center gap-3 pt-2">
                                            {step.href && (
                                                <Link
                                                    href={step.href}
                                                    className={`inline-flex items-center gap-2 ${c.bg} ${c.border} border ${c.text} hover:opacity-80 px-4 py-2 rounded-xl text-sm font-medium transition-opacity`}
                                                >
                                                    <Play className="w-3.5 h-3.5" />
                                                    {step.hrefLabel}
                                                    <ArrowRight className="w-3.5 h-3.5" />
                                                </Link>
                                            )}
                                            <button
                                                onClick={() => toggle(step.id)}
                                                className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium border transition-all ${
                                                    done
                                                        ? "bg-muted border-border text-muted-foreground hover:bg-accent"
                                                        : "bg-emerald-500/10 border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/20"
                                                }`}
                                            >
                                                <CheckCircle2 className="w-3.5 h-3.5" />
                                                {done ? "Marcar como pendiente" : "Marcar como completado"}
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>

            {/* Footer */}
            <div className="mt-12 border-t border-border pt-8">
                <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-5 flex items-center gap-2">
                    <BookOpen className="w-4 h-4" /> Explora todos los módulos
                </h2>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    {[
                        { label: "Ventas", href: "/ventas/facturas", icon: FileText, color: "indigo" },
                        { label: "Compras", href: "/compras/facturas", icon: ShoppingCart, color: "rose" },
                        { label: "Contactos", href: "/clientes", icon: Users2, color: "blue" },
                        { label: "Catálogo", href: "/catalogo", icon: Package, color: "emerald" },
                        { label: "RRHH", href: "/rrhh/empleados", icon: Users2, color: "violet" },
                        { label: "Contabilidad", href: "/contabilidad/perdidas-y-ganancias", icon: BarChart3, color: "teal" },
                        { label: "Automatizaciones", href: "/automatizaciones", icon: Zap, color: "amber" },
                        { label: "Analítica", href: "/analitica", icon: BarChart3, color: "orange" },
                    ].map(m => {
                        const c = COLOR_MAP[m.color];
                        const MIcon = m.icon;
                        return (
                            <Link
                                key={m.href}
                                href={m.href}
                                className={`flex items-center gap-2.5 p-3 rounded-xl border ${c.border} ${c.bg} hover:opacity-80 transition-opacity group`}
                            >
                                <MIcon className={`w-4 h-4 ${c.text} flex-shrink-0`} />
                                <span className="text-sm text-foreground group-hover:text-foreground transition-colors">{m.label}</span>
                                <ChevronRight className="w-3.5 h-3.5 text-muted-foreground ml-auto group-hover:text-muted-foreground transition-colors" />
                            </Link>
                        );
                    })}
                </div>
            </div>
        </div>
    );
}
