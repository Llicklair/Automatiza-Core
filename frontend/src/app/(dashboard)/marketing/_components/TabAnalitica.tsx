"use client";

import { useState, useEffect, useCallback } from "react";
import { useTranslations } from "next-intl";
import {
    BarChart3, Loader2, Eye, Users, Heart, MessageCircle, Share2, MousePointerClick,
} from "lucide-react";
import { marketingApi, Campaign, CampaignMetrics } from "@/lib/api/marketing";
import { logError } from "@/lib/logger";

const METRIC_CARDS = [
    { key: "impressions", labelKey: "metricImpressions", icon: Eye,                color: "text-blue-400" },
    { key: "reach",       labelKey: "metricReach",       icon: Users,             color: "text-cyan-400" },
    { key: "likes",       labelKey: "metricLikes",       icon: Heart,             color: "text-pink-400" },
    { key: "comments",    labelKey: "metricComments",    icon: MessageCircle,     color: "text-violet-400" },
    { key: "shares",      labelKey: "metricShares",      icon: Share2,            color: "text-emerald-400" },
    { key: "clicks",      labelKey: "metricClicks",      icon: MousePointerClick, color: "text-amber-400" },
] as const;

// ── Tab: Analítica ───────────────────────────────────────────────────────────────

export function TabAnalitica() {
    const t = useTranslations("marketing.analitica");
    const [campaigns, setCampaigns] = useState<Campaign[]>([]);
    const [selected, setSelected] = useState<string>("");
    const [metrics, setMetrics] = useState<CampaignMetrics | null>(null);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        marketingApi.campaigns.list()
            .then((data) => {
                setCampaigns(data);
                if (data.length) setSelected(data[0].id);
            })
            .catch((err) => logError("marketing/analitica/campaigns", err));
    }, []);

    const loadMetrics = useCallback(async (campaignId: string) => {
        if (!campaignId) return;
        setLoading(true);
        try {
            setMetrics(await marketingApi.campaigns.metrics(campaignId));
        } catch (err) {
            logError("marketing/analitica/metrics", err);
            setMetrics(null);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { loadMetrics(selected); }, [selected, loadMetrics]);

    const fmtNum = (n: number) => n.toLocaleString("es-ES");

    if (!campaigns.length) {
        return (
            <div className="flex flex-col items-center justify-center py-16 text-center">
                <BarChart3 className="w-10 h-10 text-muted-foreground/40 mb-3" />
                <p className="text-sm text-muted-foreground">{t("noCampaigns")}</p>
                <p className="text-xs text-muted-foreground/70">
                    {t("noCampaignsHint")}
                </p>
            </div>
        );
    }

    return (
        <div className="space-y-5">
            {/* Selector de campaña */}
            <div className="flex items-center gap-3">
                <label className="text-xs text-muted-foreground">{t("campaignLabel")}</label>
                <select
                    value={selected}
                    onChange={(e) => setSelected(e.target.value)}
                    className="text-sm bg-background border border-border rounded-lg px-3 py-1.5 text-foreground focus:outline-none focus:border-pink-500"
                >
                    {campaigns.map((c) => (
                        <option key={c.id} value={c.id}>{c.name}</option>
                    ))}
                </select>
            </div>

            {loading && (
                <div className="flex justify-center py-12">
                    <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
                </div>
            )}

            {!loading && metrics && (
                <>
                    {/* Tarjetas de totales */}
                    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
                        {METRIC_CARDS.map(({ key, labelKey, icon: Icon, color }) => (
                            <div key={key} className="rounded-xl border border-border bg-card p-3">
                                <Icon className={`w-4 h-4 ${color} mb-2`} />
                                <div className="text-lg font-semibold text-foreground">
                                    {fmtNum(metrics.totals[key])}
                                </div>
                                <div className="text-[11px] text-muted-foreground">{t(labelKey)}</div>
                            </div>
                        ))}
                    </div>

                    {/* Detalle por post */}
                    {metrics.posts.length === 0 ? (
                        <p className="text-sm text-muted-foreground text-center py-8">
                            {t("noPostsMetrics")}
                        </p>
                    ) : (
                        <div className="overflow-x-auto rounded-xl border border-border">
                            <table className="w-full text-sm">
                                <thead>
                                    <tr className="border-b border-border text-left text-xs text-muted-foreground">
                                        <th className="px-3 py-2 font-medium">{t("colNetwork")}</th>
                                        <th className="px-3 py-2 font-medium">{t("colStatus")}</th>
                                        <th className="px-3 py-2 font-medium text-right">{t("colImpressions")}</th>
                                        <th className="px-3 py-2 font-medium text-right">{t("colReach")}</th>
                                        <th className="px-3 py-2 font-medium text-right">{t("colLikes")}</th>
                                        <th className="px-3 py-2 font-medium text-right">{t("colComments")}</th>
                                        <th className="px-3 py-2 font-medium text-right">{t("colShares")}</th>
                                        <th className="px-3 py-2 font-medium text-right">{t("colDate")}</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {metrics.posts.map((p) => (
                                        <tr key={p.post_id} className="border-b border-border/50 last:border-0">
                                            <td className="px-3 py-2 capitalize text-foreground">{p.platform}</td>
                                            <td className="px-3 py-2 text-muted-foreground">{p.status}</td>
                                            <td className="px-3 py-2 text-right text-foreground">{fmtNum(p.impressions)}</td>
                                            <td className="px-3 py-2 text-right text-foreground">{fmtNum(p.reach)}</td>
                                            <td className="px-3 py-2 text-right text-foreground">{fmtNum(p.likes)}</td>
                                            <td className="px-3 py-2 text-right text-foreground">{fmtNum(p.comments)}</td>
                                            <td className="px-3 py-2 text-right text-foreground">{fmtNum(p.shares)}</td>
                                            <td className="px-3 py-2 text-right text-muted-foreground">{p.metric_date ?? "—"}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </>
            )}
        </div>
    );
}
