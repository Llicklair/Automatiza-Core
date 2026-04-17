"use client";

import { CalendarClock, Newspaper, MessageSquare } from "lucide-react";
import { useCompliance, type Tab } from "./_hooks/useCompliance";
import { CalendarioTab } from "./_components/CalendarioTab";
import { BOETab } from "./_components/BOETab";
import { ConsultaTab } from "./_components/ConsultaTab";

export default function CompliancePage() {
    const { tab, setTab } = useCompliance();

    return (
        <div className="p-8 max-w-5xl mx-auto">
            <div className="mb-8">
                <h1 className="text-2xl font-bold text-foreground">Cumplimiento Legal y Fiscal</h1>
                <p className="text-sm text-muted-foreground mt-1">
                    Calendario fiscal AEAT, novedades del BOE y consultas sobre obligaciones
                </p>
            </div>

            <div className="flex gap-1 mb-8 p-1 rounded-lg bg-card border border-border w-fit">
                {([
                    { id: "calendario", label: "Calendario fiscal", icon: CalendarClock },
                    { id: "boe", label: "Novedades BOE", icon: Newspaper },
                    { id: "consulta", label: "Consultar", icon: MessageSquare },
                ] as { id: Tab; label: string; icon: React.ElementType }[]).map(({ id, label, icon: Icon }) => (
                    <button
                        key={id}
                        onClick={() => setTab(id)}
                        className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition ${tab === id
                            ? "bg-primary text-foreground"
                            : "text-muted-foreground hover:text-foreground"
                            }`}
                    >
                        <Icon className="w-4 h-4" />
                        {label}
                    </button>
                ))}
            </div>

            {tab === "calendario" && <CalendarioTab />}
            {tab === "boe" && <BOETab />}
            {tab === "consulta" && <ConsultaTab />}
        </div>
    );
}
