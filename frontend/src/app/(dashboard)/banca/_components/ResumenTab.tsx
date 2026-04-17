"use client";

import { useEffect, useState } from "react";
import { Banknote, Loader2, RefreshCw, TrendingDown, TrendingUp, Wifi, WifiOff } from "lucide-react";
import { api } from "@/lib/api";
import { KpiCard } from "@/components/shared/KpiCard";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useToastStore } from "@/stores/toast";
import { useAgentPolling, extractOutput } from "../_hooks/useAgentPolling";
import { BarSparkline, DonutChart } from "./BancaCharts";

interface Saldo { account_id: string; iban: string; nombre: string; saldo: number; moneda: string; error?: string; }

const catColors: Record<string, string> = {
    nominas: "#60a5fa", proveedor_servicio: "#c084fc", suministros: "#22d3ee",
    financiero: "#facc15", alquiler: "#f472b6", proveedor_material: "#fb923c",
    impuestos: "#f87171", otros: "#71717a"
};
const catLabels: Record<string, string> = {
    nominas: "Nóminas", proveedor_servicio: "Soft/Servicios", suministros: "Suministros",
    financiero: "Financiero", alquiler: "Alquileres", proveedor_material: "Materiales",
    impuestos: "Impuestos"
};

const DEFAULT_CATEGORIAS = [
    { label: "Nóminas", value: 7000, color: "#60a5fa" },
    { label: "Proveedores", value: 2800, color: "#c084fc" },
    { label: "Suministros", value: 1500, color: "#22d3ee" },
    { label: "Financiero", value: 1100, color: "#facc15" },
    { label: "Otros", value: 330, color: "#71717a" },
];

export function ResumenTab() {
    const { launch, status, result, error } = useAgentPolling();
    const output = extractOutput(result);
    const resumenTexto = (output.resumen_financiero ?? output.resumen ?? null) as string | null;
    const alertas = (output.alertas ?? []) as string[];
    const isDemo = alertas.some(a => a.toLowerCase().includes("demo"));

    const [metrics, setMetrics] = useState({ ingresos: 18500, gastos: 12730, neto: 5770, margen: 31, isDemo: true });

    const porCategoriaRaw = output.por_categoria as Record<string, { total: number; operaciones: number }> | undefined;

    let categorias = DEFAULT_CATEGORIAS;
    if (porCategoriaRaw) {
        const gastosCat = Object.entries(porCategoriaRaw)
            .filter(([_, data]) => data.total < 0)
            .map(([cat, data]) => ({
                label: catLabels[cat] || "Otros",
                value: Math.abs(data.total),
                color: catColors[cat] || catColors.otros
            }))
            .sort((a, b) => b.value - a.value);
        if (gastosCat.length > 0) categorias = gastosCat;
    }

    const totalGastos = categorias.reduce((s, c) => s + c.value, 0);
    const mensual = metrics.isDemo ? [] : [metrics.neto];

    useEffect(() => {
        api.banking.summary().then((d) => {
            setMetrics({ ingresos: d.ingresos, gastos: d.gastos, neto: d.neto, margen: d.margen, isDemo: d.is_demo });
        }).catch(err => useToastStore.getState().error(err?.message || "Error al cargar datos bancarios"));

        launch("resumen financiero mes");
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    return (
        <div className="space-y-6">
            {(isDemo || metrics.isDemo) && (
                <div className="flex items-center gap-3 px-4 py-3 rounded-xl border border-warning/20 bg-warning/5 text-warning text-sm">
                    <WifiOff className="w-4 h-4 flex-shrink-0" />
                    <span>Esta cuenta es nueva y no tiene datos históricos. Estás viendo información precalculada de demostración para las tarjetas de resumen. <a href="/integraciones" className="underline hover:opacity-80">Conecta tu banco real</a> y registra facturas para ver métricas en vivo.</span>
                </div>
            )}
            {error && <div className="px-4 py-3 rounded-xl border border-destructive/20 bg-destructive/5 text-destructive text-sm">{error}</div>}

            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <KpiCard title="Ingresos" value={`+${metrics.ingresos.toLocaleString("es-ES")}€`} icon={TrendingUp} />
                <KpiCard title="Gastos" value={`-${metrics.gastos.toLocaleString("es-ES")}€`} icon={TrendingDown} />
                <KpiCard title="Resultado neto" value={`${metrics.neto >= 0 ? "+" : ""}${metrics.neto.toLocaleString("es-ES")}€`} icon={Banknote} />
                <KpiCard title="Margen" value={`${metrics.margen}%`} icon={Wifi} />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <Card>
                    <CardContent className="p-6">
                        <p className="text-sm font-medium text-foreground mb-5">Desglose de gastos</p>
                        <div className="flex items-center gap-6">
                            <div className="relative flex-shrink-0">
                                <DonutChart segments={categorias} />
                                <div className="absolute inset-0 flex items-center justify-center flex-col">
                                    <span className="text-xs text-muted-foreground">Total</span>
                                    <span className="text-sm font-bold text-foreground">{totalGastos.toLocaleString("es-ES")}€</span>
                                </div>
                            </div>
                            <div className="flex-1 space-y-2.5">
                                {categorias.map(c => (
                                    <div key={c.label}>
                                        <div className="flex justify-between text-xs mb-1">
                                            <span className="text-muted-foreground">{c.label}</span>
                                            <span className="text-foreground tabular-nums">{c.value.toLocaleString("es-ES")}€</span>
                                        </div>
                                        <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                                            <div className="h-full rounded-full transition-all duration-700"
                                                style={{ width: `${(c.value / totalGastos) * 100}%`, backgroundColor: c.color }} />
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardContent className="p-6">
                        <div className="flex items-start justify-between mb-5">
                            <p className="text-sm font-medium text-foreground">Resultado neto mensual</p>
                            <span className="text-xs text-muted-foreground">Últimos 6 meses</span>
                        </div>
                        {mensual.length === 0 ? (
                            <div className="h-[60px] flex items-center justify-center text-sm text-muted-foreground">Conecta tu banco para ver la tendencia</div>
                        ) : (
                            <>
                                <BarSparkline values={mensual} color={metrics.neto >= 0 ? "#6366f1" : "#ef4444"} />
                                <div className="flex justify-between mt-2">
                                    {["Sep", "Oct", "Nov", "Dic", "Ene", "Feb"].map((m, i) => (
                                        <span key={i} className="text-xs text-muted-foreground/60">{m}</span>
                                    ))}
                                </div>
                            </>
                        )}
                        <div className="mt-6 pt-5 border-t border-border">
                            <div className="flex justify-between text-xs mb-2">
                                <span className="text-muted-foreground">Margen sobre ingresos</span>
                                <span className="font-bold text-primary">{metrics.margen}%</span>
                            </div>
                            <div className="h-2 rounded-full bg-muted overflow-hidden">
                                <div className="h-full rounded-full bg-gradient-to-r from-primary to-primary/60 transition-all duration-1000"
                                    style={{ width: `${Math.min(100, Math.max(0, metrics.margen))}%` }} />
                            </div>
                            <p className="text-xs text-muted-foreground/60 mt-1.5">
                                {metrics.margen >= 30 ? "Margen saludable" : metrics.margen >= 15 ? "Margen ajustado" : "Margen bajo"}
                            </p>
                        </div>
                    </CardContent>
                </Card>
            </div>

            <Card>
                <CardContent className="p-6">
                    <div className="flex items-center justify-between mb-4">
                        <p className="text-sm font-medium text-foreground">Análisis del agente IA</p>
                        <Button variant="ghost" size="sm"
                            onClick={() => launch("resumen financiero mes")}
                            disabled={status === "polling" || status === "creating"}
                            className="text-muted-foreground"
                        >
                            {status === "polling" || status === "creating" ? <Loader2 className="mr-1.5 h-3 w-3 animate-spin" /> : <RefreshCw className="mr-1.5 h-3 w-3" />}
                            {status === "polling" ? "Generando…" : "Regenerar"}
                        </Button>
                    </div>
                    {status === "creating" || status === "polling" ? (
                        <div className="flex items-center gap-3 text-muted-foreground text-sm py-4">
                            <Loader2 className="w-4 h-4 animate-spin" /> El agente está analizando tus finanzas…
                        </div>
                    ) : (
                        <p className="text-sm text-foreground leading-relaxed whitespace-pre-line">
                            {resumenTexto ?? "Haz clic en Regenerar para que la IA analice tus movimientos del mes y genere recomendaciones personalizadas."}
                        </p>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}
