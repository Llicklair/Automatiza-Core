"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { ShieldCheck, Inbox } from "lucide-react";
import { ApprovalsTab } from "./_components/ApprovalsTab";
import { ActivityTab } from "./_components/ActivityTab";
import { PageContainer } from "@/components/shared/PageContainer";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";

const TABS = [
    { key: "aprobaciones", labelKey: "tabs.approvals", icon: ShieldCheck },
    { key: "actividad", labelKey: "tabs.activity", icon: Inbox },
] as const;

type TabKey = (typeof TABS)[number]["key"];

export default function BandejaPage() {
    const t = useTranslations("bandeja");
    const searchParams = useSearchParams();
    const initialTab = TABS.some(tab => tab.key === searchParams.get("tab")) ? searchParams.get("tab") as TabKey : "aprobaciones";
    const [activeTab, setActiveTab] = useState<TabKey>(initialTab);
    const [pendingCount, setPendingCount] = useState(0);

    const switchTab = (tab: TabKey) => {
        setActiveTab(tab);
        const url = new URL(window.location.href);
        url.searchParams.set("tab", tab);
        window.history.replaceState(null, "", url.toString());
    };

    return (
        <PageContainer width="5xl">
            {/* Header */}
            <div>
                <h1 className="text-xl font-semibold text-foreground flex items-center gap-2">
                    <Inbox className="w-6 h-6 text-violet-400" /> {t("title")}
                </h1>
                <p className="text-xs text-muted-foreground mt-1">{t("subtitle")}</p>
            </div>

            {/* Tabs */}
            <Tabs value={activeTab} onValueChange={(v) => switchTab(v as TabKey)}>
                <TabsList className="h-auto w-full justify-start gap-1 rounded-none border-b border-border bg-transparent p-0">
                    {TABS.map(tab => {
                        const Icon = tab.icon;
                        return (
                            <TabsTrigger
                                key={tab.key}
                                value={tab.key}
                                className="-mb-px flex items-center gap-2 rounded-none border-b-2 border-transparent px-4 py-2.5 text-sm font-medium text-muted-foreground transition-colors hover:border-border hover:text-foreground data-[state=active]:border-violet-500 data-[state=active]:bg-transparent data-[state=active]:text-foreground data-[state=active]:shadow-none"
                            >
                                <Icon className="w-4 h-4" />
                                {t(tab.labelKey)}
                                {tab.key === "aprobaciones" && pendingCount > 0 && (
                                    <span className="ml-1 px-1.5 py-0.5 text-[10px] font-bold rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/30">
                                        {pendingCount}
                                    </span>
                                )}
                            </TabsTrigger>
                        );
                    })}
                </TabsList>
            </Tabs>

            {/* Tab content */}
            {activeTab === "aprobaciones" && (
                <ApprovalsTab onPendingCount={setPendingCount} />
            )}

            {activeTab === "actividad" && (
                <ActivityTab isActive={activeTab === "actividad"} />
            )}
        </PageContainer>
    );
}
