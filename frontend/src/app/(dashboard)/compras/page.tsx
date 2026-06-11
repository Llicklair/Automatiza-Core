import Link from "next/link";
import { FileText, ShoppingCart, Building2, ArrowRight, PackageOpen } from "lucide-react";
import { PageContainer } from "@/components/shared/PageContainer";

const SECTIONS = [
    {
        href: "/compras/facturas",
        icon: FileText,
        color: "text-rose-400",
        bg: "bg-rose-500/10 border-rose-500/20",
        glow: "group-hover:shadow-rose-500/10",
        title: "Facturas Recibidas",
        description: "Registro y gestión de facturas de proveedores. Concilia con tus pagos bancarios.",
    },
    {
        href: "/compras/pedidos",
        icon: ShoppingCart,
        color: "text-amber-400",
        bg: "bg-amber-500/10 border-amber-500/20",
        glow: "group-hover:shadow-amber-500/10",
        title: "Pedidos de Compra",
        description: "Órdenes de compra enviadas a proveedores y su estado de recepción.",
    },
    {
        href: "/compras/proveedores",
        icon: Building2,
        color: "text-sky-400",
        bg: "bg-sky-500/10 border-sky-500/20",
        glow: "group-hover:shadow-sky-500/10",
        title: "Proveedores",
        description: "Directorio de proveedores con condiciones de pago, NIF y historial de compras.",
    },
] as const;

export default function ComprasPage() {
    return (
        <PageContainer width="5xl" className="space-y-8">
            <div>
                <div className="flex items-center gap-3 mb-2">
                    <div className="w-10 h-10 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center">
                        <PackageOpen className="w-5 h-5 text-rose-400" />
                    </div>
                    <h1 className="text-3xl font-bold text-foreground tracking-tight">Compras</h1>
                </div>
                <p className="text-sm text-muted-foreground ml-[52px]">
                    Facturas recibidas, pedidos a proveedores y directorio de suministradores.
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
                                Abrir <ArrowRight className="w-3 h-3" />
                            </div>
                        </div>
                    </Link>
                ))}
            </div>
        </PageContainer>
    );
}
