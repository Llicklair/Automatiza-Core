import Link from "next/link";
import { getTranslations } from "next-intl/server";
import {
    Activity, Calendar, TrendingUp, Video, BookOpen, ArrowRight
} from "lucide-react";
import { PageContainer } from "@/components/shared/PageContainer";

const SECTIONS = [
    {
        href: "/crm/actividades",
        icon: Activity,
        color: "text-pink-400",
        bg: "bg-pink-500/10 border-pink-500/20",
        glow: "group-hover:shadow-pink-500/10",
        key: "actividades",
    },
    {
        href: "/crm/calendario",
        icon: Calendar,
        color: "text-violet-400",
        bg: "bg-violet-500/10 border-violet-500/20",
        glow: "group-hover:shadow-violet-500/10",
        key: "calendario",
    },
    {
        href: "/crm/embudo-de-ventas",
        icon: TrendingUp,
        color: "text-emerald-400",
        bg: "bg-emerald-500/10 border-emerald-500/20",
        glow: "group-hover:shadow-emerald-500/10",
        key: "embudo",
    },
    {
        href: "/crm/reuniones",
        icon: Video,
        color: "text-sky-400",
        bg: "bg-sky-500/10 border-sky-500/20",
        glow: "group-hover:shadow-sky-500/10",
        key: "reuniones",
    },
    {
        href: "/crm/reservas",
        icon: BookOpen,
        color: "text-amber-400",
        bg: "bg-amber-500/10 border-amber-500/20",
        glow: "group-hover:shadow-amber-500/10",
        key: "reservas",
    },
] as const;

export default async function CRMPage() {
    const t = await getTranslations("crm");
    return (
        <PageContainer width="5xl" className="space-y-8">
            {/* Header */}
            <div>
                <div className="flex items-center gap-3 mb-2">
                    <div className="w-10 h-10 rounded-xl bg-pink-500/10 border border-pink-500/20 flex items-center justify-center">
                        <Activity className="w-5 h-5 text-pink-400" />
                    </div>
                    <h1 className="text-3xl font-bold text-foreground tracking-tight">{t("index.title")}</h1>
                </div>
                <p className="text-sm text-muted-foreground ml-[52px]">
                    {t("index.description")}
                </p>
            </div>

            {/* Section cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {SECTIONS.map((s) => (
                    <Link key={s.href} href={s.href} className="group block">
                        <div className={`h-full bg-card border border-border rounded-2xl p-5 flex flex-col gap-4 hover:border-primary/30 transition-all duration-200 hover:shadow-lg ${s.glow}`}>
                            <div className={`w-10 h-10 rounded-xl border ${s.bg} flex items-center justify-center shrink-0`}>
                                <s.icon className={`w-5 h-5 ${s.color}`} />
                            </div>
                            <div className="flex-1">
                                <p className="text-sm font-semibold text-foreground mb-1">{t(`index.sections.${s.key}.title`)}</p>
                                <p className="text-xs text-muted-foreground leading-relaxed">{t(`index.sections.${s.key}.description`)}</p>
                            </div>
                            <div className={`flex items-center gap-1 text-xs font-medium ${s.color} opacity-0 group-hover:opacity-100 transition-opacity`}>
                                {t("index.open")} <ArrowRight className="w-3 h-3" />
                            </div>
                        </div>
                    </Link>
                ))}
            </div>
        </PageContainer>
    );
}
