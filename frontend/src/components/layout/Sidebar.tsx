"use client";

import React from "react";
import Link from "next/link";
import { Settings, ChevronDown, ChevronRight, PanelLeftClose, PanelLeft } from "lucide-react";
import { cn } from "@/lib/utils";
import { ScrollArea } from "@/components/ui/scroll-area";
import { NAV_SECTIONS, type NavItem, type NavSection } from "./nav-config";
import { useSidebar } from "./_hooks/useSidebar";
import { useUserRole } from "@/hooks/useUserRole";

export function Sidebar() {
    const {
        collapsed,
        expandedItems,
        toggleCollapsed,
        toggleExpanded,
        handleNavClick,
        isActive,
        isParentActive,
    } = useSidebar();

    const role = useUserRole();
    const isAdmin = role === "admin";
    const isEmployee = role === "employee";

    // Para rol "employee": solo se ve Inicio, Mi portal y Configuración > Perfil.
    const EMPLOYEE_ALLOWED_HREFS = new Set<string>([
        "/",
        "/portal",
        "/configuracion",
        "/configuracion/perfil",
    ]);

    const filterItem = (item: NavItem): NavItem | null => {
        if (item.adminOnly && !isAdmin) return null;
        if (isEmployee) {
            const allowedSubs = item.subItems?.filter(s => EMPLOYEE_ALLOWED_HREFS.has(s.href));
            if (allowedSubs && allowedSubs.length > 0) {
                return { ...item, subItems: allowedSubs };
            }
            if (item.href && EMPLOYEE_ALLOWED_HREFS.has(item.href)) {
                return { ...item, subItems: undefined };
            }
            return null;
        }
        if (item.subItems) {
            const visibleSubs = item.subItems.filter(s => !s.adminOnly || isAdmin);
            if (visibleSubs.length === 0) return null;
            return { ...item, subItems: visibleSubs };
        }
        return item;
    };

    const renderNavItem = (item: NavItem) => {
        const Icon = item.icon;
        const active = isParentActive(item);
        const expanded = expandedItems.has(item.label);
        const hasSubItems = !!item.subItems && item.subItems.length > 0;

        const highlight = !!item.highlight;
        // Container: hover/activo sutil cuando highlight, sin pisar el color del texto
        const containerStyle = highlight
            ? cn(
                "hover:bg-primary/5 transition-all",
                active && "bg-primary/10"
            )
            : (active
                ? "bg-primary/15 text-primary"
                : "text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-foreground");
        // Icono: color primary + halo sutil con drop-shadow del propio color
        const iconClass = highlight
            ? "h-4 w-4 flex-shrink-0 text-primary drop-shadow-[0_0_4px_currentColor]"
            : "h-4 w-4 flex-shrink-0";
        // Label: foreground en negrita (contraste con icono primary)
        const labelClass = highlight
            ? "truncate text-foreground font-semibold tracking-tight"
            : "truncate";

        // Collapsed mode
        if (collapsed) {
            const href = item.href || (item.subItems?.[0]?.href ?? "#");
            return (
                <div key={item.label}>
                    <Link
                        href={href}
                        onClick={(e) => handleNavClick(e, href)}
                        title={item.label}
                        aria-label={item.label}
                        className={cn(
                            "flex items-center justify-center w-full h-9 rounded-md transition-colors",
                            containerStyle
                        )}
                    >
                        <Icon className={iconClass} />
                    </Link>
                </div>
            );
        }

        // Expanded mode - simple link
        if (!hasSubItems && item.href) {
            return (
                <div key={item.label}>
                    <Link
                        href={item.href}
                        onClick={(e) => handleNavClick(e, item.href!)}
                        className={cn(
                            "flex items-center gap-2.5 px-2.5 h-9 rounded-md text-[13px] font-medium transition-colors",
                            containerStyle
                        )}
                    >
                        <Icon className={iconClass} />
                        <span className={labelClass}>{item.label}</span>
                    </Link>
                </div>
            );
        }

        // Expanded mode - collapsible parent with sub-items
        return (
            <div key={item.label}>
                <button
                    onClick={() => toggleExpanded(item.label)}
                    aria-expanded={expanded}
                    aria-label={`${item.label} (${expanded ? "expandido" : "colapsado"})`}
                    className={cn(
                        "flex items-center gap-2.5 px-2.5 h-9 w-full rounded-md text-[13px] font-medium transition-colors",
                        active
                            ? "text-primary"
                            : "text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-foreground"
                    )}
                >
                    <Icon className="h-4 w-4 flex-shrink-0" />
                    <span className="truncate flex-1 text-left">{item.label}</span>
                    {expanded ? (
                        <ChevronDown className="h-3.5 w-3.5 flex-shrink-0 opacity-50" />
                    ) : (
                        <ChevronRight className="h-3.5 w-3.5 flex-shrink-0 opacity-50" />
                    )}
                </button>
                {expanded && item.subItems && (
                    <div className="ml-[22px] border-l border-sidebar-border pl-2.5 mt-0.5 space-y-0.5">
                        {item.subItems.map((sub) => {
                            const subActive = isActive(sub.href);
                            return (
                                <Link
                                    key={sub.href}
                                    href={sub.href}
                                    onClick={(e) => handleNavClick(e, sub.href)}
                                    className={cn(
                                        "flex items-center h-8 px-2 rounded-md text-[13px] transition-colors",
                                        subActive
                                            ? "bg-primary/15 text-primary font-medium"
                                            : "text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-foreground"
                                    )}
                                >
                                    <span className="truncate">{sub.label}</span>
                                </Link>
                            );
                        })}
                    </div>
                )}
            </div>
        );
    };

    const renderSection = (section: NavSection, index: number) => {
        return (
            <div key={section.title ?? `section-${index}`} className={cn(index > 0 && "mt-4")}>
                {section.title && !collapsed && (
                    <div className="px-3 mb-1.5">
                        <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground/70">
                            {section.title}
                        </span>
                    </div>
                )}
                {section.title && collapsed && (
                    <div className="mx-3 mb-1.5 border-t border-sidebar-border" />
                )}
                <div className="space-y-0.5">
                    {section.items.map((item) => {
                        const visible = filterItem(item);
                        return visible ? renderNavItem(visible) : null;
                    })}
                </div>
            </div>
        );
    };

    const settingsActive = isActive("/configuracion");

    return (
        <aside
            className={cn(
                "flex flex-col border-r border-sidebar-border bg-sidebar flex-shrink-0 transition-all duration-200",
                collapsed ? "w-16" : "w-60"
            )}
        >
            {/* Logo block */}
            <div className="flex items-center gap-2.5 px-4 py-4 border-b border-sidebar-border">
                <img
                    src="/logo.svg"
                    alt="AutomatizaPyme"
                    className="h-7 w-7 flex-shrink-0"
                />
                {!collapsed && (
                    <span className="text-sm font-semibold text-sidebar-foreground truncate">
                        AutomatizaPyme
                    </span>
                )}
            </div>

            {/* Scrollable nav area */}
            <ScrollArea className="flex-1">
                <nav aria-label="Navegacion principal" className="px-2 py-3">
                    {NAV_SECTIONS.map((section, i) => renderSection(section, i))}
                </nav>
            </ScrollArea>

            {/* Footer: settings (admin only) + collapse toggle */}
            <div className="px-2 py-3 border-t border-sidebar-border space-y-0.5">
                {/* Settings link — solo admin */}
                {isAdmin && (collapsed ? (
                    <Link
                        href="/configuracion/empresa"
                        onClick={(e) => handleNavClick(e, "/configuracion/empresa")}
                        title="Configuración"
                        aria-label="Configuración"
                        className={cn(
                            "flex items-center justify-center w-full h-9 rounded-md transition-colors",
                            settingsActive
                                ? "bg-primary/15 text-primary"
                                : "text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-foreground"
                        )}
                    >
                        <Settings className="h-4 w-4" />
                    </Link>
                ) : (
                    <Link
                        href="/configuracion/empresa"
                        onClick={(e) => handleNavClick(e, "/configuracion/empresa")}
                        className={cn(
                            "flex items-center gap-2.5 px-2.5 h-9 rounded-md text-[13px] font-medium transition-colors",
                            settingsActive
                                ? "bg-primary/15 text-primary"
                                : "text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-foreground"
                        )}
                    >
                        <Settings className="h-4 w-4 flex-shrink-0" />
                        <span className="truncate">Configuración</span>
                    </Link>
                ))}

                {/* Collapse toggle */}
                <button
                    onClick={toggleCollapsed}
                    title={collapsed ? "Expandir menú" : "Colapsar menú"}
                    aria-label={collapsed ? "Expandir menú lateral" : "Colapsar menú lateral"}
                    aria-expanded={!collapsed}
                    aria-controls="main-content"
                    className={cn(
                        "flex items-center h-9 rounded-md text-[13px] font-medium transition-colors text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-foreground",
                        collapsed ? "justify-center w-full" : "gap-2.5 px-2.5 w-full"
                    )}
                >
                    {collapsed ? (
                        <PanelLeft className="h-4 w-4" />
                    ) : (
                        <>
                            <PanelLeftClose className="h-4 w-4 flex-shrink-0" />
                            <span className="truncate">Colapsar</span>
                        </>
                    )}
                </button>
            </div>
        </aside>
    );
}
