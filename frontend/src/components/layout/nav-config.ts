import {
    LayoutDashboard, ListChecks, ShieldCheck, ScrollText, Zap, Plug, Scale,
    Landmark, FileText, Users, Upload, Package, ChevronDown, ChevronRight,
    Home, Flag, ShoppingCart, Briefcase, Building2, Calendar,
    Users2, PieChart, Building, BookOpen, Bell, CheckCircle2, X, ScanLine,
    BarChart3, Sparkles, Settings, Layers, Download, Megaphone, Bot,
    Activity, Wand2, FileSearch,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

export type NavItem = {
    label: string;
    icon: LucideIcon;
    href?: string;
    subItems?: { label: string; href: string }[];
};

export type NavSection = {
    title?: string;
    items: NavItem[];
};

export const NAV_SECTIONS: NavSection[] = [
    {
        items: [
            { label: "Primeros pasos", icon: Flag, href: "/primeros-pasos" },
            { label: "Inicio", icon: Home, href: "/" },
            { label: "Tareas", icon: Sparkles, href: "/mi-equipo" },
            { label: "Bandeja", icon: Activity, href: "/bandeja" },
            { label: "Sandbox IA", icon: Wand2, href: "/sandbox" },
            { label: "Automatizaciones", icon: Zap, href: "/automatizaciones" },
        ],
    },
    {
        title: "Negocio",
        items: [
            { label: "Contactos", icon: Users2, href: "/clientes" },
            {
                label: "Ventas", icon: ShoppingCart, subItems: [
                    { label: "Facturas", href: "/ventas/facturas" },
                    { label: "Albaranes", href: "/albaranes" },
                    { label: "Presupuestos", href: "/ventas/presupuestos" },
                    { label: "Pedidos", href: "/ventas/pedidos" },
                    { label: "Recurrentes", href: "/ventas/recurrentes" },
                    { label: "Servicios", href: "/ventas/servicios" },
                ],
            },
            {
                label: "Compras", icon: Package, subItems: [
                    { label: "Facturas", href: "/compras/facturas" },
                    { label: "Pedidos", href: "/compras/pedidos" },
                    { label: "Proveedores", href: "/compras/proveedores" },
                ],
            },
            {
                label: "CRM", icon: Users, subItems: [
                    { label: "Embudo de ventas", href: "/crm/embudo-de-ventas" },
                    { label: "Actividades", href: "/crm/actividades" },
                    { label: "Calendario", href: "/crm/calendario" },
                    { label: "Reservas", href: "/crm/reservas" },
                    { label: "Reuniones", href: "/crm/reuniones" },
                ],
            },
            {
                label: "RRHH", icon: Briefcase, subItems: [
                    { label: "Empleados", href: "/rrhh/empleados" },
                    { label: "Nóminas", href: "/rrhh/nominas" },
                    { label: "Reclutamiento", href: "/rrhh/reclutamiento" },
                    { label: "Análisis de CV", href: "/rrhh/analisis-cv" },
                    { label: "Gestoría Documental", href: "/rrhh/documentos" },
                ],
            },
            {
                label: "Inventario", icon: Building2, subItems: [
                    { label: "Productos", href: "/catalogo" },
                    { label: "Stock", href: "/inventario/stock" },
                    { label: "Escáner almacén", href: "/inventario/scanner" },
                ],
            },
            {
                label: "Proyectos", icon: Calendar, subItems: [
                    { label: "Panel", href: "/proyectos" },
                    { label: "Tareas", href: "/proyectos/tareas" },
                    { label: "Mis tareas", href: "/proyectos/mis-tareas" },
                ],
            },
        ],
    },
    {
        title: "Finanzas",
        items: [
            {
                label: "Tesorería", icon: Landmark, subItems: [
                    { label: "Cuentas", href: "/banca" },
                    { label: "Cashflow", href: "/tesoreria/cashflow" },
                    { label: "Pagos y cobros", href: "/tesoreria/pagos-y-cobros" },
                    { label: "Remesas", href: "/tesoreria/remesas" },
                ],
            },
            {
                label: "Contabilidad", icon: BookOpen, subItems: [
                    { label: "Cuadro de cuentas", href: "/contabilidad/cuadro-de-cuentas" },
                    { label: "Libro diario", href: "/contabilidad/libro-diario" },
                    { label: "P&G", href: "/contabilidad/perdidas-y-ganancias" },
                    { label: "Balance", href: "/contabilidad/balance-de-situacion" },
                    { label: "Activos", href: "/contabilidad/activos" },
                    { label: "Asesorías", href: "/contabilidad/asesorias" },
                ],
            },
            { label: "Impuestos", icon: Scale, href: "/impuestos" },
            { label: "Compliance", icon: ShieldCheck, href: "/compliance" },
        ],
    },
    {
        title: "Análisis",
        items: [
            { label: "Analítica", icon: PieChart, href: "/analitica" },
            { label: "Informes IA", icon: BarChart3, href: "/informes" },
            { label: "Marketing", icon: Megaphone, href: "/marketing" },
            { label: "Auditoría", icon: ScrollText, href: "/auditoria" },
        ],
    },
    {
        title: "Herramientas",
        items: [
            { label: "Plantillas", icon: Layers, href: "/plantillas" },
            { label: "Escáner", icon: ScanLine, href: "/escaner" },
            { label: "Documentos", icon: FileText, href: "/documentos" },
            {
                label: "Integraciones", icon: Plug, subItems: [
                    { label: "Conexiones", href: "/integraciones" },
                    { label: "Mensajería", href: "/configuracion/integraciones" },
                ],
            },
            {
                label: "Configuración", icon: Settings, subItems: [
                    { label: "Empresa", href: "/configuracion/empresa" },
                    { label: "Perfil", href: "/configuracion/perfil" },
                    { label: "Claves API", href: "/configuracion/api-keys" },
                    { label: "Copias de seguridad", href: "/configuracion/backups" },
                    { label: "Actualizaciones", href: "/configuracion/actualizaciones" },
                ],
            },
        ],
    },
];

// Route label mapping for breadcrumbs - flattened from NAV_SECTIONS
export const ROUTE_LABELS: Record<string, string> = {};

// Build from NAV_SECTIONS
for (const section of NAV_SECTIONS) {
    for (const item of section.items) {
        if (item.href) {
            ROUTE_LABELS[item.href] = item.label;
        }
        if (item.subItems) {
            for (const sub of item.subItems) {
                ROUTE_LABELS[sub.href] = sub.label;
            }
        }
    }
}

// Additional manual labels for settings/config pages
Object.assign(ROUTE_LABELS, {
    "/configuracion/empresa": "Empresa",
    "/configuracion/actualizaciones": "Actualizaciones",
    "/configuracion/integraciones": "Mensajería",
    "/configuracion/perfil": "Perfil",
    "/configuracion/api-keys": "Claves API",
    "/configuracion/backups": "Copias de seguridad",
});
