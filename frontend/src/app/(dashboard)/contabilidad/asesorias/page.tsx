"use client";

import { Scale, Briefcase, Users, Building, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { useAsesorias } from "./_hooks/useAsesorias";
import { AdvisoryChatPanel } from "./_components/AdvisoryChatPanel";
import { CalendarSection } from "./_components/CalendarSection";
import { GuidesSection } from "./_components/GuidesSection";
import { NewsFeed } from "./_components/NewsFeed";

const TABS = [
    { id: "fiscal", label: "Fiscal / AEAT", icon: Briefcase },
    { id: "laboral", label: "Laboral", icon: Users },
    { id: "mercantil", label: "Mercantil", icon: Building },
];

export default function AsesoriasPage() {
    const a = useAsesorias();

    return (
        <div className="p-8 max-w-7xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight text-foreground flex items-center gap-3">
                        <Scale className="w-8 h-8 text-primary" />
                        Asesoría Jurídica y Fiscal
                    </h1>
                    <p className="text-muted-foreground mt-2">
                        Mantente al día de tus obligaciones con la AEAT y las últimas normativas del BOE para tu negocio.
                    </p>
                </div>

                <div className="flex bg-card p-1 rounded-xl border border-border">
                    {TABS.map((tab) => {
                        const Icon = tab.icon;
                        const isActive = a.filter === tab.id;
                        return (
                            <Button
                                key={tab.id}
                                variant="ghost"
                                onClick={() => a.setFilter(tab.id)}
                                className={cn(
                                    "flex items-center gap-2 text-sm font-medium",
                                    isActive
                                        ? "bg-primary/20 text-primary shadow-sm hover:bg-primary/20"
                                        : "text-muted-foreground hover:text-foreground"
                                )}
                            >
                                <Icon className="w-4 h-4" />
                                {tab.label}
                            </Button>
                        );
                    })}
                </div>
            </div>

            {a.loading ? (
                <div className="flex items-center justify-center py-20">
                    <Loader2 className="w-8 h-8 text-primary animate-spin" />
                </div>
            ) : (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    {/* Left Column: Chat IA + Calendario Fiscal */}
                    <div className="col-span-1 space-y-4">
                        <AdvisoryChatPanel
                            chatMessages={a.chatMessages}
                            chatInput={a.chatInput}
                            setChatInput={a.setChatInput}
                            chatLoading={a.chatLoading}
                            onSubmit={a.handleChat}
                        />
                        <CalendarSection events={a.events} filter={a.filter} />
                    </div>

                    {/* Right Column: Guías + BOE Feed */}
                    <div className="col-span-1 lg:col-span-2 space-y-8">
                        <GuidesSection
                            guides={a.guides}
                            filter={a.filter}
                            expandedGuide={a.expandedGuide}
                            setExpandedGuide={a.setExpandedGuide}
                        />
                        <NewsFeed
                            news={a.news}
                            filteredNews={a.filteredNews}
                            newsSearch={a.newsSearch}
                            setNewsSearch={a.setNewsSearch}
                        />
                    </div>
                </div>
            )}
        </div>
    );
}
