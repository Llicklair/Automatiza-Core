import {
    Wallet, ArrowUpRight, ArrowDownRight, AlertTriangle, TrendingUp,
} from "lucide-react";
import { format } from "date-fns";
import { es } from "date-fns/locale";
import { getTranslations } from "next-intl/server";
import { cn } from "@/lib/utils";
import type { BankTransaction } from "@/lib/api";

const fmt = (v: number) =>
    new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" }).format(v);

interface KpiCardsProps {
    loading: boolean;
    saldoCaja: number;
    ultimaTx: BankTransaction | undefined;
    totalCobros: number;
    cobrosCount: number;
    totalPagos: number;
    pagosCount: number;
    overdueCount: number;
    saldoNeto: number;
}

export default async function KpiCards({
    loading, saldoCaja, ultimaTx, totalCobros, cobrosCount,
    totalPagos, pagosCount, overdueCount, saldoNeto,
}: KpiCardsProps) {
    const t = await getTranslations("tesoreria");
    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Saldo caja */}
            <div className="bg-card border border-border p-5 rounded-2xl relative overflow-hidden">
                <div className="flex items-center gap-3 mb-3">
                    <div className="w-9 h-9 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center">
                        <Wallet className="w-4 h-4 text-blue-400" />
                    </div>
                    <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">{t("kpiCards.cajaActual")}</span>
                </div>
                <p className={cn("text-2xl font-bold tracking-tight", saldoCaja >= 0 ? "text-foreground" : "text-red-400")}>
                    {loading ? "—" : fmt(saldoCaja)}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                    {ultimaTx ? t("kpiCards.ultimoMov", { fecha: format(new Date(ultimaTx.date), "d MMM", { locale: es }) }) : t("kpiCards.sinMovimientos")}
                </p>
            </div>

            {/* Cobros pendientes */}
            <div className="bg-card border border-border p-5 rounded-2xl">
                <div className="flex items-center gap-3 mb-3">
                    <div className="w-9 h-9 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
                        <ArrowUpRight className="w-4 h-4 text-emerald-400" />
                    </div>
                    <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">{t("kpiCards.porCobrar")}</span>
                </div>
                <p className="text-2xl font-bold text-emerald-400 tracking-tight">
                    {loading ? "—" : fmt(totalCobros)}
                </p>
                <p className="text-xs text-muted-foreground mt-1">{t("kpiCards.facturasEmitidas", { count: cobrosCount })}</p>
            </div>

            {/* Pagos pendientes */}
            <div className="bg-card border border-border p-5 rounded-2xl">
                <div className="flex items-center gap-3 mb-3">
                    <div className="w-9 h-9 rounded-xl bg-red-500/10 border border-red-500/20 flex items-center justify-center">
                        <ArrowDownRight className="w-4 h-4 text-red-400" />
                    </div>
                    <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">{t("kpiCards.porPagar")}</span>
                </div>
                <p className="text-2xl font-bold text-red-400 tracking-tight">
                    {loading ? "—" : fmt(totalPagos)}
                </p>
                <p className="text-xs text-muted-foreground mt-1">{t("kpiCards.facturasRecibidas", { count: pagosCount })}</p>
            </div>

            {/* Neto / alerta vencidos */}
            <div className={cn("p-5 rounded-2xl border", overdueCount > 0 ? "bg-red-500/5 border-red-500/20" : "bg-card border-border")}>
                <div className="flex items-center gap-3 mb-3">
                    <div className={cn("w-9 h-9 rounded-xl flex items-center justify-center", overdueCount > 0 ? "bg-red-500/10 border border-red-500/20" : "bg-muted border border-border")}>
                        {overdueCount > 0
                            ? <AlertTriangle className="w-4 h-4 text-red-400" />
                            : <TrendingUp className="w-4 h-4 text-muted-foreground" />}
                    </div>
                    <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                        {overdueCount > 0 ? t("kpiCards.vencidas") : t("kpiCards.netoPeriodo")}
                    </span>
                </div>
                {overdueCount > 0 ? (
                    <>
                        <p className="text-2xl font-bold text-red-400 tracking-tight">{t("kpiCards.facturasVencidas", { count: overdueCount })}</p>
                        <p className="text-xs text-muted-foreground mt-1">{t("kpiCards.atencionInmediata")}</p>
                    </>
                ) : (
                    <>
                        <p className={cn("text-2xl font-bold tracking-tight", saldoNeto >= 0 ? "text-foreground" : "text-red-400")}>
                            {loading ? "—" : fmt(saldoNeto)}
                        </p>
                        <p className="text-xs text-muted-foreground mt-1">{t("kpiCards.ingresosGastos")}</p>
                    </>
                )}
            </div>
        </div>
    );
}
