"use client";

import { useState } from "react";
import { Mail, FileText, BarChart3, Send } from "lucide-react";
import TabCampaigns from "./_components/CampaignsTab";
import TabTemplates from "./_components/TemplatesTab";
import TabStats from "./_components/StatsTab";
import { PageContainer } from "@/components/shared/PageContainer";

// ── Tabs ───────────────────────────────────────────────────────────────────────

const TABS = [
    { key: "campaigns", label: "Campañas",   icon: Send },
    { key: "templates", label: "Plantillas", icon: FileText },
    { key: "stats",     label: "Estadísticas", icon: BarChart3 },
] as const;
type TabKey = typeof TABS[number]["key"];

// ── Page ───────────────────────────────────────────────────────────────────────

export default function EmailMarketingPage() {
    const [tab, setTab] = useState<TabKey>("campaigns");

    return (
        <PageContainer width="5xl" className="space-y-5">
            <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-blue-500/10 border border-blue-500/20">
                    <Mail className="w-5 h-5 text-blue-400" />
                </div>
                <div>
                    <h1 className="text-lg font-semibold text-foreground">Email Marketing</h1>
                    <p className="text-xs text-muted-foreground">Campañas masivas a tus clientes usando tu cuenta de email configurada</p>
                </div>
            </div>

            <div className="flex gap-1 border-b border-border">
                {TABS.map(({ key, label, icon: Icon }) => (
                    <button
                        key={key}
                        onClick={() => setTab(key)}
                        className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px ${
                            tab === key
                                ? "border-blue-500 text-blue-400"
                                : "border-transparent text-muted-foreground hover:text-foreground"
                        }`}
                    >
                        <Icon className="w-3.5 h-3.5" />
                        {label}
                    </button>
                ))}
            </div>

            {tab === "campaigns" && <TabCampaigns />}
            {tab === "templates" && <TabTemplates />}
            {tab === "stats"     && <TabStats />}
        </PageContainer>
    );
}
