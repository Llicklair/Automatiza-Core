import Link from "next/link";
import {
    BookOpen, BarChart2, Scale, Grid3x3, TrendingDown, Package, ArrowRight, Calculator
} from "lucide-react";
import { PageContainer } from "@/components/shared/PageContainer";

const SECTIONS = [
    {
        href: "/contabilidad/libro-diario",
        icon: BookOpen,
        color: "text-indigo-400",
        bg: "bg-indigo-500/10 border-indigo-500/20",
        glow: "group-hover:shadow-indigo-500/10",
        title: "Libro Diario",
        description: "Registro cronológico de todos los asientos contables de la empresa.",
    },
    {
        href: "/contabilidad/perdidas-y-ganancias",
        icon: BarChart2,
        color: "text-emerald-400",
        bg: "bg-emerald-500/10 border-emerald-500/20",
        glow: "group-hover:shadow-emerald-500/10",
        title: "Pérdidas y Ganancias",
        description: "Cuenta de resultados: ingresos, gastos y beneficio del ejercicio.",
    },
    {
        href: "/contabilidad/balance-de-situacion",
        icon: Scale,
        color: "text-sky-400",
        bg: "bg-sky-500/10 border-sky-500/20",
        glow: "group-hover:shadow-sky-500/10",
        title: "Balance de Situación",
        description: "Activo, pasivo y patrimonio neto en un momento determinado.",
    },
    {
        href: "/contabilidad/cuadro-de-cuentas",
        icon: Grid3x3,
        color: "text-violet-400",
        bg: "bg-violet-500/10 border-violet-500/20",
        glow: "group-hover:shadow-violet-500/10",
        title: "Cuadro de Cuentas",
        description: "Plan General Contable con el árbol de cuentas y sus saldos.",
    },
    {
        href: "/contabilidad/activos",
        icon: Package,
        color: "text-amber-400",
        bg: "bg-amber-500/10 border-amber-500/20",
        glow: "group-hover:shadow-amber-500/10",
        title: "Activos Fijos",
        description: "Inmovilizado material e inmaterial, amortizaciones y valor neto contable.",
    },
    {
        href: "/contabilidad/asesorias",
        icon: TrendingDown,
        color: "text-pink-400",
        bg: "bg-pink-500/10 border-pink-500/20",
        glow: "group-hover:shadow-pink-500/10",
        title: "Asesorías",
        description: "Comunicación y envío de documentación a tu gestor o asesor fiscal.",
    },
] as const;

export default function ContabilidadPage() {
    return (
        <PageContainer width="5xl" className="space-y-8">
            <div>
                <div className="flex items-center gap-3 mb-2">
                    <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center">
                        <Calculator className="w-5 h-5 text-indigo-400" />
                    </div>
                    <h1 className="text-3xl font-bold text-foreground tracking-tight">Contabilidad</h1>
                </div>
                <p className="text-sm text-muted-foreground ml-[52px]">
                    Asientos contables, estados financieros y cuadro de cuentas del ejercicio.
                </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
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
                                Abrir <ArrowRight className="w-3 h-3" />
                            </div>
                        </div>
                    </Link>
                ))}
            </div>
        </PageContainer>
    );
}
