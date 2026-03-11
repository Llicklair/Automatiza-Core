"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import {
    LayoutDashboard,
    ListChecks,
    ShieldCheck,
    ScrollText,
    Zap,
    Plug,
    Scale,
    Landmark,
    FileText,
    Users,
    Upload,
    Package,
    ChevronDown,
    ChevronRight,
    Home,
    Flag,
    UserCircle,
    ShoppingCart,
    Briefcase,
    Building2,
    Calendar,
    Users2,
    PieChart,
    Building,
    BookOpen,
    Bell, CheckCircle2, X, ScanLine, BarChart3
} from "lucide-react";
import ProfileMenu from "@/components/ProfileMenu";
import { useToastStore, type ToastType } from "@/stores/toast";
import { AlertCircle, AlertTriangle } from "lucide-react";

type NavItem = {
    label: string;
    icon: any;
    href?: string;
    subItems?: { label: string; href: string }[];
};

const NAV_ITEMS: NavItem[] = [
    { label: "Primeros pasos", icon: Flag, href: "/primeros-pasos" },
    { label: "Inicio", icon: Home, href: "/" },
    { label: "Aprobaciones", icon: UserCircle, href: "/aprobaciones" },
    { label: "Tareas IA", icon: ListChecks, href: "/tareas" },
    { label: "Automatizaciones", icon: Zap, href: "/automatizaciones" },
    { label: "Contactos", icon: Users2, href: "/clientes" },
    {
        label: "Ventas", icon: ShoppingCart, subItems: [
            { label: "Pedidos", href: "/ventas/pedidos" },
            { label: "Facturas", href: "/ventas/facturas" },
            { label: "Recurrentes", href: "/ventas/recurrentes" },
            { label: "Presupuestos", href: "/ventas/presupuestos" },
            { label: "Servicios", href: "/ventas/servicios" },
        ]
    },
    {
        label: "Compras", icon: Package, subItems: [
            { label: "Pedidos", href: "/compras/pedidos" },
            { label: "Facturas", href: "/compras/facturas" },
            { label: "Proveedores", href: "/compras/proveedores" },
        ]
    },
    {
        label: "CRM", icon: Users, subItems: [
            { label: "Embudo de ventas", href: "/crm/embudo-de-ventas" },
            { label: "Actividades", href: "/crm/actividades" },
            { label: "Calendario", href: "/crm/calendario" },
            { label: "Reservas", href: "/crm/reservas" },
            { label: "Reuniones", href: "/crm/reuniones" },
        ]
    },
    {
        label: "RRHH", icon: Briefcase, subItems: [
            { label: "Empleados", href: "/rrhh/empleados" },
            { label: "Nóminas", href: "/rrhh/nominas" },
        ]
    },
    {
        label: "Inventario", icon: Building2, subItems: [
            { label: "Productos", href: "/catalogo" },
            { label: "Stock", href: "/inventario/stock" },
        ]
    },
    {
        label: "Proyectos", icon: Calendar, subItems: [
            { label: "Panel Principal", href: "/proyectos" },
            { label: "Tablero Tareas", href: "/proyectos/tareas" },
        ]
    },
    {
        label: "Tesorería", icon: Landmark, subItems: [
            { label: "Cuentas", href: "/banca" },
            { label: "Cashflow", href: "/tesoreria/cashflow" },
            { label: "Pagos y cobros", href: "/tesoreria/pagos-y-cobros" },
            { label: "Remesas", href: "/tesoreria/remesas" },
        ]
    },
    {
        label: "Contabilidad", icon: BookOpen, subItems: [
            { label: "Cuadro de cuentas", href: "/contabilidad/cuadro-de-cuentas" },
            { label: "Libro diario", href: "/contabilidad/libro-diario" },
            { label: "Activos", href: "/contabilidad/activos" },
            { label: "Pérdidas y Ganancias", href: "/contabilidad/perdidas-y-ganancias" },
            { label: "Balance de situación", href: "/contabilidad/balance-de-situacion" },
            { label: "Asesorías", href: "/contabilidad/asesorias" },
        ]
    },
    { label: "Impuestos", icon: Scale, href: "/impuestos" },
    { label: "Analítica", icon: PieChart, href: "/analitica" },
    { label: "Informes IA", icon: BarChart3, href: "/informes" },
    { label: "Escáner", icon: ScanLine, href: "/escaner" },
    { label: "Documentos", icon: FileText, href: "/documentos" },
    { label: "Integraciones", icon: Plug, href: "/integraciones" },
    { label: "Auditoría", icon: ScrollText, href: "/auditoria" },
];

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const pathname = usePathname();
    const router = useRouter();
    const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({});
    const [notification, setNotification] = useState<{ msg: string; type: "info" | "ok" } | null>(null);
    const toasts = useToastStore((s) => s.toasts);
    const dismissToast = useToastStore((s) => s.dismiss);
    const showToast = useToastStore((s) => s.show);

    const toggleGroup = (label: string) => {
        setExpandedGroups(prev => ({
            ...prev,
            [label]: !prev[label]
        }));
    };

    useEffect(() => {
        const token = localStorage.getItem("access_token");
        if (!token) {
            router.push("/login");
            return;
        }

        // Conectar a WebSockets para notificaciones en tiempo real
        const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const wsUrl = `ws://127.0.0.1:8080/ws/notifications?token=${token}`;
        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log("WebSocket conectado globalmente");
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.type === "event" && data.event) {
                    let msg = "";
                    switch (data.event) {
                        case "invoice_created":
                            msg = `Factura ${data.context?.invoice_number || 'generada'} creada`;
                            break;
                        case "employee_created":
                            msg = `Empleado ${data.context?.employee_name || 'nuevo'} registrado`;
                            break;
                        case "document_uploaded":
                            msg = `Documento subido. Procesando...`;
                            break;
                        case "document_processed":
                            msg = `Documento ${data.context?.original_name || ''} procesado.`;
                            break;
                        case "task_completed":
                            msg = `Una tarea IA ha finalizado con éxito.`;
                            break;
                        case "approval_approved":
                            msg = `Aprobación procesada correctamente.`;
                            if (data.workflow_count) msg += ` Disparados ${data.workflow_count} workflows.`;
                            break;
                        default:
                            msg = `Nuevo evento: ${data.event.replace(/_/g, " ")}`;
                            if (data.workflow_count) msg += ` (${data.workflow_count} automatizaciones)`;
                    }

                    showToast(msg, "info");
                }
            } catch (e) {
                console.error("Error parseando mensaje WS", e);
            }
        };

        ws.onclose = () => {
            console.log("WebSocket desconectado");
        }

        return () => {
            ws.close();
        };

    }, [router]);


    return (
        <div className="flex h-screen bg-[#09090b] overflow-hidden">
            {/* ── Sidebar ───────────────────────────────────────────────── */}
            <aside className="w-60 flex flex-col border-r border-[#27272a] bg-[#111113]">
                {/* Logo */}
                <div className="flex items-center gap-3 px-5 py-5 border-b border-[#27272a]">
                    <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-indigo-600">
                        <Zap className="w-4 h-4 text-white" />
                    </div>
                    <span className="font-semibold text-white text-sm">AutomatizaPyme</span>
                </div>

                {/* Nav */}
                <nav className="flex-1 px-3 py-4 overflow-y-auto overflow-x-hidden space-y-0.5 custom-scrollbar">
                    {NAV_ITEMS.map((item) => {
                        const hasSub = !!item.subItems;
                        const isExpanded = !!expandedGroups[item.label];

                        // Check if any subitem is active
                        const isChildActive = hasSub && item.subItems!.some(
                            sub => sub.href !== "#" && pathname.startsWith(sub.href)
                        );
                        // Check if main item is active (if no subitems)
                        const isMainActive = !hasSub && item.href !== "#" && (
                            item.href === "/" ? pathname === "/" : pathname.startsWith(item.href!)
                        );

                        const isActive = isChildActive || isMainActive;

                        return (
                            <div key={item.label}>
                                {hasSub ? (
                                    <button
                                        onClick={() => toggleGroup(item.label)}
                                        className={cn(
                                            "w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                                            isActive && !isExpanded
                                                ? "bg-indigo-600/10 text-indigo-400"
                                                : "text-zinc-400 hover:text-white hover:bg-white/5"
                                        )}
                                    >
                                        <div className="flex items-center gap-3">
                                            <item.icon className="w-4 h-4 flex-shrink-0" />
                                            {item.label}
                                        </div>
                                        {isExpanded ? (
                                            <ChevronDown className="w-3 h-3 opacity-50" />
                                        ) : (
                                            <ChevronRight className="w-3 h-3 opacity-50" />
                                        )}
                                    </button>
                                ) : (
                                    <Link
                                        href={item.href!}
                                        className={cn(
                                            "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                                            isActive
                                                ? "bg-indigo-600/20 text-indigo-400"
                                                : "text-zinc-400 hover:text-white hover:bg-white/5"
                                        )}
                                    >
                                        <item.icon className="w-4 h-4 flex-shrink-0" />
                                        {item.label}
                                    </Link>
                                )}

                                {/* Subitems */}
                                {hasSub && isExpanded && (
                                    <div className="mt-1 mb-2 ml-4 pl-4 border-l border-[#27272a] space-y-0.5">
                                        {item.subItems!.map((sub) => {
                                            const subActive = sub.href !== "#" && (
                                                sub.href === "/" ? pathname === "/" : pathname.startsWith(sub.href)
                                            );
                                            return (
                                                <Link
                                                    key={sub.label}
                                                    href={sub.href}
                                                    className={cn(
                                                        "block px-3 py-1.5 rounded-lg text-xs font-medium transition-colors line-clamp-1",
                                                        subActive
                                                            ? "bg-indigo-600/20 text-indigo-400"
                                                            : "text-zinc-500 hover:text-zinc-300 hover:bg-white/5"
                                                    )}
                                                >
                                                    {sub.label}
                                                </Link>
                                            );
                                        })}
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </nav>

                {/* Spacer inferior */}
                <div className="pb-4" />
            </aside>

            {/* ── Contenido principal ───────────────────────────────────── */}
            <div className="flex-1 flex flex-col overflow-hidden">
                {/* Top header */}
                <header className="h-12 flex-shrink-0 flex items-center justify-end px-6 border-b border-[#27272a] bg-[#111113]/60 backdrop-blur-sm">
                    <ProfileMenu />
                </header>
                <main className="flex-1 overflow-y-auto">
                    {children}
                </main>
            </div>

            {/* Global Toast Stack */}
            <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-2 items-end">
                {toasts.map((t) => {
                    const styles: Record<ToastType, string> = {
                        success: "bg-emerald-500/10 border-emerald-500/30 text-emerald-300",
                        error:   "bg-red-500/10 border-red-500/30 text-red-300",
                        warning: "bg-amber-500/10 border-amber-500/30 text-amber-300",
                        info:    "bg-indigo-500/10 border-indigo-500/30 text-indigo-300",
                    };
                    const icons: Record<ToastType, React.ReactNode> = {
                        success: <CheckCircle2 className="w-4 h-4 flex-shrink-0" />,
                        error:   <AlertCircle className="w-4 h-4 flex-shrink-0" />,
                        warning: <AlertTriangle className="w-4 h-4 flex-shrink-0" />,
                        info:    <Bell className="w-4 h-4 flex-shrink-0" />,
                    };
                    return (
                        <div
                            key={t.id}
                            className={`flex items-center gap-3 px-4 py-3 rounded-xl shadow-2xl text-sm font-medium border max-w-sm animate-in slide-in-from-bottom-3 duration-200 ${styles[t.type]}`}
                        >
                            {icons[t.type]}
                            <span className="flex-1">{t.message}</span>
                            <button onClick={() => dismissToast(t.id)} className="opacity-50 hover:opacity-100 ml-1">
                                <X className="w-3.5 h-3.5" />
                            </button>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
