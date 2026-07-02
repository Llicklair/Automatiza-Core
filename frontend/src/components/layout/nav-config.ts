import {
    LayoutDashboard, ListChecks, ShieldCheck, ScrollText, Zap, Plug, Scale,
    Landmark, FileText, Users, Upload, Package, ChevronDown, ChevronRight,
    Home, Flag, ShoppingCart, Briefcase, Building2, Calendar,
    Users2, PieChart, Building, BookOpen, Bell, CheckCircle2, X, ScanLine,
    BarChart3, Sparkles, Settings, Layers, Download, Megaphone, Bot,
    Activity, FileSearch, Clock, Timer, UserCircle, Receipt,
    Mail, AlertTriangle, FolderKanban, BadgeCheck,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

export type NavItem = {
    label: string;
    icon: LucideIcon;
    href?: string;
    adminOnly?: boolean;
    requiredPlan?: "pro" | "gestoria";
    /** Marca el item como núcleo de la app — se renderiza con un color destacado en el sidebar. */
    highlight?: boolean;
    subItems?: { label: string; href: string; adminOnly?: boolean; requiredPlan?: "pro" | "gestoria" }[];
};

export type NavSection = {
    title?: string;
    items: NavItem[];
};

export const NAV_SECTIONS: NavSection[] = [
    {
        items: [
            { label: "Inicio", icon: Home, href: "/" },
            { label: "Primeros pasos", icon: Flag, href: "/primeros-pasos" },
            { label: "Mi portal", icon: UserCircle, href: "/portal" },
            { label: "Mi equipo", icon: Sparkles, href: "/mi-equipo", highlight: true },
            { label: "Automatizaciones", icon: Zap, href: "/automatizaciones", highlight: true },
            { label: "Calendario", icon: Calendar, href: "/calendario" },
            { label: "Bandeja", icon: Activity, href: "/bandeja" },
        ],
    },
    {
        title: "Negocio",
        items: [
            {
                label: "Contactos", icon: Users2, subItems: [
                    { label: "Clientes", href: "/clientes" },
                    { label: "Portal clientes", href: "/clientes/portal", adminOnly: true, requiredPlan: "gestoria" },
                ],
            },
            {
                label: "Ventas", icon: ShoppingCart, subItems: [
                    { label: "Resumen", href: "/ventas" },
                    { label: "Facturas", href: "/ventas/facturas" },
                    { label: "Albaranes", href: "/albaranes" },
                    { label: "Presupuestos", href: "/ventas/presupuestos" },
                    { label: "Pedidos", href: "/ventas/pedidos" },
                    { label: "Recurrentes", href: "/ventas/recurrentes" },
                    { label: "Servicios", href: "/ventas/servicios" },
                    { label: "Facturación electrónica", href: "/ventas/facturacion-electronica" },
                ],
            },
            {
                label: "Compras", icon: Package, subItems: [
                    { label: "Resumen", href: "/compras" },
                    { label: "Facturas", href: "/compras/facturas" },
                    { label: "Pedidos", href: "/compras/pedidos" },
                    { label: "Proveedores", href: "/compras/proveedores" },
                ],
            },
            {
                label: "CRM", icon: Users, requiredPlan: "pro", subItems: [
                    { label: "Resumen", href: "/crm" },
                    { label: "Embudo de ventas", href: "/crm/embudo-de-ventas" },
                    { label: "Actividades", href: "/crm/actividades" },
                    { label: "Calendario CRM", href: "/crm/calendario" },
                    { label: "Reservas", href: "/crm/reservas" },
                    { label: "Reuniones", href: "/crm/reuniones" },
                ],
            },
            {
                label: "RRHH", icon: Briefcase, requiredPlan: "pro", subItems: [
                    { label: "Resumen", href: "/rrhh" },
                    { label: "Empleados", href: "/rrhh/empleados" },
                    { label: "Nóminas", href: "/rrhh/nominas" },
                    { label: "Reclutamiento", href: "/rrhh/reclutamiento" },
                    { label: "Gestoría Documental", href: "/rrhh/documentos" },
                    { label: "Jornada y ausencias", href: "/rrhh/jornada" },
                    { label: "Gastos", href: "/rrhh/gastos" },
                ],
            },
            {
                label: "Inventario", icon: Building2, subItems: [
                    { label: "Resumen", href: "/inventario" },
                    { label: "Productos", href: "/catalogo" },
                    { label: "Stock", href: "/inventario/stock" },
                    { label: "TPV", href: "/tpv" },
                    { label: "Escáner almacén", href: "/inventario/scanner" },
                ],
            },
            {
                label: "Proyectos", icon: FolderKanban, subItems: [
                    { label: "Panel", href: "/proyectos" },
                    { label: "Tareas", href: "/proyectos/tareas" },
                ],
            },
        ],
    },
    {
        title: "Finanzas",
        items: [
            {
                label: "Tesorería", icon: Landmark, requiredPlan: "pro", subItems: [
                    { label: "Resumen", href: "/tesoreria" },
                    { label: "Cuentas", href: "/banca" },
                    { label: "Cashflow", href: "/tesoreria/cashflow" },
                    { label: "Pagos y cobros", href: "/tesoreria/pagos-y-cobros" },
                    { label: "Remesas", href: "/tesoreria/remesas" },
                ],
            },
            {
                label: "Contabilidad", icon: BookOpen, requiredPlan: "pro", subItems: [
                    { label: "Resumen", href: "/contabilidad" },
                    { label: "Cuadro de cuentas", href: "/contabilidad/cuadro-de-cuentas" },
                    { label: "Libro diario", href: "/contabilidad/libro-diario" },
                    { label: "P&G", href: "/contabilidad/perdidas-y-ganancias" },
                    { label: "Balance", href: "/contabilidad/balance-de-situacion" },
                    { label: "Activos", href: "/contabilidad/activos" },
                    { label: "Asesorías", href: "/contabilidad/asesorias" },
                ],
            },
            { label: "Impuestos", icon: Scale, href: "/impuestos", requiredPlan: "pro" },
        ],
    },
    {
        title: "Verifactu",
        items: [
            { label: "Configuración fiscal (AEAT)", icon: BadgeCheck, href: "/configuracion/verifactu", adminOnly: true, requiredPlan: "pro" },
        ],
    },
    {
        title: "Análisis",
        items: [
            { label: "Analítica", icon: PieChart, href: "/analitica", requiredPlan: "pro" },
            { label: "Informes IA", icon: BarChart3, href: "/informes", requiredPlan: "pro" },
            { label: "Email Marketing", icon: Mail, href: "/email-marketing", requiredPlan: "pro" },
            { label: "Marketing", icon: Megaphone, href: "/marketing", requiredPlan: "gestoria" },
            { label: "Alertas", icon: AlertTriangle, href: "/alertas", requiredPlan: "pro" },
        ],
    },
    {
        title: "Gobierno",
        items: [
            { label: "Compliance", icon: ShieldCheck, href: "/compliance", adminOnly: true, requiredPlan: "gestoria" },
            { label: "Auditoría", icon: ScrollText, href: "/auditoria", adminOnly: true, requiredPlan: "gestoria" },
        ],
    },
    {
        title: "Herramientas",
        items: [
            { label: "Plantillas", icon: Layers, href: "/plantillas", requiredPlan: "pro" },
            { label: "Escáner e importación", icon: ScanLine, href: "/escaner", requiredPlan: "pro" },
            { label: "Documentos", icon: FileText, href: "/documentos", requiredPlan: "pro" },
            { label: "Correos", icon: Mail, href: "/correos", requiredPlan: "pro" },
            { label: "Integraciones", icon: Plug, href: "/integraciones", requiredPlan: "pro" },
            {
                label: "Configuración", icon: Settings, subItems: [
                    { label: "Resumen", href: "/configuracion" },
                    { label: "Empresa", href: "/configuracion/empresa" },
                    { label: "Perfil", href: "/configuracion/perfil" },
                    { label: "Preferencias", href: "/configuracion/preferencias" },
                    { label: "Idioma", href: "/configuracion/idioma" },
                    { label: "Usuarios", href: "/configuracion/usuarios", adminOnly: true },
                    { label: "Mensajería", href: "/configuracion/integraciones" },
                    { label: "Claves API", href: "/configuracion/api-keys", adminOnly: true },
                    { label: "Copias de seguridad", href: "/configuracion/backups", adminOnly: true },
                    { label: "Autonomía de agentes", href: "/configuracion/autonomia", adminOnly: true },
                    { label: "Mantenimiento", href: "/configuracion/mantenimiento", adminOnly: true },
                    { label: "Actualizaciones", href: "/configuracion/actualizaciones", adminOnly: true },
                ],
            },
        ],
    },
];

// Route label mapping for breadcrumbs - flattened from NAV_SECTIONS
export const ROUTE_LABELS: Record<string, string> = {};

for (const section of NAV_SECTIONS) {
    for (const item of section.items) {
        if (item.href) ROUTE_LABELS[item.href] = item.label;
        if (item.subItems) {
            for (const sub of item.subItems) ROUTE_LABELS[sub.href] = sub.label;
        }
    }
}

Object.assign(ROUTE_LABELS, {
    "/configuracion/empresa": "Empresa",
    "/configuracion/actualizaciones": "Actualizaciones",
    "/configuracion/integraciones": "Mensajería",
    "/configuracion/perfil": "Perfil",
    "/configuracion/api-keys": "Claves API",
    "/configuracion/backups": "Copias de seguridad",
    "/configuracion/usuarios": "Usuarios",
    "/configuracion/preferencias": "Preferencias",
    "/configuracion/idioma": "Idioma",
    "/configuracion/regap": "Apoderamiento AEAT",
    "/configuracion/verifactu": "Modo Verifactu",
    "/configuracion/autonomia": "Autonomía de agentes",
    "/configuracion/firma-digital": "Firma digital",
    "/configuracion/mantenimiento": "Mantenimiento",
    "/bienvenida": "Bienvenida",
    "/bienvenida/simulacion-303": "Simulación Modelo 303",
    "/impuestos/asistida": "Presentación asistida (131 / 200)",
    "/impuestos/modelos": "Modelos AEAT (preview)",
});
