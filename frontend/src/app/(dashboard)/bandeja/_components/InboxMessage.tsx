import { useTranslations } from "next-intl";
import type { AIEmployee, ActivityEntry } from "@/lib/api/ai_employees";

type CategoryEntry = { icon: string; color: string; label: string };

export const buildCategoryConfig = (
    t: (key: string) => string,
): Record<string, CategoryEntry> => ({
    billing:    { icon: "💰", color: "bg-amber-500/10 border-amber-500/20 text-amber-400",   label: t("categories.billing") },
    hr:         { icon: "👥", color: "bg-blue-500/10 border-blue-500/20 text-blue-400",       label: t("categories.hr") },
    crm:        { icon: "🤝", color: "bg-violet-500/10 border-violet-500/20 text-violet-400", label: t("categories.crm") },
    email:      { icon: "📧", color: "bg-sky-500/10 border-sky-500/20 text-sky-400",          label: t("categories.email") },
    banking:    { icon: "🏦", color: "bg-emerald-500/10 border-emerald-500/20 text-emerald-400", label: t("categories.banking") },
    compliance: { icon: "⚖️", color: "bg-orange-500/10 border-orange-500/20 text-orange-400", label: t("categories.compliance") },
    documents:  { icon: "📄", color: "bg-muted border-border text-muted-foreground",       label: t("categories.documents") },
    system:     { icon: "⚙️", color: "bg-muted border-border text-muted-foreground",       label: t("categories.system") },
});

export function timeAgo(
    dateStr: string,
    t: (key: string, values?: Record<string, string | number>) => string,
): string {
    const diff = Date.now() - new Date(dateStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return t("time.now");
    if (mins < 60) return t("time.minutesAgo", { mins });
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return t("time.hoursAgo", { hrs });
    return new Date(dateStr).toLocaleDateString("es-ES", { day: "numeric", month: "short" });
}

export function InboxMessage({ entry, employee }: { entry: ActivityEntry; employee?: AIEmployee }) {
    const t = useTranslations("bandeja");
    const categoryConfig = buildCategoryConfig(t);
    const cat = categoryConfig[entry.category] ?? categoryConfig.system;

    return (
        <div className="flex gap-3 py-4 px-1 border-b border-border last:border-0 hover:bg-card rounded-lg transition-colors -mx-1 px-2">
            {/* Avatar agente */}
            <div className="w-9 h-9 rounded-full bg-violet-500/10 border border-violet-500/20 flex items-center justify-center text-base shrink-0 mt-0.5">
                {entry.icon || cat.icon}
            </div>

            <div className="flex-1 min-w-0 space-y-1">
                {/* Cabecera */}
                <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 min-w-0">
                        <span className="text-sm font-medium text-foreground truncate">
                            {employee?.name ?? t("inbox.aiAgent")}
                        </span>
                        <span className={`shrink-0 text-[10px] px-1.5 py-0.5 rounded border font-medium ${cat.color}`}>
                            {cat.label}
                        </span>
                    </div>
                    <span className="text-[10px] text-muted-foreground/60 shrink-0">{timeAgo(entry.created_at, t)}</span>
                </div>

                {/* Mensaje */}
                <p className="text-sm text-foreground leading-relaxed">{entry.message}</p>

                {/* Metadata si existe */}
                {entry.metadata && Object.keys(entry.metadata).length > 0 && (
                    <div className="flex flex-wrap gap-2 pt-1">
                        {Object.entries(entry.metadata).slice(0, 4).map(([k, v]) => (
                            <span key={k} className="text-[10px] text-muted-foreground/60">
                                <span className="text-muted-foreground">{k.replace(/_/g, " ")}:</span>{" "}
                                <span className="text-muted-foreground">{String(v).slice(0, 50)}</span>
                            </span>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
