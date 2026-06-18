"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { Scale, FileText, Send } from "lucide-react";
import { ResumenPanel } from "./ResumenPanel";
import { ModelosPanel } from "./ModelosPanel";
import { AsistidaPanel } from "./AsistidaPanel";
import { PageContainer } from "@/components/shared/PageContainer";

type Tab = "resumen" | "modelos" | "asistida";

export default function ImpuestosPage() {
    const t = useTranslations("impuestos");
    const searchParams = useSearchParams();
    const initial = searchParams.get("tab");
    const [tab, setTab] = useState<Tab>(
        initial === "modelos" || initial === "asistida" ? initial : "resumen"
    );

    const tabs: { key: Tab; label: string; icon: typeof Scale }[] = [
        { key: "resumen", label: t("tabs.resumen"), icon: Scale },
        { key: "modelos", label: t("tabs.modelos"), icon: FileText },
        { key: "asistida", label: t("tabs.asistida"), icon: Send },
    ];

    return (
        <PageContainer width="5xl">
            <div className="flex items-center gap-1 border-b border-border">
                {tabs.map(tb => {
                    const Icon = tb.icon;
                    const active = tab === tb.key;
                    return (
                        <button
                            key={tb.key}
                            onClick={() => setTab(tb.key)}
                            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${
                                active
                                    ? "border-primary text-foreground"
                                    : "border-transparent text-muted-foreground hover:text-foreground"
                            }`}>
                            <Icon className="w-4 h-4" /> {tb.label}
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
