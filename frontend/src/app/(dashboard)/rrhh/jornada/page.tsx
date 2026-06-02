"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { Clock, Timer, Umbrella } from "lucide-react";
import { HorariosPanel } from "../horarios/HorariosPanel";
import { FichajesPanel } from "../fichajes/FichajesPanel";
import { VacacionesPanel } from "../vacaciones/VacacionesPanel";

type Tab = "horarios" | "fichajes" | "vacaciones";

export default function JornadaPage() {
    const searchParams = useSearchParams();
    const initial = searchParams.get("tab");
    const [tab, setTab] = useState<Tab>(
        initial === "fichajes" || initial === "vacaciones" ? initial : "horarios"
    );

    const tabs: { key: Tab; label: string; icon: typeof Clock }[] = [
        { key: "horarios", label: "Horarios", icon: Clock },
        { key: "fichajes", label: "Fichajes", icon: Timer },
        { key: "vacaciones", label: "Vacaciones", icon: Umbrella },
    ];

    return (
        <div className="p-8 max-w-[1400px] mx-auto space-y-6">
            <div className="flex items-center gap-1 border-b border-border">
                {tabs.map(t => {
                    const Icon = t.icon;
                    const active = tab === t.key;
                    return (
                        <button
                            key={t.key}
                            onClick={() => setTab(t.key)}
                            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${
                                active
                                    ? "border-primary text-foreground"
                                    : "border-transparent text-muted-foreground hover:text-foreground"
                            }`}>
                            <Icon className="w-4 h-4" /> {t.label}
                        </button>
                    );
                })}
            </div>

            {tab === "horarios" && <HorariosPanel />}
            {tab === "fichajes" && <FichajesPanel />}
            {tab === "vacaciones" && <VacacionesPanel />}
        </div>
    );
}
