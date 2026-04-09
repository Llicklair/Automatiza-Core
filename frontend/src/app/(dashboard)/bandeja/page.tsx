"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { ShieldCheck, Inbox } from "lucide-react";
import { ApprovalsTab } from "./_components/ApprovalsTab";
import { ActivityTab } from "./_components/ActivityTab";

const TABS = [
    { key: "aprobaciones", label: "Aprobaciones", icon: ShieldCheck },
    { key: "actividad", label: "Actividad", icon: Inbox },
] as const;

type TabKey = (typeof TABS)[number]["key"];

export default function BandejaPage() {
    const searchParams = useSearchParams();
    const initialTab = TABS.some(t => t.key === searchParams.get("tab")) ? searchParams.get("tab") as TabKey : "aprobaciones";
    const [activeTab, setActiveTab] = useState<TabKey>(initialTab);
    const [pendingCount, setPendingCount] = useState(0);

    const switchTab = (tab: TabKey) => {
        setActiveTab(tab);
        const url = new URL(window.location.href);
        url.searchParams.set("tab", tab);
        window.history.replaceState(null, "", url.toString());
    };

    return (
        <div className="max-w-5xl mx-auto px-4 py-8 space-y-6">
            {/* Header */}
            <div>
                <h1 className="text-xl font-semibold text-foreground flex items-center gap-2">
                    <Inbox className="w-6 h-6 text-violet-400" /> Bandeja
                </h1>
                <p className="text-xs text-muted-foreground mt-1">Aprobaciones pendientes y actividad de tus agentes</p>
            </div>

            {/* Tabs */}
            <div className="flex gap-1 border-b border-border">
                {TABS.map(tab => {
                    const Icon = tab.icon;
                    const isActive = activeTab === tab.key;
                    return (
                        <button
                            key={tab.key}
                            onClick={() => switchTab(tab.key)}
                            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px ${
                                isActive
                                    ? "border-violet-500 text-foreground"
                                    : "border-transparent text-muted-foreground hover:text-foreground hover:border-border"
                            }`}
                        >
                            <Icon className="w-4 h-4" />
                            {tab.label}
                            {tab.key === "aprobaciones" && pendingCount > 0 && (
                                <span className="ml-1 px-1.5 py-0.5 text-[10px] font-bold rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/30">
                                    {pendingCount}
                                </span>
                            )}
                        </button>
                    );
                })}
            </div>

            {/* Tab content */}
            {activeTab === "aprobaciones" && (
                <ApprovalsTab onPendingCount={setPendingCount} />
            )}

            {activeTab === "actividad" && (
                <ActivityTab isActive={activeTab === "actividad"} />
            )}
        </div>
    );
}
