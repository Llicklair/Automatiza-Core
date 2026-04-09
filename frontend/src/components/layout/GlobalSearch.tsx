"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Search } from "lucide-react";
import {
    CommandDialog,
    CommandInput,
    CommandList,
    CommandEmpty,
    CommandGroup,
    CommandItem,
} from "@/components/ui/command";
import { NAV_SECTIONS } from "./nav-config";

export function GlobalSearch() {
    const [open, setOpen] = useState(false);
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

    const handleSelect = (href: string) => {
        setOpen(false);
        router.push(href);
    };

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
                <CommandInput placeholder="Buscar página o función..." />
                <CommandList>
                    <CommandEmpty>Sin resultados.</CommandEmpty>
                    {NAV_SECTIONS.map((section, si) => (
                        <CommandGroup key={si} heading={section.title || "Principal"}>
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
