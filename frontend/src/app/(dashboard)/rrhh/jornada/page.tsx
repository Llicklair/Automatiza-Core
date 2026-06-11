"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { Clock, Timer, Umbrella } from "lucide-react";
import { HorariosPanel } from "../horarios/HorariosPanel";
import { FichajesPanel } from "../fichajes/FichajesPanel";
import { VacacionesPanel } from "../vacaciones/VacacionesPanel";
import { PageContainer } from "@/components/shared/PageContainer";

type Tab = "horarios" | "fichajes" | "vacaciones";

// I18N — config estructural + labelKey; se traduce en render con t(key).
const TABS: { key: Tab; labelKey: string; icon: typeof Clock }[] = [
    { key: "horarios", labelKey: "jornada.tabs.horarios", icon: Clock },
    { key: "fichajes", labelKey: "jornada.tabs.fichajes", icon: Timer },
    { key: "vacaciones", labelKey: "jornada.tabs.vacaciones", icon: Umbrella },
];

export default function JornadaPage() {
    const t = useTranslations("rrhh");
    const searchParams = useSearchParams();
    const initial = searchParams.get("tab");
    const [tab, setTab] = useState<Tab>(
        initial === "fichajes" || initial === "vacaciones" ? initial : "horarios"
    );

    return (
        <PageContainer>
            <div className="flex items-center gap-1 border-b border-border">
                {TABS.map(item => {
                    const Icon = item.icon;
                    const active = tab === item.key;
                    return (
                        <button
                            key={item.key}
                            onClick={() => setTab(item.key)}
                            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${
                                active
                                    ? "border-primary text-foreground"
                                    : "border-transparent text-muted-foreground hover:text-foreground"
                            }`}>
                            <Icon className="w-4 h-4" /> {t(item.labelKey)}
                        </button>
                    );
                })}
            </div>

            {tab === "horarios" && <HorariosPanel />}
            {tab === "fichajes" && <FichajesPanel />}
            {tab === "vacaciones" && <VacacionesPanel />}
        </PageContainer>
    );
}
