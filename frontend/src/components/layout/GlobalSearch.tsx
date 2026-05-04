"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Search, Users, UserCircle, FileText } from "lucide-react";
import {
    CommandDialog,
    CommandInput,
    CommandList,
    CommandEmpty,
    CommandGroup,
    CommandItem,
    CommandSeparator,
} from "@/components/ui/command";
import { NAV_SECTIONS } from "./nav-config";
import { api, type SearchResult } from "@/lib/api";

const TYPE_ICON: Record<string, React.ReactNode> = {
    employee: <Users className="mr-2 h-4 w-4 text-indigo-400" />,
    client:   <UserCircle className="mr-2 h-4 w-4 text-emerald-400" />,
    invoice:  <FileText className="mr-2 h-4 w-4 text-amber-400" />,
};

const TYPE_LABEL: Record<string, string> = {
    employee: "Empleados",
    client:   "Clientes",
    invoice:  "Facturas",
};

function groupResults(results: SearchResult[]): Record<string, SearchResult[]> {
    return results.reduce<Record<string, SearchResult[]>>((acc, r) => {
        (acc[r.type] ||= []).push(r);
        return acc;
    }, {});
}

export function GlobalSearch() {
    const [open, setOpen] = useState(false);
    const [query, setQuery] = useState("");
    const [results, setResults] = useState<SearchResult[]>([]);
    const [loading, setLoading] = useState(false);
    const router = useRouter();

    useEffect(() => {
        const down = (e: KeyboardEvent) => {
            if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
                e.preventDefault();
                setOpen((prev) => !prev);
            }
        };
        document.addEventListener("keydown", down);
        return () => document.removeEventListener("keydown", down);
    }, []);

    // Reset on close
    useEffect(() => {
        if (!open) {
            setQuery("");
            setResults([]);
        }
    }, [open]);

    const fetchResults = useCallback(async (q: string) => {
        if (q.length < 2) { setResults([]); return; }
        setLoading(true);
        try {
            const data = await api.search(q);
            setResults(data);
        } catch {
            setResults([]);
        } finally {
            setLoading(false);
        }
    }, []);

    // Debounce
    useEffect(() => {
        const t = setTimeout(() => fetchResults(query), 250);
        return () => clearTimeout(t);
    }, [query, fetchResults]);

    const handleSelect = (href: string) => {
        setOpen(false);
        router.push(href);
    };

    const grouped = groupResults(results);
    const hasResults = results.length > 0;

    return (
        <>
            <button
                onClick={() => setOpen(true)}
                className="flex items-center gap-2 h-8 px-3 rounded-md border border-input bg-background text-muted-foreground text-xs hover:bg-accent hover:text-accent-foreground transition-colors"
            >
                <Search className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">Buscar...</span>
                <kbd className="hidden sm:inline-flex h-5 items-center gap-0.5 rounded border border-border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground">
                    <span className="text-[10px]">⌘</span>K
                </kbd>
            </button>

            <CommandDialog open={open} onOpenChange={setOpen}>
                <CommandInput
                    placeholder="Buscar empleados, clientes, facturas..."
                    value={query}
                    onValueChange={setQuery}
                />
                <CommandList>
                    {/* Real data results */}
                    {query.length >= 2 && (
                        <>
                            {loading && (
                                <div className="py-6 text-center text-sm text-muted-foreground">Buscando…</div>
                            )}
                            {!loading && !hasResults && (
                                <CommandEmpty>Sin resultados para &quot;{query}&quot;</CommandEmpty>
                            )}
                            {!loading && hasResults && Object.entries(grouped).map(([type, items]) => (
                                <CommandGroup key={type} heading={TYPE_LABEL[type] ?? type}>
                                    {items.map((r) => (
                                        <CommandItem
                                            key={r.id}
                                            value={`${r.label} ${r.sublabel}`}
                                            onSelect={() => handleSelect(r.href)}
                                        >
                                            {TYPE_ICON[r.type]}
                                            <span>{r.label}</span>
                                            {r.sublabel && (
                                                <span className="ml-2 text-xs text-muted-foreground">{r.sublabel}</span>
                                            )}
                                        </CommandItem>
                                    ))}
                                </CommandGroup>
                            ))}
                            <CommandSeparator />
                        </>
                    )}

                    {/* Navigation fallback (always shown) */}
                    {NAV_SECTIONS.map((section, si) => (
                        <CommandGroup key={si} heading={section.title || "Navegación"}>
                            {section.items.map((item) => {
                                if (item.href) {
                                    return (
                                        <CommandItem
                                            key={item.href}
                                            value={item.label}
                                            onSelect={() => handleSelect(item.href!)}
                                        >
                                            <item.icon className="mr-2 h-4 w-4 text-muted-foreground" />
                                            {item.label}
                                        </CommandItem>
                                    );
                                }
                                return item.subItems?.map((sub) => (
                                    <CommandItem
                                        key={sub.href}
                                        value={`${item.label} ${sub.label}`}
                                        onSelect={() => handleSelect(sub.href)}
                                    >
                                        <item.icon className="mr-2 h-4 w-4 text-muted-foreground" />
                                        <span className="text-muted-foreground mr-1">{item.label} ›</span>
                                        {sub.label}
                                    </CommandItem>
                                ));
                            })}
                        </CommandGroup>
                    ))}
                </CommandList>
            </CommandDialog>
        </>
    );
}
