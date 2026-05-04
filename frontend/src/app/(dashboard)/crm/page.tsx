import Link from "next/link";
import {
    Activity, Calendar, TrendingUp, Video, BookOpen, ArrowRight
} from "lucide-react";

const SECTIONS = [
    {
        href: "/crm/actividades",
        icon: Activity,
        color: "text-pink-400",
        bg: "bg-pink-500/10 border-pink-500/20",
        glow: "group-hover:shadow-pink-500/10",
        title: "Actividades",
        description: "Muro de interacciones: llamadas, emails y resúmenes generados por IA.",
    },
    {
        href: "/crm/calendario",
        icon: Calendar,
        color: "text-violet-400",
        bg: "bg-violet-500/10 border-violet-500/20",
        glow: "group-hover:shadow-violet-500/10",
        title: "Calendario",
        description: "Vista mensual de eventos, citas y tareas programadas con clientes.",
    },
    {
        href: "/crm/embudo-de-ventas",
        icon: TrendingUp,
        color: "text-emerald-400",
        bg: "bg-emerald-500/10 border-emerald-500/20",
        glow: "group-hover:shadow-emerald-500/10",
        title: "Embudo de Ventas",
        description: "Pipeline kanban para mover oportunidades por las fases de cierre.",
    },
    {
        href: "/crm/reuniones",
        icon: Video,
        color: "text-sky-400",
        bg: "bg-sky-500/10 border-sky-500/20",
        glow: "group-hover:shadow-sky-500/10",
        title: "Reuniones",
        description: "Agenda y actas de reuniones con clientes y prospectos.",
    },
    {
        href: "/crm/reservas",
        icon: BookOpen,
        color: "text-amber-400",
        bg: "bg-amber-500/10 border-amber-500/20",
        glow: "group-hover:shadow-amber-500/10",
        title: "Reservas",
        description: "Gestiona citas y reservas de servicios con tus contactos.",
    },
] as const;

export default function CRMPage() {
    return (
        <div className="p-8 max-w-5xl mx-auto space-y-8">
            {/* Header */}
            <div>
                <div className="flex items-center gap-3 mb-2">
                    <div className="w-10 h-10 rounded-xl bg-pink-500/10 border border-pink-500/20 flex items-center justify-center">
                        <Activity className="w-5 h-5 text-pink-400" />
                    </div>
                    <h1 className="text-3xl font-bold text-foreground tracking-tight">CRM</h1>
                </div>
                <p className="text-sm text-muted-foreground ml-[52px]">
                    Gestión de relaciones con clientes — actividades, pipeline y agenda comercial.
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
        </div>
    );
}
