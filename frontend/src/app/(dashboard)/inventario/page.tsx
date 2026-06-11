import Link from "next/link";
import { Package, ScanLine, ArrowRight, Boxes } from "lucide-react";
import { ValuationWidget } from "./_components/ValuationWidget";
import { PageContainer } from "@/components/shared/PageContainer";

const SECTIONS = [
    {
        href: "/inventario/stock",
        icon: Package,
        color: "text-emerald-400",
        bg: "bg-emerald-500/10 border-emerald-500/20",
        glow: "group-hover:shadow-emerald-500/10",
        title: "Stock",
        description: "Niveles de inventario, movimientos de entrada/salida y alertas de stock mínimo.",
    },
    {
        href: "/inventario/scanner",
        icon: ScanLine,
        color: "text-sky-400",
        bg: "bg-sky-500/10 border-sky-500/20",
        glow: "group-hover:shadow-sky-500/10",
        title: "Escáner",
        description: "Registra entradas y salidas de producto leyendo códigos de barras o QR.",
    },
] as const;

export default function InventarioPage() {
    return (
        <PageContainer width="5xl" className="space-y-8">
            <div>
                <div className="flex items-center gap-3 mb-2">
                    <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
                        <Boxes className="w-5 h-5 text-emerald-400" />
                    </div>
                    <h1 className="text-3xl font-bold text-foreground tracking-tight">Inventario</h1>
                </div>
                <p className="text-sm text-muted-foreground ml-[52px]">
                    Control de stock y registro de movimientos por escáner de código.
                </p>
            </div>

            <ValuationWidget />

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-lg">
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
