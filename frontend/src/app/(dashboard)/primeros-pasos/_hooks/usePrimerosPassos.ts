"use client";

import { useState, useEffect } from "react";
import {
    Users2, FileText, Package, Bot, Zap, Building2,
    ShoppingCart, BarChart3, KeyRound
} from "lucide-react";
import { api } from "@/lib/api";

export interface Step {
    id: string;
    title: string;
    description: string;
    detail: string;
    icon: any;
    color: string;
    href?: string;
    hrefLabel?: string;
    tips: string[];
    prerequisite?: string;
}

export const STEPS: Step[] = [
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
        id: "api_keys",
        title: "Configura tu clave de IA",
        description: "Los agentes usan tu propia clave de IA (modelo BYOK). Sin clave, la IA no funciona.",
        detail: "Ve a Configuración → Claves API, elige un proveedor (Anthropic recomendado; también OpenAI o Groq), pega tu clave y actívala. Se guarda cifrada y puedes cambiarla cuando quieras.",
        icon: KeyRound,
        color: "violet",
        href: "/configuracion/api-keys",
        hrefLabel: "Ir a Claves API",
        tips: [
            "Crea la clave en la web del proveedor (p.ej. console.anthropic.com); pagas solo tu consumo.",
            "Claude Code solo funciona si tienes instalado el CLI de Claude (uso avanzado/dev).",
        ],
        prerequisite: "empresa",
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
        prerequisite: "api_keys",
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
            "Una automatización es diferente de una tarea: las tareas son puntuales ('hazme esto ahora'), las automatizaciones se ejecutan solas según reglas.",
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

export const COLOR_MAP: Record<string, { bg: string; border: string; text: string; ring: string; dot: string }> = {
    indigo: { bg: "bg-primary/10", border: "border-primary/20", text: "text-primary", ring: "ring-primary/30", dot: "bg-primary" },
    blue:   { bg: "bg-blue-500/10",   border: "border-blue-500/20",   text: "text-blue-400",   ring: "ring-blue-500/30",   dot: "bg-blue-500" },
    emerald:{ bg: "bg-emerald-500/10",border: "border-emerald-500/20",text: "text-emerald-400",ring: "ring-emerald-500/30",dot: "bg-emerald-500" },
    violet: { bg: "bg-violet-500/10", border: "border-violet-500/20", text: "text-violet-400", ring: "ring-violet-500/30", dot: "bg-violet-500" },
    amber:  { bg: "bg-amber-500/10",  border: "border-amber-500/20",  text: "text-amber-400",  ring: "ring-amber-500/30",  dot: "bg-amber-500" },
    rose:   { bg: "bg-rose-500/10",   border: "border-rose-500/20",   text: "text-rose-400",   ring: "ring-rose-500/30",   dot: "bg-rose-500" },
    orange: { bg: "bg-orange-500/10", border: "border-orange-500/20", text: "text-orange-400", ring: "ring-orange-500/30", dot: "bg-orange-500" },
    teal:   { bg: "bg-teal-500/10",   border: "border-teal-500/20",   text: "text-teal-400",   ring: "ring-teal-500/30",   dot: "bg-teal-500" },
};

export const IA_EXAMPLES = [
    "Factura a Acme Corp por 5 horas de consultoría a 80€/h",
    "¿Cuánto he facturado este mes?",
    "Crea una nómina borrador para todos los empleados activos",
    "Muéstrame las facturas vencidas y sin cobrar",
    "Dame el resumen de gastos del trimestre por categoría",
    "Registra el cobro de la factura F-2024-012",
];

export function usePrimerosPassos() {
    const [completed, setCompleted] = useState<Set<string>>(new Set());
    const [expanded, setExpanded] = useState<string | null>("empresa");
    const [iaExample, setIaExample] = useState(0);

    useEffect(() => {
        const saved = localStorage.getItem("onboarding_completed");
        const base = new Set<string>(saved ? JSON.parse(saved) : []);

        Promise.all([api.tenant.me(), api.tenant.getLlmConfig()])
            .then(([tenant, llm]) => {
                if (tenant.nif && tenant.name) base.add("empresa");
                else base.delete("empresa");
                // claude_code funciona con el CLI (sin key); en otro caso, el
                // proveedor activo debe tener clave. (Igual que el banner.)
                const active = llm.active_llm_provider;
                const configured =
                    active === "claude_code" || Boolean(llm.providers?.[active]?.has_key);
                if (configured) base.add("api_keys");
                else base.delete("api_keys");
                setCompleted(new Set(base));
            })
            .catch(() => setCompleted(new Set(base)));
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

    return { completed, expanded, iaExample, toggle, expand, completedCount, totalSteps, pct, isLocked };
}
