"use client";

import { useState, useEffect } from "react";
import { BarChart3, Loader2 } from "lucide-react";
import {
    emailMarketingApi,
    type EmailCampaign,
} from "@/lib/api/email_marketing";
import { fmt } from "./constants";

// ── Tab: Estadísticas ──────────────────────────────────────────────────────────

export default function TabStats() {
    const [campaigns, setCampaigns] = useState<EmailCampaign[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        emailMarketingApi.campaigns.list()
            .then((data) => setCampaigns(data.filter((c) => c.status === "sent" || c.sent_count > 0)))
            .catch(() => {})
            .finally(() => setLoading(false));
    }, []);

    const totalSent = campaigns.reduce((acc, c) => acc + c.sent_count, 0);
    const totalFailed = campaigns.reduce((acc, c) => acc + c.failed_count, 0);
    const totalRecipients = campaigns.reduce((acc, c) => acc + c.total_count, 0);

    if (loading) return <div className="flex justify-center py-10"><Loader2 className="w-5 h-5 animate-spin text-muted-foreground" /></div>;

    if (campaigns.length === 0) return (
        <div className="flex flex-col items-center py-16 text-center">
            <BarChart3 className="w-8 h-8 text-muted-foreground/30 mb-3" />
            <p className="text-sm text-muted-foreground">Todavía no hay campañas enviadas</p>
        </div>
    );

    return (
        <div className="space-y-6">
            {/* Resumen global */}
            <div className="grid grid-cols-3 gap-4">
                {[
                    { label: "Emails enviados", value: totalSent, color: "text-emerald-400" },
                    { label: "Fallidos", value: totalFailed, color: "text-red-400" },
                    { label: "Tasa de éxito", value: totalRecipients ? `${Math.round((totalSent / totalRecipients) * 100)}%` : "—", color: "text-blue-400" },
                ].map((s) => (
                    <div key={s.label} className="bg-card border border-border rounded-xl p-4 text-center">
                        <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
                        <p className="text-xs text-muted-foreground mt-1">{s.label}</p>
                    </div>
                ))}
            </div>

            {/* Por campaña */}
            <div className="space-y-3">
                {campaigns.map((c) => {
                    const pct = c.total_count ? Math.round((c.sent_count / c.total_count) * 100) : 0;
                    return (
                        <div key={c.id} className="bg-card border border-border rounded-xl p-4 space-y-3">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm font-medium text-foreground">{c.name}</p>
                                    <p className="text-xs text-muted-foreground">{fmt(c.sent_at)}</p>
                                </div>
                                <span className="text-sm font-semibold text-blue-400">{pct}%</span>
                            </div>
                            <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                                <div className="h-full bg-blue-500 rounded-full" style={{ width: `${pct}%` }} />
                            </div>
                            <div className="flex gap-4 text-[11px] text-muted-foreground">
                                <span>{c.total_count} destinatarios</span>
                                <span className="text-emerald-400">{c.sent_count} enviados</span>
                                {c.failed_count > 0 && <span className="text-red-400">{c.failed_count} fallidos</span>}
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
