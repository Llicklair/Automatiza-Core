"use client";

import { useState } from "react";
import { Megaphone, Link2, PenSquare, CalendarClock, Sparkles } from "lucide-react";
import { TabCuentas } from "./_components/TabCuentas";
import { TabCrear } from "./_components/TabCrear";
import { TabProgramados } from "./_components/TabProgramados";
import { TabPlanIA } from "./_components/TabPlanIA";
import { PageContainer } from "@/components/shared/PageContainer";

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
            <div className="flex gap-1 border-b border-border">
                {TABS.map(({ key, label, icon: Icon }) => (
                    <button
                        key={key}
                        onClick={() => setTab(key)}
                        className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px ${
                            tab === key
                                ? "border-pink-500 text-pink-400"
                                : "border-transparent text-muted-foreground hover:text-foreground"
                        }`}
                    >
                        <Icon className="w-3.5 h-3.5" />
                        {label}
                    </button>
                ))}
            </div>

            {tab === "cuentas"     && <TabCuentas />}
            {tab === "crear"       && <TabCrear />}
            {tab === "programados" && <TabProgramados />}
            {tab === "plan-ia"     && <TabPlanIA />}
        </PageContainer>
    );
}
