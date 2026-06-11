import Link from "next/link";
import { getTranslations } from "next-intl/server";
import {
    Users, Wallet, UserPlus, FileText, Brain, ArrowRight, Briefcase, Clock, Timer, Umbrella, Receipt
} from "lucide-react";
import { PageContainer } from "@/components/shared/PageContainer";

// I18N — patrón de referencia para constantes con texto de UI:
// las constantes conservan SOLO la configuración estructural (href, icono,
// colores) y referencian las claves i18n con `titleKey`/`descriptionKey`
// (sin template literals). El componente traduce en render con t(key).
const SECTIONS = [
    {
        href: "/rrhh/empleados",
        icon: Users,
        color: "text-indigo-400",
        bg: "bg-indigo-500/10 border-indigo-500/20",
        glow: "group-hover:shadow-indigo-500/10",
        titleKey: "home.sections.empleados.title",
        descriptionKey: "home.sections.empleados.description",
    },
    {
        href: "/rrhh/nominas",
        icon: Wallet,
        color: "text-emerald-400",
        bg: "bg-emerald-500/10 border-emerald-500/20",
        glow: "group-hover:shadow-emerald-500/10",
        titleKey: "home.sections.nominas.title",
        descriptionKey: "home.sections.nominas.description",
    },
    {
        href: "/rrhh/reclutamiento",
        icon: UserPlus,
        color: "text-sky-400",
        bg: "bg-sky-500/10 border-sky-500/20",
        glow: "group-hover:shadow-sky-500/10",
        titleKey: "home.sections.reclutamiento.title",
        descriptionKey: "home.sections.reclutamiento.description",
    },
    {
        href: "/rrhh/documentos",
        icon: FileText,
        color: "text-amber-400",
        bg: "bg-amber-500/10 border-amber-500/20",
        glow: "group-hover:shadow-amber-500/10",
        titleKey: "home.sections.documentos.title",
        descriptionKey: "home.sections.documentos.description",
    },
    {
        href: "/rrhh/analisis-cv",
        icon: Brain,
        color: "text-pink-400",
        bg: "bg-pink-500/10 border-pink-500/20",
        glow: "group-hover:shadow-pink-500/10",
        titleKey: "home.sections.analisisCv.title",
        descriptionKey: "home.sections.analisisCv.description",
    },
    {
        href: "/rrhh/horarios",
        icon: Clock,
        color: "text-teal-400",
        bg: "bg-teal-500/10 border-teal-500/20",
        glow: "group-hover:shadow-teal-500/10",
        titleKey: "home.sections.horarios.title",
        descriptionKey: "home.sections.horarios.description",
    },
    {
        href: "/rrhh/fichajes",
        icon: Timer,
        color: "text-orange-400",
        bg: "bg-orange-500/10 border-orange-500/20",
        glow: "group-hover:shadow-orange-500/10",
        titleKey: "home.sections.fichajes.title",
        descriptionKey: "home.sections.fichajes.description",
    },
    {
        href: "/rrhh/vacaciones",
        icon: Umbrella,
        color: "text-cyan-400",
        bg: "bg-cyan-500/10 border-cyan-500/20",
        glow: "group-hover:shadow-cyan-500/10",
        titleKey: "home.sections.vacaciones.title",
        descriptionKey: "home.sections.vacaciones.description",
    },
    {
        href: "/rrhh/gastos",
        icon: Receipt,
        color: "text-violet-400",
        bg: "bg-violet-500/10 border-violet-500/20",
        glow: "group-hover:shadow-violet-500/10",
        titleKey: "home.sections.gastos.title",
        descriptionKey: "home.sections.gastos.description",
    },
] as const;

export default async function RRHHPage() {
    const t = await getTranslations("rrhh");
    return (
        <PageContainer width="5xl" className="space-y-8">
            {/* Header */}
            <div>
                <div className="flex items-center gap-3 mb-2">
                    <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center">
                        <Briefcase className="w-5 h-5 text-indigo-400" />
                    </div>
                    <h1 className="text-3xl font-bold text-foreground tracking-tight">{t("home.title")}</h1>
                </div>
                <p className="text-sm text-muted-foreground ml-[52px]">
                    {t("home.subtitle")}
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
                                <p className="text-sm font-semibold text-foreground mb-1">{t(s.titleKey)}</p>
                                <p className="text-xs text-muted-foreground leading-relaxed">{t(s.descriptionKey)}</p>
                            </div>
                            <div className={`flex items-center gap-1 text-xs font-medium ${s.color} opacity-0 group-hover:opacity-100 transition-opacity`}>
                                {t("home.open")} <ArrowRight className="w-3 h-3" />
                            </div>
                        </div>
                    </Link>
                ))}
            </div>
        </PageContainer>
    );
}
