"use client";

import { useTranslations } from "next-intl";
import {
    Users, RefreshCw, ChevronLeft, ChevronRight,
    Loader2, AlertCircle, CheckCircle2, PlusCircle,
    Receipt, Building2, Scale,
} from "lucide-react";
import type { FiscalSnapshot } from "@/lib/api";
import { KpiCard, Section, Row } from "./InformesHelpers";
import {
    fmt, fmtMonth, fmtQuarter,
    prevMonth, nextMonth, currentMonthStr,
    prevQuarter, nextQuarter, currentQuarterStr,
} from "../_hooks/useInformes";

interface FiscalTabProps {
    fiscalMode: "mensual" | "trimestral";
    setFiscalMode: (m: "mensual" | "trimestral") => void;
    fiscalMonth: string;
    setFiscalMonth: (m: string) => void;
    fiscalQuarter: string;
    setFiscalQuarter: (q: string) => void;
    fiscalSnap: FiscalSnapshot | null;
    fiscalLoading: boolean;
    fiscalGenerating: boolean;
    fiscalError: string | null;
    fiscalGenOk: boolean;
    loadFiscalSnapshot: () => void;
    handleGenerateFiscal: () => void;
}

export function FiscalTab({
    fiscalMode, setFiscalMode,
    fiscalMonth, setFiscalMonth,
    fiscalQuarter, setFiscalQuarter,
    fiscalSnap, fiscalLoading, fiscalGenerating, fiscalError, fiscalGenOk,
    loadFiscalSnapshot, handleGenerateFiscal,
}: FiscalTabProps) {
    const t = useTranslations("informes");
    return (
        <>
            {/* Controls */}
            <div className="flex items-center gap-3 flex-wrap">
                {/* Mode toggle */}
                <div className="flex items-center gap-0 rounded-xl border border-border bg-card p-0.5">
                    <button onClick={() => setFiscalMode("mensual")}
                        className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${fiscalMode === "mensual" ? "bg-accent text-foreground" : "text-muted-foreground hover:text-foreground"}`}>
                        {t("fiscal.mensual")}
                    </button>
                    <button onClick={() => setFiscalMode("trimestral")}
                        className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${fiscalMode === "trimestral" ? "bg-accent text-foreground" : "text-muted-foreground hover:text-foreground"}`}>
                        {t("fiscal.trimestral")}
                    </button>
                </div>

                {/* Period selector */}
                {fiscalMode === "mensual" ? (
                    <div className="flex items-center gap-1 rounded-xl border border-border bg-card px-2 py-1">
                        <button onClick={() => setFiscalMonth(prevMonth(fiscalMonth))} className="p-1.5 rounded-lg hover:bg-accent/50 text-muted-foreground">
                            <ChevronLeft className="w-4 h-4" />
                        </button>
                        <span className="text-sm font-semibold text-foreground w-36 text-center">{fmtMonth(t, fiscalMonth)}</span>
                        <button onClick={() => setFiscalMonth(nextMonth(fiscalMonth))}
                            disabled={fiscalMonth >= currentMonthStr()}
                            className="p-1.5 rounded-lg hover:bg-accent/50 text-muted-foreground disabled:opacity-30">
                            <ChevronRight className="w-4 h-4" />
                        </button>
                    </div>
                ) : (
                    <div className="flex items-center gap-1 rounded-xl border border-border bg-card px-2 py-1">
                        <button onClick={() => setFiscalQuarter(prevQuarter(fiscalQuarter))} className="p-1.5 rounded-lg hover:bg-accent/50 text-muted-foreground">
                            <ChevronLeft className="w-4 h-4" />
                        </button>
                        <span className="text-sm font-semibold text-foreground w-36 text-center">{fmtQuarter(t, fiscalQuarter)}</span>
                        <button onClick={() => setFiscalQuarter(nextQuarter(fiscalQuarter))}
                            disabled={fiscalQuarter >= currentQuarterStr()}
                            className="p-1.5 rounded-lg hover:bg-accent/50 text-muted-foreground disabled:opacity-30">
                            <ChevronRight className="w-4 h-4" />
                        </button>
                    </div>
                )}

                <button onClick={loadFiscalSnapshot} disabled={fiscalLoading}
                    className="flex items-center gap-2 px-3 py-2 rounded-xl border border-border text-sm text-foreground hover:bg-accent/50 transition-colors">
                    <RefreshCw className={`w-4 h-4 ${fiscalLoading ? "animate-spin" : ""}`} /> {t("fiscal.refresh")}
                </button>

                <button onClick={handleGenerateFiscal} disabled={fiscalGenerating}
                    className="flex items-center gap-2 px-4 py-2 rounded-xl bg-red-600 hover:bg-red-500 text-sm font-semibold text-foreground transition-colors disabled:opacity-40">
                    {fiscalGenerating ? <Loader2 className="w-4 h-4 animate-spin" /> : <PlusCircle className="w-4 h-4" />}
                    {t("fiscal.generatePdf")}
                </button>
            </div>

            {/* Alerts */}
            {fiscalError && (
                <div className="flex items-center gap-2 rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">
                    <AlertCircle className="w-4 h-4 shrink-0" /> {fiscalError}
                </div>
            )}
            {fiscalGenOk && (
                <div className="flex items-center gap-2 rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-300">
                    <CheckCircle2 className="w-4 h-4 shrink-0" /> {t("fiscal.genOk")}
                </div>
            )}

            {fiscalLoading && (
                <div className="flex items-center justify-center py-20 text-muted-foreground">
                    <Loader2 className="w-6 h-6 animate-spin mr-2" /> {t("fiscal.loadingData")}
                </div>
            )}

            {fiscalSnap && !fiscalLoading && (
                <>
                    {/* Resumen ejecutivo */}
                    <div className="rounded-2xl border border-red-500/20 bg-gradient-to-br from-red-900/20 to-card p-5">
                        <p className="text-xs font-semibold text-red-400 uppercase tracking-wider mb-2">
                            {t("fiscal.resumenFiscal", { period: fiscalSnap.period_label })}
                        </p>
                        <p className="text-sm text-foreground leading-relaxed">{fiscalSnap.resumen_ejecutivo}</p>
                    </div>

                    {/* KPIs */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <KpiCard
                            label={t("fiscal.kpiResultadoIva")}
                            value={`${fmt(fiscalSnap.iva.resultado_iva)} €`}
                            sub={fiscalSnap.iva.resultado_iva > 0 ? t("fiscal.kpiResultadoIvaIngresar") : t("fiscal.kpiResultadoIvaCompensar")}
                            icon={Receipt}
                            color={fiscalSnap.iva.resultado_iva > 0 ? "red" : "emerald"}
                        />
                        <KpiCard
                            label={t("fiscal.kpiIrpfRetenciones")}
                            value={`${fmt(fiscalSnap.irpf.total_retenciones)} €`}
                            sub={t("fiscal.kpiIrpfSub")}
                            icon={Users}
                            color="amber"
                        />
                        <KpiCard
                            label={t("fiscal.kpiIsEstimado")}
                            value={`${fmt(fiscalSnap.impuesto_sociedades.cuota_estimada)} €`}
                            sub={t("fiscal.kpiIsSub", { tipo: fiscalSnap.impuesto_sociedades.tipo_estimado })}
                            icon={Building2}
                            color="blue"
                        />
                        <KpiCard
                            label={t("fiscal.kpiTotalObligaciones")}
                            value={`${fmt(fiscalSnap.iva.resultado_iva + fiscalSnap.irpf.total_retenciones + fiscalSnap.impuesto_sociedades.cuota_estimada)} €`}
                            sub={t("fiscal.kpiTotalSub")}
                            icon={Scale}
                            color="indigo"
                        />
                    </div>

                    {/* Detail sections */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {/* IVA */}
                        <Section title={t("fiscal.sectionIva")} icon={Receipt}>
                            <Row label={t("fiscal.ivaRepercutido21")} value={`${fmt(fiscalSnap.iva.repercutido_21)} €`} />
                            <Row label={t("fiscal.ivaRepercutido10")} value={`${fmt(fiscalSnap.iva.repercutido_10)} €`} />
                            <Row label={t("fiscal.ivaRepercutido4")} value={`${fmt(fiscalSnap.iva.repercutido_4)} €`} />
                            <Row label={t("fiscal.totalRepercutido")} value={`${fmt(fiscalSnap.iva.total_repercutido)} €`} highlight />
                            <div className="border-t border-border mt-1 pt-1" />
                            <Row label={t("fiscal.ivaSoportado21")} value={`${fmt(fiscalSnap.iva.soportado_21)} €`} />
                            <Row label={t("fiscal.ivaSoportado10")} value={`${fmt(fiscalSnap.iva.soportado_10)} €`} />
                            <Row label={t("fiscal.ivaSoportado4")} value={`${fmt(fiscalSnap.iva.soportado_4)} €`} />
                            <Row label={t("fiscal.totalSoportado")} value={`${fmt(fiscalSnap.iva.total_soportado)} €`} highlight />
                            <div className="border-t border-border mt-1 pt-1" />
                            <Row label={t("fiscal.resultadoIva")} value={`${fmt(fiscalSnap.iva.resultado_iva)} €`} highlight />
                        </Section>

                        {/* IRPF + IS */}
                        <div className="space-y-4">
                            <Section title={t("fiscal.sectionRetencionesIrpf")} icon={Users}>
                                <Row label={t("fiscal.retencionesNominas")} value={`${fmt(fiscalSnap.irpf.retenciones_nominas)} €`} />
                                <Row label={t("fiscal.retencionesFacturas")} value={`${fmt(fiscalSnap.irpf.retenciones_facturas)} €`} />
                                <Row label={t("fiscal.totalRetenciones")} value={`${fmt(fiscalSnap.irpf.total_retenciones)} €`} highlight />
                            </Section>

                            <Section title={t("fiscal.sectionImpuestoSociedades")} icon={Building2}>
                                <Row label={t("fiscal.ingresosBrutos")} value={`${fmt(fiscalSnap.impuesto_sociedades.ingresos_brutos)} €`} />
                                <Row label={t("fiscal.gastosDeducibles")} value={`${fmt(fiscalSnap.impuesto_sociedades.gastos_deducibles)} €`} />
                                <Row label={t("fiscal.baseImponible")} value={`${fmt(fiscalSnap.impuesto_sociedades.base_imponible)} €`} highlight />
                                <Row label={t("fiscal.tipoImpositivo")} value={`${fiscalSnap.impuesto_sociedades.tipo_estimado}%`} />
                                <Row label={t("fiscal.cuotaEstimada")} value={`${fmt(fiscalSnap.impuesto_sociedades.cuota_estimada)} €`} highlight />
                            </Section>
                        </div>
                    </div>

                    {/* Disclaimer */}
                    <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 px-4 py-3 text-xs text-amber-300/80 text-center">
                        {t("fiscal.disclaimer")}
                    </div>
                </>
            )}

            {!fiscalLoading && !fiscalSnap && !fiscalError && (
                <div className="text-center py-20 text-muted-foreground">
                    <Receipt className="w-12 h-12 mx-auto mb-4 opacity-30" />
                    <p className="text-lg font-semibold text-muted-foreground">{t("fiscal.emptyTitle", { period: fiscalMode === "trimestral" ? fmtQuarter(t, fiscalQuarter) : fmtMonth(t, fiscalMonth) })}</p>
                    <p className="text-sm mt-1">{t("fiscal.emptySubtitle")}</p>
                </div>
            )}
        </>
    );
}
