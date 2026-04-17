"use client";

import { useState } from "react";
import { Banknote, Link2, RefreshCw, TrendingUp } from "lucide-react";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/ui/button";
import { SaldosTab } from "./_components/SaldosTab";
import { TransaccionesTab } from "./_components/TransaccionesTab";
import { ResumenTab } from "./_components/ResumenTab";

type Tab = "saldos" | "transacciones" | "resumen";

const TABS: { id: Tab; label: string; icon: React.ElementType }[] = [
    { id: "saldos",         label: "Saldos",           icon: Banknote    },
    { id: "transacciones",  label: "Transacciones",    icon: RefreshCw   },
    { id: "resumen",        label: "Resumen del mes",  icon: TrendingUp  },
];

export default function BancaPage() {
    const [tab, setTab] = useState<Tab>("saldos");

    return (
        <div className="p-6 space-y-6">
            <PageHeader
                title="Banca PSD2"
                description="Visión financiera en tiempo real de tus cuentas bancarias"
                icon={Banknote}
                actions={
                    <Button variant="outline" asChild>
                        <a href="/integraciones">
                            <Link2 className="mr-2 h-4 w-4" /> Conectar banco
                        </a>
                    </Button>
                }
            />

            <div className="flex gap-1 p-1 rounded-xl bg-card border border-border w-fit">
                {TABS.map(({ id, label, icon: Icon }) => (
                    <button key={id} onClick={() => setTab(id)}
                        className={`flex items-center gap-2 px-5 py-2 rounded-lg text-sm font-medium transition-all duration-200
                            ${tab === id ? "bg-primary text-primary-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"}`}>
                        <Icon className="w-4 h-4" /> {label}
                    </button>
                ))}
            </div>

            {tab === "saldos"        && <SaldosTab />}
            {tab === "transacciones" && <TransaccionesTab />}
            {tab === "resumen"       && <ResumenTab />}
        </div>
    );
}
