"use client";

import { AlertTriangle } from "lucide-react";
import { useTranslations } from "next-intl";
import { useAnalitica } from "./_hooks/useAnalitica";
import { ResumenSection } from "./_components/ResumenSection";
import { VentasSection } from "./_components/VentasSection";
import { FinanzasSection } from "./_components/FinanzasSection";
import { RrhhSection } from "./_components/RrhhSection";
import { IaSection } from "./_components/IaSection";

function monthOptions(months: string[]): { value: string; label: string }[] {
    const opts: { value: string; label: string }[] = [];
    const now = new Date();
    let y = now.getFullYear();
    let m = now.getMonth();
    for (let i = 0; i < 12; i++) {
        const value = `${y}-${String(m + 1).padStart(2, "0")}`;
        opts.push({ value, label: `${months[m]} ${y}` });
        m -= 1;
        if (m < 0) { m = 11; y -= 1; }
    }
    return opts;
}

export default function AnaliticaPage() {
    const t = useTranslations("analitica");
    const {
        loading, error, period, setPeriod, periodLabel,
        cashflow, isDemo,
        ingresosPeriodo, gastosPeriodo, beneficioPeriodo, margenPeriodo,
        emitidasCount, recibidasCount,
        factPagadas, factPendientes, factBorrador,
        importePendienteCobro, importePendientePago, ticketMedio,
        vencenProximos, importeVencenProximos,
        topClientes, pieData,
        ventasDetalle, cobrosPagos,
        rrhh, banca,
        ia, iaDetalle,
        tasksDone, tasksFailed, tasksSuccessRate, tasksPending,
        inventario,
    } = useAnalitica();

    const months = [
        t("months.january"), t("months.february"), t("months.march"), t("months.april"),
        t("months.may"), t("months.june"), t("months.july"), t("months.august"),
        t("months.september"), t("months.october"), t("months.november"), t("months.december"),
    ];
    const opts = monthOptions(months);

    return (
        <div className="p-8 max-w-[1400px] mx-auto space-y-6">
            {/* Header */}
            <div className="flex items-start justify-between flex-wrap gap-4">
                <div>
                    <h1 className="text-3xl font-bold text-foreground tracking-tight">{t("page.title")}</h1>
                    <p className="mt-1 text-sm text-muted-foreground">
                        {t("page.subtitle")} — {periodLabel || t("page.loading")}
                        {isDemo && !loading && (
                            <span className="ml-2 text-xs text-amber-500 font-medium bg-amber-500/10 px-2 py-0.5 rounded-full border border-amber-500/20">
                                {t("page.noDataPeriod")}
                            </span>
                        )}
                    </p>
                    {error && (
                        <p className="mt-2 text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-1.5 inline-block">
                            {error}
                        </p>
                    )}
                </div>
                <div className="flex items-center gap-2">
                    <label className="text-xs text-muted-foreground font-medium">{t("page.period")}</label>
                    <select
                        value={period}
                        onChange={(e) => setPeriod(e.target.value)}
                        disabled={loading}
                        className="bg-card border border-border rounded-lg px-3 py-1.5 text-sm text-foreground hover:border-primary/40 focus:outline-none focus:border-primary transition-colors"
                    >
                        {opts.map(o => (
                            <option key={o.value} value={o.value}>{o.label}</option>
                        ))}
                    </select>
                </div>
            </div>

            {/* Aviso datos demo en banca */}
            {banca.has_demo_data && (
                <div className="flex items-start gap-3 p-4 rounded-2xl border border-amber-500/30 bg-amber-500/5">
                    <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
                    <div className="flex-1 text-sm">
                        <p className="font-medium text-amber-300">{t("demoBanner.title")}</p>
                        <p className="text-muted-foreground text-xs mt-1">
                            {t("demoBanner.body")}{" "}
                            {t("demoBanner.deleteFrom")} <code className="px-1 py-0.5 rounded bg-amber-500/10 text-amber-300">DELETE /api/v1/banking/transactions/demo</code>.
                        </p>
                    </div>
                </div>
            )}

            {/* Stacked sections */}
            <div className="space-y-12">
                {/* ── RESUMEN ───────────────────────────────────────────── */}
                <ResumenSection
                    loading={loading}
                    periodLabel={periodLabel}
                    cashflow={cashflow}
                    pieData={pieData}
                    ingresosPeriodo={ingresosPeriodo}
                    gastosPeriodo={gastosPeriodo}
                    beneficioPeriodo={beneficioPeriodo}
                    margenPeriodo={margenPeriodo}
                    emitidasCount={emitidasCount}
                    recibidasCount={recibidasCount}
                    factPagadas={factPagadas}
                    factPendientes={factPendientes}
                    factBorrador={factBorrador}
                    importePendienteCobro={importePendienteCobro}
                    vencenProximos={vencenProximos}
                    importeVencenProximos={importeVencenProximos}
                    tasksDone={tasksDone}
                    tasksSuccessRate={tasksSuccessRate}
                    bajasUnits={inventario.bajas_units}
                    bajasValueEur={inventario.bajas_value_eur}
                    belowMinCount={inventario.below_min_count}
                />

                {/* ── VENTAS ────────────────────────────────────────────── */}
                <VentasSection
                    periodLabel={periodLabel}
                    cashflow={cashflow}
                    topClientes={topClientes}
                    ventasDetalle={ventasDetalle}
                    ingresosPeriodo={ingresosPeriodo}
                    emitidasCount={emitidasCount}
                    ticketMedio={ticketMedio}
                    importePendienteCobro={importePendienteCobro}
                    factPagadas={factPagadas}
                    factPendientes={factPendientes}
                    factBorrador={factBorrador}
                />

                {/* ── FINANZAS ──────────────────────────────────────────── */}
                <FinanzasSection
                    periodLabel={periodLabel}
                    banca={banca}
                    cobrosPagos={cobrosPagos}
                    beneficioPeriodo={beneficioPeriodo}
                    margenPeriodo={margenPeriodo}
                    gastosPeriodo={gastosPeriodo}
                    recibidasCount={recibidasCount}
                    importePendienteCobro={importePendienteCobro}
                    importePendientePago={importePendientePago}
                />

                {/* ── RRHH ──────────────────────────────────────────────── */}
                <RrhhSection periodLabel={periodLabel} rrhh={rrhh} />

                {/* ── IA ────────────────────────────────────────────────── */}
                <IaSection
                    periodLabel={periodLabel}
                    ia={ia}
                    iaDetalle={iaDetalle}
                    tasksDone={tasksDone}
                    tasksFailed={tasksFailed}
                    tasksSuccessRate={tasksSuccessRate}
                    tasksPending={tasksPending}
                />
            </div>
        </div>
    );
}
