"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
    Flag, CheckCircle2, Circle, ChevronRight, ChevronDown,
    Users2, FileText, Package, Bot, Zap, Building2,
    ShoppingCart, BookOpen, BarChart3, ArrowRight, Sparkles,
    Play, Lock
} from "lucide-react";

// ── Datos de los pasos ────────────────────────────────────────────────────────

interface Step {
    id: string;
    title: string;
    description: string;
    detail: string;
    icon: any;
    color: string;
    href?: string;
    hrefLabel?: string;
    tips: string[];
    prerequisite?: string; // id del paso requerido antes
}

const STEPS: Step[] = [
    {
        id: "empresa",
        title: "Configura tu empresa",
        description: "Añade el nombre, NIF y dirección fiscal. Estos datos aparecerán en todas tus facturas.",
        detail: "Ve a Configuración → Empresa y rellena los datos de tu negocio. Solo se hace una vez.",
        icon: Building2,
        color: "indigo",
        href: "/configuracion/empresa",
        hrefLabel: "Ir a Configuración",
        tips: [
            "El NIF/CIF es obligatorio para emitir facturas válidas en España.",
            "Puedes añadir tu logo más adelante desde el mismo panel.",
        ],
    },
    {
        id: "clientes",
        title: "Da de alta tus primeros clientes",
        description: "Crea el directorio de contactos: clientes, proveedores o leads. La IA los usará al generar facturas.",
        detail: "En Contactos puedes importarlos manualmente o dejar que la IA los detecte automáticamente al escanear facturas recibidas.",
        icon: Users2,
        color: "blue",
        href: "/clientes",
        hrefLabel: "Ir a Contactos",
        tips: [
            "El NIF del cliente se valida automáticamente al emitir una factura.",
            "Filtra por tipo: Cliente, Proveedor, Lead o Empresa.",
        ],
        prerequisite: "empresa",
    },
    {
        id: "catalogo",
        title: "Crea tu catálogo de productos y servicios",
        description: "Define los artículos o servicios que vendes con su precio e IVA. Así la IA puede rellenar facturas en segundos.",
        detail: "El catálogo centraliza precios y tipos de IVA. Cuando pides a la IA 'factura a Tech SL por 3 horas de consultoría', busca en el catálogo y completa la factura automáticamente.",
        icon: Package,
        color: "emerald",
        href: "/catalogo",
        hrefLabel: "Ir al Catálogo",
        tips: [
            "Asigna SKU/referencias si tienes artículos con código.",
            "El IVA por defecto es 21% — cámbialo a 0% para exportaciones.",
        ],
        prerequisite: "clientes",
    },
    {
        id: "factura",
        title: "Emite tu primera factura",
        description: "Crea una factura de venta real o pide a la IA que la genere por ti en lenguaje natural.",
        detail: "Puedes crear facturas manualmente desde Ventas → Facturas → Nueva Factura, o simplemente escribir en el chat de IA: 'Factura a [cliente] por [concepto]' y el agente la creará y te pedirá confirmación.",
        icon: FileText,
        color: "violet",
        href: "/ventas/facturas/nueva",
        hrefLabel: "Nueva Factura",
        tips: [
            "Las facturas en estado 'Borrador' no cuentan en la contabilidad hasta que las marcas como 'Pendiente'.",
            "Descarga el PDF directamente desde el listado de facturas.",
        ],
        prerequisite: "catalogo",
    },
    {
        id: "ia",
        title: "Habla con la IA",
        description: "El agente IA está disponible en todo momento. Escríbele en lenguaje natural y ejecutará acciones reales.",
        detail: "Pulsa el botón del asistente IA (esquina inferior derecha) o desde el panel de Tareas IA. Puedes pedirle cosas como: 'Muéstrame las facturas pendientes de cobro de este mes', 'Crea una nómina para María García' o 'Dame el resumen de ventas de febrero'.",
        icon: Bot,
        color: "amber",
        tips: [
            "La IA siempre te pide confirmación antes de ejecutar acciones irreversibles.",
            "Puedes hablar en español con acentos, abreviaturas o lenguaje informal.",
            "El historial de tareas está en el panel 'Tareas IA'.",
        ],
        prerequisite: "factura",
    },
    {
        id: "compras",
        title: "Registra tus gastos y facturas recibidas",
        description: "Escanea o sube facturas de proveedores. La IA extrae los datos y los categoriza automáticamente.",
        detail: "En Compras → Facturas puedes registrar facturas de proveedores manualmente, o usar el Escáner para subir un PDF o foto — la IA leerá el NIF, importe e IVA por ti.",
        icon: ShoppingCart,
        color: "rose",
        href: "/compras/facturas",
        hrefLabel: "Ir a Compras",
        tips: [
            "Los gastos registrados alimentan automáticamente la P&G en Contabilidad.",
            "Marca facturas como 'Pagada' para llevar el control de tesorería.",
        ],
        prerequisite: "ia",
    },
    {
        id: "automatizaciones",
        title: "Configura una automatización",
        description: "Define reglas que la IA ejecuta de forma autónoma: recordatorios de cobro, informes semanales, alertas de vencimiento…",
        detail: "Las automatizaciones son instrucciones en lenguaje natural que el sistema ejecuta de forma programada. Ejemplo: 'Cada lunes a las 9h envíame un resumen de facturas vencidas' o 'Si una factura lleva más de 30 días sin cobrar, notifícame'.",
        icon: Zap,
        color: "orange",
        href: "/automatizaciones",
        hrefLabel: "Ir a Automatizaciones",
        tips: [
            "Puedes pausar o eliminar cualquier automatización en cualquier momento.",
            "Las automatizaciones activas se muestran con un indicador verde en el panel.",
        ],
        prerequisite: "compras",
    },
    {
        id: "analítica",
        title: "Revisa tu analítica y P&G",
        description: "Con datos reales ya registrados, consulta la cuenta de resultados, el cuadro de cuentas y el dashboard de analítica.",
        detail: "El módulo de Contabilidad calcula Pérdidas & Ganancias directamente desde los asientos del libro diario (generados automáticamente por las facturas). La Analítica muestra tendencias de ingresos, gastos y los mejores clientes.",
        icon: BarChart3,
        color: "teal",
        href: "/analitica",
        hrefLabel: "Ir a Analítica",
        tips: [
            "La P&G se actualiza en tiempo real con cada nueva factura.",
            "El Cuadro de Cuentas sigue el Plan General Contable español (PGC).",
        ],
        prerequisite: "compras",
    },
];

const COLOR_MAP: Record<string, { bg: string; border: string; text: string; ring: string; dot: string }> = {
    indigo: { bg: "bg-indigo-500/10", border: "border-indigo-500/20", text: "text-indigo-400", ring: "ring-indigo-500/30", dot: "bg-indigo-500" },
    blue:   { bg: "bg-blue-500/10",   border: "border-blue-500/20",   text: "text-blue-400",   ring: "ring-blue-500/30",   dot: "bg-blue-500" },
    emerald:{ bg: "bg-emerald-500/10",border: "border-emerald-500/20",text: "text-emerald-400",ring: "ring-emerald-500/30",dot: "bg-emerald-500" },
    violet: { bg: "bg-violet-500/10", border: "border-violet-500/20", text: "text-violet-400", ring: "ring-violet-500/30", dot: "bg-violet-500" },
    amber:  { bg: "bg-amber-500/10",  border: "border-amber-500/20",  text: "text-amber-400",  ring: "ring-amber-500/30",  dot: "bg-amber-500" },
    rose:   { bg: "bg-rose-500/10",   border: "border-rose-500/20",   text: "text-rose-400",   ring: "ring-rose-500/30",   dot: "bg-rose-500" },
    orange: { bg: "bg-orange-500/10", border: "border-orange-500/20", text: "text-orange-400", ring: "ring-orange-500/30", dot: "bg-orange-500" },
    teal:   { bg: "bg-teal-500/10",   border: "border-teal-500/20",   text: "text-teal-400",   ring: "ring-teal-500/30",   dot: "bg-teal-500" },
};

// ── Comandos de ejemplo para la IA ────────────────────────────────────────────

const IA_EXAMPLES = [
    "Factura a Acme Corp por 5 horas de consultoría a 80€/h",
    "¿Cuánto he facturado este mes?",
    "Crea una nómina borrador para todos los empleados activos",
    "Muéstrame las facturas vencidas y sin cobrar",
    "Dame el resumen de gastos del trimestre por categoría",
    "Registra el cobro de la factura F-2024-012",
];

// ── Componente principal ───────────────────────────────────────────────────────

export default function PrimerosPassPage() {
    const [completed, setCompleted] = useState<Set<string>>(new Set());
    const [expanded, setExpanded] = useState<string | null>("empresa");
    const [iaExample, setIaExample] = useState(0);

    // Persiste el progreso en localStorage
    useEffect(() => {
        const saved = localStorage.getItem("onboarding_completed");
        if (saved) setCompleted(new Set(JSON.parse(saved)));
    }, []);

    const toggle = (id: string) => {
        setCompleted(prev => {
            const next = new Set(prev);
            if (next.has(id)) next.delete(id);
            else next.add(id);
            localStorage.setItem("onboarding_completed", JSON.stringify(Array.from(next)));
            return next;
        });
    };

    const expand = (id: string) => setExpanded(prev => prev === id ? null : id);

    // Rotate IA examples
    useEffect(() => {
        const t = setInterval(() => setIaExample(i => (i + 1) % IA_EXAMPLES.length), 3000);
        return () => clearInterval(t);
    }, []);

    const completedCount = completed.size;
    const totalSteps = STEPS.length;
    const pct = Math.round((completedCount / totalSteps) * 100);

    const isLocked = (step: Step) => {
        if (!step.prerequisite) return false;
        return !completed.has(step.prerequisite);
    };

    return (
        <div className="min-h-screen bg-[#09090b] text-white p-8 max-w-4xl mx-auto">

            {/* Header */}
            <div className="mb-10">
                <div className="flex items-center gap-3 mb-4">
                    <div className="w-12 h-12 rounded-2xl bg-indigo-600 flex items-center justify-center shadow-lg shadow-indigo-500/30">
                        <Flag className="w-6 h-6 text-white" />
                    </div>
                    <div>
                        <h1 className="text-3xl font-bold text-white tracking-tight">Primeros Pasos</h1>
                        <p className="text-zinc-400 text-sm mt-0.5">Tu guía para poner en marcha AutomatizaPyme</p>
                    </div>
                </div>

                {/* Barra de progreso */}
                <div className="bg-[#111113] border border-[#27272a] rounded-2xl p-5">
                    <div className="flex items-center justify-between mb-3">
                        <span className="text-sm font-medium text-zinc-300">
                            {completedCount === totalSteps
                                ? "¡Enhorabuena! Todo configurado 🎉"
                                : `${completedCount} de ${totalSteps} pasos completados`}
                        </span>
                        <span className="text-sm font-bold text-indigo-400">{pct}%</span>
                    </div>
                    <div className="w-full bg-zinc-800 rounded-full h-2.5 overflow-hidden">
                        <div
                            className="h-full bg-gradient-to-r from-indigo-600 to-violet-500 rounded-full transition-all duration-700"
                            style={{ width: `${pct}%` }}
                        />
                    </div>
                    <div className="flex gap-1.5 mt-3">
                        {STEPS.map(s => (
                            <div
                                key={s.id}
                                className={`flex-1 h-1 rounded-full transition-all duration-500 ${completed.has(s.id) ? COLOR_MAP[s.color].dot : "bg-zinc-800"}`}
                            />
                        ))}
                    </div>
                </div>
            </div>

            {/* IA Quick Demo */}
            <div className="mb-8 bg-gradient-to-br from-indigo-600/10 via-violet-600/5 to-transparent border border-indigo-500/20 rounded-2xl p-5 relative overflow-hidden">
                <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-600/5 rounded-full blur-3xl pointer-events-none" />
                <div className="relative z-10">
                    <div className="flex items-center gap-2 mb-3">
                        <Sparkles className="w-4 h-4 text-indigo-400" />
                        <span className="text-xs font-semibold text-indigo-400 uppercase tracking-wider">Asistente IA — puedes pedirle cosas como:</span>
                    </div>
                    <div className="font-mono text-sm text-white bg-black/30 border border-white/10 rounded-xl px-4 py-3 min-h-[44px] flex items-center transition-all duration-500">
                        <span className="text-indigo-300 mr-2">▸</span>
                        <span key={iaExample} className="animate-in fade-in duration-500">
                            &ldquo;{IA_EXAMPLES[iaExample]}&rdquo;
                        </span>
                    </div>
                    <p className="text-xs text-zinc-500 mt-2">
                        El agente IA actúa en tiempo real — ejecuta, crea y consulta sin que tengas que tocar un formulario.
                    </p>
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
                                    ? "border-zinc-800/50 bg-[#0d0d0f] opacity-60"
                                    : done
                                    ? `border-zinc-700 bg-[#111113]`
                                    : open
                                    ? `border-[${c.border}] bg-[#111113] ring-1 ${c.ring}`
                                    : "border-[#27272a] bg-[#111113] hover:border-zinc-600"
                            }`}
                        >
                            {/* Row */}
                            <button
                                onClick={() => !locked && expand(step.id)}
                                disabled={locked}
                                className="w-full flex items-center gap-4 p-5 text-left transition-colors"
                            >
                                {/* Step number / check */}
                                <div className="flex-shrink-0">
                                    {done ? (
                                        <div className="w-8 h-8 rounded-full bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center">
                                            <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                                        </div>
                                    ) : locked ? (
                                        <div className="w-8 h-8 rounded-full bg-zinc-800 border border-zinc-700 flex items-center justify-center">
                                            <Lock className="w-4 h-4 text-zinc-600" />
                                        </div>
                                    ) : (
                                        <div className={`w-8 h-8 rounded-full ${c.bg} border ${c.border} flex items-center justify-center`}>
                                            <span className={`text-xs font-bold ${c.text}`}>{idx + 1}</span>
                                        </div>
                                    )}
                                </div>

                                {/* Icon */}
                                <div className={`w-10 h-10 rounded-xl ${c.bg} border ${c.border} flex items-center justify-center flex-shrink-0`}>
                                    <Icon className={`w-5 h-5 ${c.text}`} />
                                </div>

                                {/* Text */}
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2">
                                        <h3 className={`font-semibold text-sm ${done ? "line-through text-zinc-500" : "text-white"}`}>
                                            {step.title}
                                        </h3>
                                        {done && <span className="text-[10px] text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-full font-medium">Hecho</span>}
                                        {locked && <span className="text-[10px] text-zinc-500 bg-zinc-800 border border-zinc-700 px-2 py-0.5 rounded-full font-medium">Bloqueado</span>}
                                    </div>
                                    <p className="text-xs text-zinc-500 mt-0.5 truncate">{step.description}</p>
                                </div>

                                {/* Chevron */}
                                {!locked && (
                                    <div className="flex-shrink-0 text-zinc-500">
                                        {open ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                                    </div>
                                )}
                            </button>

                            {/* Expanded detail */}
                            {open && !locked && (
                                <div className={`px-5 pb-5 border-t ${c.border} bg-black/20`}>
                                    <div className="pt-4 space-y-4">
                                        {/* Detail text */}
                                        <p className="text-sm text-zinc-300 leading-relaxed">{step.detail}</p>

                                        {/* Tips */}
                                        <div className="space-y-2">
                                            {step.tips.map((tip, i) => (
                                                <div key={i} className="flex items-start gap-2.5">
                                                    <div className={`w-1.5 h-1.5 rounded-full ${c.dot} flex-shrink-0 mt-1.5`} />
                                                    <p className="text-xs text-zinc-400">{tip}</p>
                                                </div>
                                            ))}
                                        </div>

                                        {/* Actions */}
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
                                                        ? "bg-zinc-800 border-zinc-700 text-zinc-400 hover:bg-zinc-700"
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

            {/* Footer — módulos del sistema */}
            <div className="mt-12 border-t border-[#27272a] pt-8">
                <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-5 flex items-center gap-2">
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
                                <span className="text-sm text-zinc-300 group-hover:text-white transition-colors">{m.label}</span>
                                <ChevronRight className="w-3.5 h-3.5 text-zinc-600 ml-auto group-hover:text-zinc-400 transition-colors" />
                            </Link>
                        );
                    })}
                </div>
            </div>
        </div>
    );
}
