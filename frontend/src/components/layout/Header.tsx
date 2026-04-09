"use client";

import { Breadcrumbs } from "./Breadcrumbs";
import { GlobalSearch } from "./GlobalSearch";
import { ThemeToggle } from "./ThemeToggle";
import NotificationBell from "@/components/NotificationBell";
import ProfileMenu from "@/components/ProfileMenu";

export function Header() {
    return (
        <header className="h-14 flex-shrink-0 flex items-center justify-between px-4 lg:px-6 border-b border-border bg-card/50 backdrop-blur-sm" style={{ zIndex: 9999 }}>
            <Breadcrumbs />
            <div className="ml-auto flex items-center gap-1">
                <GlobalSearch />
                <ThemeToggle />
                <NotificationBell />
                <ProfileMenu />
            </div>
        </header>
    );
}
