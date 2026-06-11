"use client";

import { useState } from "react";
import { Megaphone, Link2, PenSquare, CalendarClock, Sparkles } from "lucide-react";
import { TabCuentas } from "./_components/TabCuentas";
import { TabCrear } from "./_components/TabCrear";
import { TabProgramados } from "./_components/TabProgramados";
import { TabPlanIA } from "./_components/TabPlanIA";
import { PageContainer } from "@/components/shared/PageContainer";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";

// ── Tabs ───────────────────────────────────────────────────────────────────────

const TABS = [
    { key: "cuentas",     label: "Cuentas",     icon: Link2 },
    { key: "crear",       label: "Crear post",  icon: PenSquare },
    { key: "programados", label: "Programados",  icon: CalendarClock },
    { key: "plan-ia",     label: "Plan IA",     icon: Sparkles },
] as const;

type TabKey = typeof TABS[number]["key"];

// ── Page ───────────────────────────────────────────────────────────────────────

export default function MarketingPage() {
    const [tab, setTab] = useState<TabKey>("cuentas");

    return (
        <PageContainer width="5xl" className="space-y-5">
            {/* Header */}
            <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-pink-500/10 border border-pink-500/20">
                    <Megaphone className="w-5 h-5 text-pink-400" />
                </div>
                <div>
                    <h1 className="text-lg font-semibold text-foreground">Marketing &amp; Redes Sociales</h1>
                    <p className="text-xs text-muted-foreground">Conecta tus redes, programa posts y genera contenido con IA</p>
                </div>
            </div>

            {/* Tabs */}
            <Tabs value={tab} onValueChange={(v) => setTab(v as TabKey)}>
                <TabsList className="h-auto w-full justify-start gap-1 rounded-none border-b border-border bg-transparent p-0">
                    {TABS.map(({ key, label, icon: Icon }) => (
                        <TabsTrigger
                            key={key}
                            value={key}
                            className="-mb-px flex items-center gap-2 rounded-none border-b-2 border-transparent px-4 py-2.5 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground data-[state=active]:border-pink-500 data-[state=active]:bg-transparent data-[state=active]:text-pink-400 data-[state=active]:shadow-none"
                        >
                            <Icon className="w-3.5 h-3.5" />
                            {label}
                        </TabsTrigger>
                    ))}
                </TabsList>
            </Tabs>

            {tab === "cuentas"     && <TabCuentas />}
            {tab === "crear"       && <TabCrear />}
            {tab === "programados" && <TabProgramados />}
            {tab === "plan-ia"     && <TabPlanIA />}
        </PageContainer>
    );
}
