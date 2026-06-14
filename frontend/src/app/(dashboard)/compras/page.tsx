import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { FileText, ShoppingCart, Building2, ArrowRight, PackageOpen } from "lucide-react";
import { PageContainer } from "@/components/shared/PageContainer";

const SECTIONS = [
    {
        href: "/compras/facturas",
        icon: FileText,
        color: "text-rose-400",
        bg: "bg-rose-500/10 border-rose-500/20",
        glow: "group-hover:shadow-rose-500/10",
        titleKey: "index.sections.facturas.title",
        descriptionKey: "index.sections.facturas.description",
    },
    {
        href: "/compras/pedidos",
        icon: ShoppingCart,
        color: "text-amber-400",
        bg: "bg-amber-500/10 border-amber-500/20",
        glow: "group-hover:shadow-amber-500/10",
        titleKey: "index.sections.pedidos.title",
        descriptionKey: "index.sections.pedidos.description",
    },
    {
        href: "/compras/proveedores",
        icon: Building2,
        color: "text-sky-400",
        bg: "bg-sky-500/10 border-sky-500/20",
        glow: "group-hover:shadow-sky-500/10",
        titleKey: "index.sections.proveedores.title",
        descriptionKey: "index.sections.proveedores.description",
    },
] as const;

export default async function ComprasPage() {
    const t = await getTranslations("compras");
    return (
        <PageContainer width="5xl" className="space-y-8">
            <div>
                <div className="flex items-center gap-3 mb-2">
                    <div className="w-10 h-10 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center">
                        <PackageOpen className="w-5 h-5 text-rose-400" />
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
                                <p className="text-sm font-semibold text-foreground mb-1">{t(s.titleKey)}</p>
                                <p className="text-xs text-muted-foreground leading-relaxed">{t(s.descriptionKey)}</p>
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
