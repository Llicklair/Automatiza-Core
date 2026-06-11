import Link from "next/link";
import {
    Users, Wallet, UserPlus, FileText, Brain, ArrowRight, Briefcase, Clock, Timer, Umbrella, Receipt
} from "lucide-react";
import { PageContainer } from "@/components/shared/PageContainer";

const SECTIONS = [
    {
        href: "/rrhh/empleados",
        icon: Users,
        color: "text-indigo-400",
        bg: "bg-indigo-500/10 border-indigo-500/20",
        glow: "group-hover:shadow-indigo-500/10",
        title: "Empleados",
        description: "Directorio de plantilla, roles, salarios y contratos. Base para el agente de nóminas.",
    },
    {
        href: "/rrhh/nominas",
        icon: Wallet,
        color: "text-emerald-400",
        bg: "bg-emerald-500/10 border-emerald-500/20",
        glow: "group-hover:shadow-emerald-500/10",
        title: "Nóminas",
        description: "Pre-cálculo y aprobación de nóminas mensuales generadas por el agente IA.",
    },
    {
        href: "/rrhh/reclutamiento",
        icon: UserPlus,
        color: "text-sky-400",
        bg: "bg-sky-500/10 border-sky-500/20",
        glow: "group-hover:shadow-sky-500/10",
        title: "Reclutamiento",
        description: "Pipeline de candidatos y fases del proceso de selección.",
    },
    {
        href: "/rrhh/documentos",
        icon: FileText,
        color: "text-amber-400",
        bg: "bg-amber-500/10 border-amber-500/20",
        glow: "group-hover:shadow-amber-500/10",
        title: "Documentos",
        description: "Contratos, nóminas firmadas y archivos del trabajador centralizados.",
    },
    {
        href: "/rrhh/analisis-cv",
        icon: Brain,
        color: "text-pink-400",
        bg: "bg-pink-500/10 border-pink-500/20",
        glow: "group-hover:shadow-pink-500/10",
        title: "Análisis de CV",
        description: "El agente IA extrae y puntúa candidaturas automáticamente desde PDF.",
    },
    {
        href: "/rrhh/horarios",
        icon: Clock,
        color: "text-teal-400",
        bg: "bg-teal-500/10 border-teal-500/20",
        glow: "group-hover:shadow-teal-500/10",
        title: "Horarios",
        description: "Plantilla semanal fija por empleado: hora de entrada y salida por día.",
    },
    {
        href: "/rrhh/fichajes",
        icon: Timer,
        color: "text-orange-400",
        bg: "bg-orange-500/10 border-orange-500/20",
        glow: "group-hover:shadow-orange-500/10",
        title: "Fichajes",
        description: "Control de presencia en tiempo real: quién está trabajando ahora mismo.",
    },
    {
        href: "/rrhh/vacaciones",
        icon: Umbrella,
        color: "text-cyan-400",
        bg: "bg-cyan-500/10 border-cyan-500/20",
        glow: "group-hover:shadow-cyan-500/10",
        title: "Vacaciones",
        description: "Solicitudes de ausencia: vacaciones, bajas y excedencias con flujo de aprobación.",
    },
    {
        href: "/rrhh/gastos",
        icon: Receipt,
        color: "text-violet-400",
        bg: "bg-violet-500/10 border-violet-500/20",
        glow: "group-hover:shadow-violet-500/10",
        title: "Gastos",
        description: "Gestión de dietas y gastos: el empleado envía el justificante y el admin aprueba y reembolsa.",
    },
] as const;

export default function RRHHPage() {
    return (
        <PageContainer width="5xl" className="space-y-8">
            {/* Header */}
            <div>
                <div className="flex items-center gap-3 mb-2">
                    <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center">
                        <Briefcase className="w-5 h-5 text-indigo-400" />
                    </div>
                    <h1 className="text-3xl font-bold text-foreground tracking-tight">Recursos Humanos</h1>
                </div>
                <p className="text-sm text-muted-foreground ml-[52px]">
                    Gestión de plantilla, nóminas automatizadas y selección de personal asistida por IA.
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
