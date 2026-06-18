"use client";

import { Clock, ArrowRight, BrainCircuit, Sparkles } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { StatusBadge } from "./DashboardBadges";
import type { Task } from "@/lib/api";

interface AiActivitySectionProps {
    loading: boolean;
    tasks: Task[];
}

export function AiActivitySection({ loading, tasks }: AiActivitySectionProps) {
    const t = useTranslations("dashboard");
    return (
        <div className="bg-card border border-primary/20 rounded-2xl overflow-hidden shadow-lg shadow-primary/20">
            <div className="px-5 py-4 border-b border-primary/20 bg-gradient-to-r from-indigo-500/15 to-transparent flex items-center justify-between">
                <h2 className="text-sm font-semibold text-primary flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-primary" /> {t("aiActivity.title")}
                </h2>
                <Link href="/mi-equipo?tab=tareas" className="text-[11px] text-primary hover:text-primary font-medium transition-colors flex items-center gap-1">
                    {t("aiActivity.viewAll")} <ArrowRight className="w-3 h-3" />
                </Link>
            </div>
            <div className="divide-y divide-border max-h-[280px] overflow-y-auto">
                {loading ? (
                    <div className="p-6 text-center text-primary/50 text-xs">{t("aiActivity.loading")}</div>
                ) : tasks.length === 0 ? (
                    <div className="p-8 text-center flex flex-col items-center gap-2">
                        <BrainCircuit className="w-8 h-8 text-muted-foreground" />
                        <p className="text-xs text-muted-foreground">{t("aiActivity.emptyLine1")}<br />{t("aiActivity.emptyLine2")}</p>
                    </div>
                ) : (
                    tasks.map(task => (
                        <div key={task.id} className="p-4 flex flex-col gap-2 hover:bg-primary/5 transition-colors">
                            <div className="flex items-start justify-between gap-3">
                                <p className="text-xs text-foreground line-clamp-2 leading-relaxed">{task.user_intent}</p>
                                <StatusBadge status={task.status} />
                            </div>
                            <div className="flex items-center gap-2 text-[10px] text-muted-foreground font-mono">
                                <Clock className="w-3 h-3" />
                                {new Date(task.created_at).toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" })}
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}
