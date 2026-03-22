"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import {
    LayoutDashboard, ListChecks, ShieldCheck, ScrollText, Zap, Plug, Scale,
    Landmark, FileText, Users, Upload, Package, ChevronDown, ChevronRight,
    Home, Flag, UserCircle, ShoppingCart, Briefcase, Building2, Calendar,
    Users2, PieChart, Building, BookOpen, Bell, CheckCircle2, X, ScanLine,
    BarChart3, Sparkles, Settings,
} from "lucide-react";
import ProfileMenu from "@/components/ProfileMenu";
import NotificationBell from "@/components/NotificationBell";
import ConfirmDialog from "@/components/ConfirmDialog";
import { useToastStore, type ToastType } from "@/stores/toast";
import { useNotificationStore } from "@/stores/notifications";
import { AlertCircle, AlertTriangle } from "lucide-react";

type NavItem = {
    label: string;
    icon: any;
    href?: string;
    subItems?: { label: string; href: string }[];
};

type NavSection = {
    title?: string;
    items: NavItem[];
};

const NAV_SECTIONS: NavSection[] = [
    {
        items: [
            { label: "Inicio", icon: Home, href: "/" },
            { label: "Tareas IA", icon: Sparkles, href: "/tareas" },
            { label: "Automatizaciones", icon: Zap, href: "/automatizaciones" },
            { label: "Aprobaciones", icon: UserCircle, href: "/aprobaciones" },
        ],
    },
    {
        title: "Negocio",
        items: [
            { label: "Contactos", icon: Users2, href: "/clientes" },
            {
                label: "Ventas", icon: ShoppingCart, subItems: [
                    { label: "Facturas", href: "/ventas/facturas" },
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
                ],
            },
            {
                label: "Inventario", icon: Building2, subItems: [
                    { label: "Productos", href: "/catalogo" },
                    { label: "Stock", href: "/inventario/stock" },
                ],
            },
            {
                label: "Proyectos", icon: Calendar, subItems: [
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
        ],
    },
    {
        title: "Análisis",
        items: [
            { label: "Analítica", icon: PieChart, href: "/analitica" },
            { label: "Informes IA", icon: BarChart3, href: "/informes" },
            { label: "Auditoría", icon: ScrollText, href: "/auditoria" },
        ],
    },
    {
        title: "Herramientas",
        items: [
            { label: "Escáner", icon: ScanLine, href: "/escaner" },
            { label: "Documentos", icon: FileText, href: "/documentos" },
            { label: "Integraciones", icon: Plug, href: "/integraciones" },
            { label: "Primeros pasos", icon: Flag, href: "/primeros-pasos" },
        ],
    },
];

function decodeJwtName(token: string): string {
    try {
        const payload = JSON.parse(atob(token.split(".")[1]));
        // sub es UUID — no usarlo como nombre
        return payload.full_name || payload.name || payload.email?.split("@")[0] || "";
    } catch {
        return "";
    }
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
    const pathname = usePathname();
    const router = useRouter();
    const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({});
    const [userName, setUserName] = useState("");
    const toasts = useToastStore((s) => s.toasts);
    const dismissToast = useToastStore((s) => s.dismiss);
    const showToast = useToastStore((s) => s.show);
    const pushNotification = useNotificationStore((s) => s.push);
    const triggerRefresh = useNotificationStore((s) => s.triggerRefresh);
    const lastCheckRef = useRef<number>(Date.now() / 1000);

    const toggleGroup = (label: string) => {
        setExpandedGroups(prev => ({ ...prev, [label]: !prev[label] }));
    };

    useEffect(() => {
        const token = localStorage.getItem("access_token");
        if (!token) { router.push("/login"); return; }

        // Nombre del usuario desde el JWT
        setUserName(decodeJwtName(token));

        // WebSocket para notificaciones en tiempo real
        const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const wsDomain = process.env.NEXT_PUBLIC_WS_URL || `${wsProtocol}//${window.location.hostname}:8080/ws`;
        const ws = new WebSocket(`${wsDomain}/notifications?token=${token}`);

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.type === "task_progress") {
                    const { step, total_steps, agent, summary, success } = data;
                    const agentLabel = agent ? `[${agent}]` : "";
                    const progressLabel = total_steps > 1 ? ` (${step}/${total_steps})` : "";
                    const msg = summary ? `${agentLabel}${progressLabel} ${summary}` : `${agentLabel}${progressLabel} Paso completado.`;
                    const toastType = success ? "info" : "warning";
                    showToast(msg, toastType);
                    pushNotification(msg, toastType as any);
                    // On final step, trigger page data refresh
                    if (step === total_steps) triggerRefresh();
                    return;
                }
                if (data.type === "event" && data.event) {
                    const eventMessages: Record<string, string> = {
                        invoice_created: `Factura ${data.context?.invoice_number || "generada"} creada`,
                        employee_created: `Empleado ${data.context?.employee_name || "nuevo"} registrado`,
                        document_uploaded: "Documento subido. Procesando...",
                        document_processed: `Documento ${data.context?.original_name || ""} procesado.`,
                        task_completed: "Tarea IA finalizada con éxito.",
                        approval_approved: `Aprobación procesada.${data.workflow_count ? ` ${data.workflow_count} automatizaciones disparadas.` : ""}`,
                    };
                    const msg = eventMessages[data.event] || `Nuevo evento: ${data.event.replace(/_/g, " ")}`;
                    showToast(msg, "info");
                    pushNotification(msg, "info");
                    triggerRefresh();
                }
            } catch { /* ignorar mensajes malformados */ }
        };

        return () => ws.close();
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [router]);

    // Auto-expandir la sección activa al montar
    useEffect(() => {
        const initial: Record<string, boolean> = {};
        for (const section of NAV_SECTIONS) {
            for (const item of section.items) {
                if (item.subItems?.some(sub => pathname.startsWith(sub.href))) {
                    initial[item.label] = true;
                }
            }
        }
        setExpandedGroups(initial);
    }, [pathname]);

    // Polling: toast cuando una automatización termina (cada 30s)
    useEffect(() => {
        const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
        if (!token) return;

        const poll = async () => {
            try {
                const since = lastCheckRef.current;
                lastCheckRef.current = Date.now() / 1000;
                const items = await api.workflows.recentCompletions(since);
                for (const item of items) {
                    const ok = item.status === "completed" || item.status === "success";
                    const msg = `Automatización "${item.workflow_name}" ${ok ? "completada" : "falló"}`;
                    const type = ok ? "success" : "error";
                    showToast(msg, type);
                    pushNotification(msg, type);
                }
                if (items.length > 0) triggerRefresh();
            } catch {
                // silencioso — no interrumpir la navegación por errores de polling
            }
        };

        const interval = setInterval(poll, 30_000);
        return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    return (
        <div className="flex h-screen bg-[#09090b] overflow-hidden">
            {/* ── Sidebar ─────────────────────────────────────────────── */}
            <aside className="w-56 flex flex-col border-r border-[#27272a] bg-[#111113] flex-shrink-0">
                {/* Logo */}
                <div className="flex items-center gap-2.5 px-4 py-4 border-b border-[#27272a]">
                    <div className="flex items-center justify-center w-7 h-7 rounded-lg bg-indigo-600 flex-shrink-0">
                        <Zap className="w-3.5 h-3.5 text-white" />
                    </div>
                    <span className="font-semibold text-white text-sm truncate">AutomatizaPyme</span>
                </div>

                {/* Nav */}
                <nav className="flex-1 px-2 py-3 overflow-y-auto overflow-x-hidden custom-scrollbar">
                    {NAV_SECTIONS.map((section, si) => (
                        <div key={si} className={si > 0 ? "mt-4" : ""}>
                            {section.title && (
                                <div className="px-2 mb-1">
                                    <span className="text-[10px] font-semibold uppercase tracking-widest text-zinc-600">
                                        {section.title}
                                    </span>
                                </div>
                            )}
                            <div className="space-y-0.5">
                                {section.items.map((item) => {
                                    const hasSub = !!item.subItems;
                                    const isExpanded = !!expandedGroups[item.label];
                                    const isChildActive = hasSub && item.subItems!.some(
                                        sub => pathname.startsWith(sub.href)
                                    );
                                    const isMainActive = !hasSub && (
                                        item.href === "/" ? pathname === "/" : pathname.startsWith(item.href!)
                                    );
                                    const isActive = isChildActive || isMainActive;

                                    return (
                                        <div key={item.label}>
                                            {hasSub ? (
                                                <button
                                                    onClick={() => toggleGroup(item.label)}
                                                    className={cn(
                                                        "w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors",
                                                        isActive && !isExpanded
                                                            ? "bg-indigo-600/10 text-indigo-400"
                                                            : "text-zinc-400 hover:text-white hover:bg-white/5"
                                                    )}
                                                >
                                                    <div className="flex items-center gap-2.5">
                                                        <item.icon className="w-3.5 h-3.5 flex-shrink-0" />
                                                        {item.label}
                                                    </div>
                                                    {isExpanded
                                                        ? <ChevronDown className="w-3 h-3 opacity-40" />
                                                        : <ChevronRight className="w-3 h-3 opacity-40" />
                                                    }
                                                </button>
                                            ) : (
                                                <Link
                                                    href={item.href!}
                                                    className={cn(
                                                        "flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors",
                                                        isActive
                                                            ? "bg-indigo-600/20 text-indigo-400"
                                                            : "text-zinc-400 hover:text-white hover:bg-white/5"
                                                    )}
                                                >
                                                    <item.icon className="w-3.5 h-3.5 flex-shrink-0" />
                                                    {item.label}
                                                </Link>
                                            )}

                                            {hasSub && isExpanded && (
                                                <div className="mt-0.5 mb-1 ml-3.5 pl-3 border-l border-[#27272a] space-y-0.5">
                                                    {item.subItems!.map((sub) => {
                                                        const subActive = pathname.startsWith(sub.href);
                                                        return (
                                                            <Link
                                                                key={sub.label}
                                                                href={sub.href}
                                                                className={cn(
                                                                    "block px-2.5 py-1 rounded-md text-xs transition-colors",
                                                                    subActive
                                                                        ? "bg-indigo-600/20 text-indigo-400 font-medium"
                                                                        : "text-zinc-500 hover:text-zinc-200 hover:bg-white/5"
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
                            </div>
                        </div>
                    ))}
                </nav>

                {/* Footer del sidebar */}
                <div className="px-2 py-3 border-t border-[#27272a]">
                    <Link
                        href="/configuracion/empresa"
                        className="flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg text-xs text-zinc-500 hover:text-zinc-300 hover:bg-white/5 transition-colors"
                    >
                        <Settings className="w-3.5 h-3.5" />
                        Configuración
                    </Link>
                </div>
            </aside>

            {/* ── Contenido principal ─────────────────────────────────── */}
            <div className="flex-1 flex flex-col overflow-hidden min-w-0">
                {/* Top header */}
                <header className="h-12 flex-shrink-0 flex items-center justify-between px-6 border-b border-[#27272a] bg-[#111113]" style={{ zIndex: 9999 }}>
                    {userName && (
                        <span className="text-xs text-zinc-500">
                            Hola, <span className="text-zinc-300 font-medium">{userName}</span>
                        </span>
                    )}
                    <div className="ml-auto flex items-center gap-1">
                        <NotificationBell />
                        <ProfileMenu />
                    </div>
                </header>
                <main className="flex-1 overflow-y-auto relative" style={{ zIndex: 1 }}>
                    {children}
                </main>
            </div>

            {/* Toast Stack */}
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

            <ConfirmDialog />
        </div>
    );
}
