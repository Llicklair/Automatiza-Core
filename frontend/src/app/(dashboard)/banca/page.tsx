"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Banknote, CheckCircle2, Link2, RefreshCw, TrendingUp } from "lucide-react";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/ui/button";
import { SaldosTab } from "./_components/SaldosTab";
import { TransaccionesTab } from "./_components/TransaccionesTab";
import { ResumenTab } from "./_components/ResumenTab";
import { ConciliacionTab } from "./_components/ConciliacionTab";
import { PageContainer } from "@/components/shared/PageContainer";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";

type Tab = "saldos" | "transacciones" | "conciliacion" | "resumen";

const TABS: { id: Tab; labelKey: string; icon: React.ElementType }[] = [
    { id: "saldos",         labelKey: "page.tabs.saldos",        icon: Banknote      },
    { id: "transacciones",  labelKey: "page.tabs.transacciones", icon: RefreshCw     },
    { id: "conciliacion",   labelKey: "page.tabs.conciliacion",  icon: CheckCircle2  },
    { id: "resumen",        labelKey: "page.tabs.resumen",       icon: TrendingUp    },
];

export default function BancaPage() {
    const t = useTranslations("banca");
    const [tab, setTab] = useState<Tab>("saldos");

    return (
        <PageContainer width="full">
            <PageHeader
                title={t("page.title")}
                description={t("page.description")}
                icon={Banknote}
                actions={
                    <Button variant="outline" asChild>
                        <a href="/integraciones">
                            <Link2 className="mr-2 h-4 w-4" /> {t("page.connectBank")}
                        </a>
                    </Button>
                }
            />

            <Tabs value={tab} onValueChange={(v) => setTab(v as Tab)}>
                <TabsList className="h-auto w-full justify-start gap-1 rounded-none border-b border-border bg-transparent p-0">
                    {TABS.map(({ id, labelKey, icon: Icon }) => (
                        <TabsTrigger
                            key={id}
                            value={id}
                            className="-mb-px flex items-center gap-2 rounded-none border-b-2 border-transparent px-4 py-2.5 text-sm font-medium text-muted-foreground transition-colors hover:border-border hover:text-foreground data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:text-foreground data-[state=active]:shadow-none"
                        >
                            <Icon className="w-4 h-4" /> {t(labelKey)}
                        </TabsTrigger>
                    ))}
                </TabsList>
            </Tabs>

            {tab === "saldos"        && <SaldosTab />}
            {tab === "transacciones" && <TransaccionesTab />}
            {tab === "conciliacion"  && <ConciliacionTab />}
            {tab === "resumen"       && <ResumenTab />}
        </PageContainer>
    );
}
