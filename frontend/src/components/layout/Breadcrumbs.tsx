"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import { ChevronRight, Home } from "lucide-react";
import { ROUTE_LABELS } from "./nav-config";

export function Breadcrumbs() {
    const pathname = usePathname();

    if (pathname === "/") return null;

    const segments = pathname.split("/").filter(Boolean);
    const crumbs: { label: string; href: string }[] = [];

    let currentPath = "";
    for (const segment of segments) {
        currentPath += `/${segment}`;
        const label = ROUTE_LABELS[currentPath] || segment.charAt(0).toUpperCase() + segment.slice(1).replace(/-/g, " ");
        crumbs.push({ label, href: currentPath });
    }

    return (
        <nav className="flex items-center gap-1 text-sm">
            <Link href="/" className="text-muted-foreground hover:text-foreground transition-colors">
                <Home className="h-3.5 w-3.5" />
            </Link>
            {crumbs.map((crumb, i) => {
                const isLast = i === crumbs.length - 1;
                return (
                    <div key={crumb.href} className="flex items-center gap-1">
                        <ChevronRight className="h-3 w-3 text-muted-foreground/50" />
                        {isLast ? (
                            <span className="text-foreground font-medium text-xs">{crumb.label}</span>
                        ) : (
                            <Link href={crumb.href} className="text-muted-foreground hover:text-foreground transition-colors text-xs">
                                {crumb.label}
                            </Link>
                        )}
                    </div>
                );
            })}
        </nav>
    );
}
