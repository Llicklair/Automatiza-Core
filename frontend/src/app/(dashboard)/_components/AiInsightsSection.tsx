"use client";

import { ArrowRight, TrendingUp, BrainCircuit, Sparkles, AlertTriangle, Lightbulb } from "lucide-react";
import Link from "next/link";

interface Insight {
    id: string | number;
    type: string;
    title: string;
    message: string;
    action_url: string;
    action_text: string;
}

interface AiInsightsSectionProps {
    insights: Insight[];
}

export function AiInsightsSection({ insights }: AiInsightsSectionProps) {
    if (insights.length === 0) return null;

    return (
        <div className="bg-card border border-primary/20 rounded-2xl overflow-hidden shadow-lg shadow-primary/20 relative">
            <div className="absolute top-0 right-0 p-4 opacity-10 blur-xl pointer-events-none">
                <BrainCircuit className="w-48 h-48 text-primary" />
            </div>
            <div className="px-6 py-5 border-b border-primary/20 flex items-center justify-between relative z-10 bg-gradient-to-r from-indigo-500/10 to-transparent">
                <h2 className="text-base font-semibold text-foreground flex items-center gap-2">
                    <Sparkles className="w-5 h-5 text-primary" /> Sugerencias Estratégicas IA
                </h2>
            </div>
            <div className="p-6 relative z-10 grid grid-cols-1 md:grid-cols-3 gap-4">
                {insights.map((insight) => {
                    let icon = <Lightbulb className="w-4 h-4 text-primary" />;
                    let bg = "bg-primary/5 border-primary/20 hover:bg-primary/10 hover:border-primary/20";
                    let titleC = "text-primary";
                    if (insight.type === 'warning') {
                        icon = <AlertTriangle className="w-4 h-4 text-amber-400" />;
                        bg = "bg-amber-500/5 border-amber-500/10 hover:bg-amber-500/10 hover:border-amber-500/20";
                        titleC = "text-amber-300";
                    } else if (insight.type === 'success') {
                        icon = <TrendingUp className="w-4 h-4 text-emerald-400" />;
                        bg = "bg-emerald-500/5 border-emerald-500/10 hover:bg-emerald-500/10 hover:border-emerald-500/20";
                        titleC = "text-emerald-300";
                    }
                    return (
                        <div key={insight.id} className={`rounded-xl border ${bg} p-5 flex flex-col justify-between transition-all duration-300 cursor-default group`}>
                            <div>
                                <div className="flex items-center gap-2 mb-3">
                                    {icon}
                                    <h4 className={`text-sm font-semibold ${titleC}`}>{insight.title}</h4>
                                </div>
                                <p className="text-xs text-muted-foreground leading-relaxed mb-4">{insight.message}</p>
                            </div>
                            <Link href={insight.action_url} className="text-xs font-medium text-foreground opacity-60 group-hover:opacity-100 group-hover:underline transition-opacity flex items-center gap-1">
                                {insight.action_text} <ArrowRight className="w-3 h-3" />
                            </Link>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
