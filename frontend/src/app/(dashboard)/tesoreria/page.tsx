import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { TrendingUp, ArrowLeftRight, Send, ArrowRight, Landmark } from "lucide-react";
import { PageContainer } from "@/components/shared/PageContainer";

const sections = (t: Awaited<ReturnType<typeof getTranslations>>) => [
    {
        href: "/tesoreria/cashflow",
        icon: TrendingUp,
        color: "text-emerald-400",
        bg: "bg-emerald-500/10 border-emerald-500/20",
        glow: "group-hover:shadow-emerald-500/10",
        title: t("sections.cashflowTitle"),
        description: t("sections.cashflowDescription"),
    },
    {
        href: "/tesoreria/pagos-y-cobros",
        icon: ArrowLeftRight,
        color: "text-sky-400",
        bg: "bg-sky-500/10 border-sky-500/20",
        glow: "group-hover:shadow-sky-500/10",
        title: t("sections.paymentsTitle"),
        description: t("sections.paymentsDescription"),
    },
    {
        href: "/tesoreria/remesas",
        icon: Send,
        color: "text-violet-400",
        bg: "bg-violet-500/10 border-violet-500/20",
        glow: "group-hover:shadow-violet-500/10",
        title: t("sections.remittancesTitle"),
        description: t("sections.remittancesDescription"),
    },
] as const;

export default async function TesoreriaPage() {
    const t = await getTranslations("tesoreria");
    const SECTIONS = sections(t);
    return (
        <PageContainer width="5xl" className="space-y-8">
            <div>
                <div className="flex items-center gap-3 mb-2">
                    <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
                        <Landmark className="w-5 h-5 text-emerald-400" />
                    </div>
                    <h1 className="text-3xl font-bold text-foreground tracking-tight">{t("index.title")}</h1>
                </div>
                <p className="text-sm text-muted-foreground ml-[52px]">
                    {t("index.subtitle")}
                </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                {SECTIONS.map((s) => (
                    <Link key={s.href} href={s.href} className="group block">
                        <div className={`h-full bg-card border border-border rounded-2xl p-5 flex flex-col gap-4 hover:border-primary/30 transition-all duration-200 hover:shadow-lg ${s.glow}`}>
                            <div className={`w-10 h-10 rounded-xl border ${s.bg} flex items-center justify-center shrink-0`}>
                                <s.icon className={`w-5 h-5 ${s.color}`} />
                            </div>
                            <div className="flex-1">
                                <p className="text-sm font-semibold text-foreground mb-1">{s.title}</p>
                                <p className="text-xs text-muted-foreground leading-relaxed">{s.description}</p>
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
