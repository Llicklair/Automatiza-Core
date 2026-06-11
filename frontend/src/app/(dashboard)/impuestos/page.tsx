"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { Scale, FileText, Send } from "lucide-react";
import { ResumenPanel } from "./ResumenPanel";
import { ModelosPanel } from "./ModelosPanel";
import { AsistidaPanel } from "./AsistidaPanel";
import { PageContainer } from "@/components/shared/PageContainer";

type Tab = "resumen" | "modelos" | "asistida";

export default function ImpuestosPage() {
    const searchParams = useSearchParams();
    const initial = searchParams.get("tab");
    const [tab, setTab] = useState<Tab>(
        initial === "modelos" || initial === "asistida" ? initial : "resumen"
    );

    const tabs: { key: Tab; label: string; icon: typeof Scale }[] = [
        { key: "resumen", label: "Resumen", icon: Scale },
        { key: "modelos", label: "Modelos AEAT", icon: FileText },
        { key: "asistida", label: "Presentación asistida", icon: Send },
    ];

    return (
        <PageContainer width="5xl">
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

            {tab === "resumen" && <ResumenPanel />}
            {tab === "modelos" && <ModelosPanel />}
            {tab === "asistida" && <AsistidaPanel />}
        </PageContainer>
    );
}
