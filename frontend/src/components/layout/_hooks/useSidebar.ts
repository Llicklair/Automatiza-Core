"use client";

import { useState, useEffect, useCallback } from "react";
import { usePathname, useRouter } from "next/navigation";
import { NAV_SECTIONS, type NavItem } from "../nav-config";
import { showConfirm } from "@/stores/confirm";
import { useNavigationGuard } from "@/stores/navigationGuard";
import type React from "react";

const STORAGE_KEY = "sidebar-collapsed";

export function useSidebar() {
    const pathname = usePathname();
    const router   = useRouter();
    const navBlocked = useNavigationGuard((s) => s.blocked);
    const navMessage = useNavigationGuard((s) => s.message);

    const [collapsed, setCollapsed]           = useState(false);
    const [expandedItems, setExpandedItems]   = useState<Set<string>>(new Set());

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
                    if (match) toExpand.add(item.label);
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
            try { localStorage.setItem(STORAGE_KEY, String(next)); } catch {}
            return next;
        });
    }, []);

    const toggleExpanded = useCallback((label: string) => {
        setExpandedItems((prev) => {
            const next = new Set(prev);
            if (next.has(label)) { next.delete(label); } else { next.add(label); }
            return next;
        });
    }, []);

    const handleNavClick = useCallback(
        (e: React.MouseEvent, href: string) => {
            if (!navBlocked) return;
            e.preventDefault();
            showConfirm({
                title: "Hay trabajo en curso",
                message: navMessage || "Si cambias de sección perderás el progreso actual. ¿Quieres salir igualmente?",
                confirmLabel: "Salir",
                cancelLabel: "Quedarse",
            }).then((confirmed) => { if (confirmed) router.push(href); });
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

    return {
        collapsed,
        expandedItems,
        toggleCollapsed,
        toggleExpanded,
        handleNavClick,
        isActive,
        isParentActive,
    };
}
