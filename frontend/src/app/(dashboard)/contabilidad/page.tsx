import Link from "next/link";
import { getTranslations } from "next-intl/server";
import {
    BookOpen, BarChart2, Scale, Grid3x3, TrendingDown, Package, ArrowRight, Calculator
} from "lucide-react";
import { PageContainer } from "@/components/shared/PageContainer";

type Translator = Awaited<ReturnType<typeof getTranslations>>;

const buildSections = (t: Translator) => [
    {
        href: "/contabilidad/libro-diario",
        icon: BookOpen,
        color: "text-indigo-400",
        bg: "bg-indigo-500/10 border-indigo-500/20",
        glow: "group-hover:shadow-indigo-500/10",
        title: t("sections.libroDiarioTitle"),
        description: t("sections.libroDiarioDescription"),
    },
    {
        href: "/contabilidad/perdidas-y-ganancias",
        icon: BarChart2,
        color: "text-emerald-400",
        bg: "bg-emerald-500/10 border-emerald-500/20",
        glow: "group-hover:shadow-emerald-500/10",
        title: t("sections.perdidasGananciasTitle"),
        description: t("sections.perdidasGananciasDescription"),
    },
    {
        href: "/contabilidad/balance-de-situacion",
        icon: Scale,
        color: "text-sky-400",
        bg: "bg-sky-500/10 border-sky-500/20",
        glow: "group-hover:shadow-sky-500/10",
        title: t("sections.balanceSituacionTitle"),
        description: t("sections.balanceSituacionDescription"),
    },
    {
        href: "/contabilidad/cuadro-de-cuentas",
        icon: Grid3x3,
        color: "text-violet-400",
        bg: "bg-violet-500/10 border-violet-500/20",
        glow: "group-hover:shadow-violet-500/10",
        title: t("sections.cuadroCuentasTitle"),
        description: t("sections.cuadroCuentasDescription"),
    },
    {
        href: "/contabilidad/activos",
        icon: Package,
        color: "text-amber-400",
        bg: "bg-amber-500/10 border-amber-500/20",
        glow: "group-hover:shadow-amber-500/10",
        title: t("sections.activosFijosTitle"),
        description: t("sections.activosFijosDescription"),
    },
    {
        href: "/contabilidad/asesorias",
        icon: TrendingDown,
        color: "text-pink-400",
        bg: "bg-pink-500/10 border-pink-500/20",
        glow: "group-hover:shadow-pink-500/10",
        title: t("sections.asesoriasTitle"),
        description: t("sections.asesoriasDescription"),
    },
] as const;

export default async function ContabilidadPage() {
    const t = await getTranslations("contabilidad");
    const sections = buildSections(t);
    return (
        <PageContainer width="5xl" className="space-y-8">
            <div>
                <div className="flex items-center gap-3 mb-2">
                    <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center">
                        <Calculator className="w-5 h-5 text-indigo-400" />
                    </div>
                    <h1 className="text-3xl font-bold text-foreground tracking-tight">{t("page.title")}</h1>
                </div>
                <p className="text-sm text-muted-foreground ml-[52px]">
                    {t("page.subtitle")}
                </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {sections.map((s) => (
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
                                Abrir <ArrowRight className="w-3 h-3" />
                            </div>
                        </div>
                    </Link>
                ))}
            </div>
        </PageContainer>
    );
}
