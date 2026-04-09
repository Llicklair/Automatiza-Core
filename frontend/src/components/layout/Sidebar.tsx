"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Settings, ChevronDown, ChevronRight, PanelLeftClose, PanelLeft } from "lucide-react";
import { cn } from "@/lib/utils";
import { ScrollArea } from "@/components/ui/scroll-area";
import { NAV_SECTIONS, type NavItem, type NavSection } from "./nav-config";
import { showConfirm } from "@/stores/confirm";
import { useNavigationGuard } from "@/stores/navigationGuard";

const STORAGE_KEY = "sidebar-collapsed";

export function Sidebar() {
    const pathname = usePathname();
    const router = useRouter();
    const navBlocked = useNavigationGuard((s) => s.blocked);
    const navMessage = useNavigationGuard((s) => s.message);

    const [collapsed, setCollapsed] = useState(false);
    const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());

    // Load collapsed state from localStorage
    useEffect(() => {
        try {
            const stored = localStorage.getItem(STORAGE_KEY);
            if (stored === "true") setCollapsed(true);
        } catch {}
    }, []);

    // Auto-expand section matching current pathname on mount
    useEffect(() => {
        const toExpand = new Set<string>();
        for (const section of NAV_SECTIONS) {
            for (const item of section.items) {
                if (item.subItems) {
                    const match = item.subItems.some(
                        (sub) => pathname === sub.href || pathname.startsWith(sub.href + "/")
                    );
                    if (match) {
                        toExpand.add(item.label);
                    }
                }
            }
        }
        if (toExpand.size > 0) {
            setExpandedItems((prev) => {
                const next = new Set(prev);
                toExpand.forEach((item) => next.add(item));
                return next;
            });
        }
    }, [pathname]);

    const toggleCollapsed = useCallback(() => {
        setCollapsed((prev) => {
            const next = !prev;
            try {
                localStorage.setItem(STORAGE_KEY, String(next));
            } catch {}
            return next;
        });
    }, []);

    const toggleExpanded = useCallback((label: string) => {
        setExpandedItems((prev) => {
            const next = new Set(prev);
            if (next.has(label)) {
                next.delete(label);
            } else {
                next.add(label);
            }
            return next;
        });
    }, []);

    const handleNavClick = useCallback(
        (e: React.MouseEvent, href: string) => {
            if (!navBlocked) return;
            e.preventDefault();
            showConfirm({
                title: "Hay trabajo en curso",
                message:
                    navMessage ||
                    "Si cambias de sección perderás el progreso actual. ¿Quieres salir igualmente?",
                confirmLabel: "Salir",
                cancelLabel: "Quedarse",
            }).then((confirmed) => {
                if (confirmed) router.push(href);
            });
        },
        [navBlocked, navMessage, router]
    );

    const isActive = useCallback(
        (href: string) => {
            if (href === "/") return pathname === "/";
            return pathname === href || pathname.startsWith(href + "/");
        },
        [pathname]
    );

    const isParentActive = useCallback(
        (item: NavItem) => {
            if (item.href) return isActive(item.href);
            if (item.subItems) {
                return item.subItems.some(
                    (sub) => pathname === sub.href || pathname.startsWith(sub.href + "/")
                );
            }
            return false;
        },
        [isActive, pathname]
    );

    const renderNavItem = (item: NavItem) => {
        const Icon = item.icon;
        const active = isParentActive(item);
        const expanded = expandedItems.has(item.label);
        const hasSubItems = !!item.subItems && item.subItems.length > 0;

        // Collapsed mode
        if (collapsed) {
            const href = item.href || (item.subItems?.[0]?.href ?? "#");
            return (
                <div key={item.label}>
                    <Link
                        href={href}
                        onClick={(e) => handleNavClick(e, href)}
                        title={item.label}
                        className={cn(
                            "flex items-center justify-center w-full h-9 rounded-md transition-colors",
                            active
                                ? "bg-primary/15 text-primary"
                                : "text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-foreground"
                        )}
                    >
                        <Icon className="h-4 w-4 flex-shrink-0" />
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
                            active
                                ? "bg-primary/15 text-primary"
                                : "text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-foreground"
                        )}
                    >
                        <Icon className="h-4 w-4 flex-shrink-0" />
                        <span className="truncate">{item.label}</span>
                    </Link>
                </div>
            );
        }

        // Expanded mode - collapsible parent with sub-items
        return (
            <div key={item.label}>
                <button
                    onClick={() => toggleExpanded(item.label)}
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
                    {section.items.map((item) => renderNavItem(item))}
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

            {/* Footer: settings + collapse toggle */}
            <div className="px-2 py-3 border-t border-sidebar-border space-y-0.5">
                {/* Settings link */}
                {collapsed ? (
                    <Link
                        href="/configuracion/empresa"
                        onClick={(e) => handleNavClick(e, "/configuracion/empresa")}
                        title="Configuración"
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
                )}

                {/* Collapse toggle */}
                <button
                    onClick={toggleCollapsed}
                    title={collapsed ? "Expandir menú" : "Colapsar menú"}
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
