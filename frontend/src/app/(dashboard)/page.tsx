"use client";

import { ErrorBoundary } from "@/components/ui/ErrorBoundary";
import { useDashboard } from "./_hooks/useDashboard";
import { AiChatBar } from "./_components/AiChatBar";
import { IntegrationsWidget } from "./_components/IntegrationsWidget";
import { KpiSection } from "./_components/KpiSection";
import { AiInsightsSection } from "./_components/AiInsightsSection";
import { CashflowChart } from "./_components/CashflowChart";
import { RecentInvoicesSection } from "./_components/RecentInvoicesSection";
import { AiActivitySection } from "./_components/AiActivitySection";
import { ApprovalsSection } from "./_components/ApprovalsSection";
import { RrhhWidget } from "./_components/RrhhWidget";

function getGreeting(name: string) {
    const h = new Date().getHours();
    const saludo = h < 14 ? "Buenos días" : h < 21 ? "Buenas tardes" : "Buenas noches";
    return name ? `${saludo}, ${name}` : saludo;
}

export default function DashboardPage() {
    const { tasks, approvals, invoices, summary, analytics, loading, userName, integrations, employees, workingNow } = useDashboard();

    return (
        <ErrorBoundary section="inicio">
        <div className="p-8 max-w-[1400px] mx-auto space-y-8 relative z-0">
            {/* Ambient glow */}
            <div className="pointer-events-none fixed top-0 left-64 w-[600px] h-[400px] opacity-30" style={{ zIndex: -1 }}>
                <div className="absolute top-0 left-0 w-96 h-96 bg-primary/20 rounded-full blur-3xl animate-pulse" />
                <div className="absolute top-16 left-48 w-64 h-64 bg-violet-600/10 rounded-full blur-3xl animate-pulse" style={{ animationDelay: "2s", animationDuration: "4s" }} />
            </div>

            {/* Header */}
            <div className="relative z-10">
                <h1 className="text-3xl font-bold text-foreground tracking-tight">{getGreeting(userName)}</h1>
                <p className="mt-1 text-sm text-muted-foreground">
                    Aquí tienes el resumen financiero y operativo de tu negocio.
                </p>
            </div>

            <AiChatBar />

            <KpiSection loading={loading} summary={summary} />

            {/* Layout Inferior */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Columna Izquierda Ancha */}
                <div className="lg:col-span-2 space-y-6">
                    {!loading && <AiInsightsSection insights={analytics.insights} />}
                    {!loading && <CashflowChart cashflow={analytics.cashflow} />}
                    <RecentInvoicesSection loading={loading} invoices={invoices} />
                </div>

                {/* Columna Derecha Estrecha */}
                <div className="space-y-6">
                    <RrhhWidget loading={loading} employees={employees} working={workingNow} />
                    <AiActivitySection loading={loading} tasks={tasks} />
                    <ApprovalsSection loading={loading} approvals={approvals} />
                    <IntegrationsWidget {...integrations} />
                </div>
            </div>
        </div>
        </ErrorBoundary>
    );
}
