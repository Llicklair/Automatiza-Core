"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { BadgeCheck, Stamp, ShieldCheck } from "lucide-react";
import { ModoVerifactuPanel } from "./ModoVerifactuPanel";
import { ApoderamientoPanel } from "./ApoderamientoPanel";
import { FirmaDigitalPanel } from "./FirmaDigitalPanel";

type Tab = "verifactu" | "apoderamiento" | "firma";

export default function ConfiguracionFiscalPage() {
    const searchParams = useSearchParams();
    const initial = searchParams.get("tab");
    const [tab, setTab] = useState<Tab>(
        initial === "apoderamiento" || initial === "firma" ? initial : "verifactu"
    );

    const tabs: { key: Tab; label: string; icon: typeof BadgeCheck }[] = [
        { key: "verifactu", label: "Modo Verifactu", icon: BadgeCheck },
        { key: "apoderamiento", label: "Apoderamiento AEAT", icon: Stamp },
        { key: "firma", label: "Firma digital", icon: ShieldCheck },
    ];

    return (
        <div className="p-6 max-w-3xl space-y-6">
            <div>
                <h1 className="text-xl font-bold text-foreground">Configuración fiscal (AEAT)</h1>
                <p className="text-sm text-muted-foreground mt-1">
                    Modo Verifactu, apoderamiento ante la AEAT y certificado de firma digital.
                </p>
            </div>

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

            {tab === "verifactu" && <ModoVerifactuPanel />}
            {tab === "apoderamiento" && <ApoderamientoPanel />}
            {tab === "firma" && <FirmaDigitalPanel />}
        </div>
    );
}
