/**
 * UI.SIM — simulación Modelo 303 con datos ejemplo.
 *
 * Disparable desde el paso 4 del wizard `/bienvenida`. El usuario ve un
 * 303 "real" calculado sobre un dataset de un autónomo prototípico antes
 * de meter sus propios datos. Sirve para fijar la promesa funcional del
 * producto en menos de 30 segundos.
 */
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, FileSpreadsheet, Info, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import type { Simulate303Result } from "@/lib/api/onboarding";
import { useToastStore } from "@/stores/toast";

export default function Simulacion303Page() {
    const toast = useToastStore();
    const [data, setData] = useState<Simulate303Result | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        api.onboarding
            .simulate303(1, 2026)
            .then(setData)
            .catch((e: Error) => toast.show(`Error: ${e.message}`, "error"))
            .finally(() => setLoading(false));
    }, [toast]);

    if (loading || !data) {
        return (
            <div className="p-8 flex items-center gap-3 text-muted-foreground">
                <Loader2 className="w-4 h-4 animate-spin" /> Generando simulación…
            </div>
        );
    }

    const fmtEUR = (n: number) =>
        n.toLocaleString("es-ES", { style: "currency", currency: "EUR" });

    const resultadoColor =
        data.totals.resultado > 0
            ? "text-amber-500"
            : data.totals.resultado < 0
                ? "text-emerald-500"
                : "text-foreground";

    return (
        <div className="p-6 max-w-3xl mx-auto space-y-6">
            <header>
                <Link
                    href="/bienvenida"
                    className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground mb-2"
                >
                    <ArrowLeft className="w-3.5 h-3.5" aria-hidden="true" /> Volver al wizard
                </Link>
                <div className="flex items-center gap-3">
                    <FileSpreadsheet className="w-5 h-5 text-primary" aria-hidden="true" />
                    <h1 className="text-2xl font-semibold text-foreground tracking-tight">
                        Modelo 303 · simulación
                    </h1>
                </div>
                <p className="mt-1 text-sm text-muted-foreground">
                    {data.tenant_name} · NIF {data.tenant_nif} · Q{data.quarter} {data.year}
                </p>
            </header>

            {/* Banner explicativo */}
            <div
                role="status"
                className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-3 flex items-start gap-2"
            >
                <Info className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" aria-hidden="true" />
                <p className="text-xs text-muted-foreground leading-relaxed">
                    <strong className="text-foreground">Datos ejemplo.</strong> Esto NO se presenta a la AEAT.
                    Es una demo de cómo el sistema calcula el 303 a partir de tus facturas reales.
                </p>
            </div>

            {/* Hero — Resultado a ingresar */}
            <section
                aria-labelledby="resultado-heading"
                className="rounded-lg border border-primary/30 bg-primary/5 p-6 text-center"
            >
                <h2
                    id="resultado-heading"
                    className="text-xs uppercase tracking-wider text-muted-foreground mb-2"
                >
                    {data.explanation.headline}
                </h2>
                <p className={`text-4xl font-bold ${resultadoColor}`}>
                    {fmtEUR(data.totals.resultado)}
                </p>
                <p className="mt-2 text-xs text-muted-foreground">
                    {data.totals.resultado > 0
                        ? "Resultado a ingresar"
                        : data.totals.resultado < 0
                            ? "A devolver (saldo a favor)"
                            : "Liquidación a cero"}
                </p>
            </section>

            {/* Desglose */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Box title="IVA devengado (ventas)">
                    <Table rows={data.iva_devengado} totals={[data.totals.devengado_base, data.totals.devengado_quota]} />
                </Box>
                <Box title="IVA deducible (compras)">
                    <Table rows={data.iva_deducible} totals={[data.totals.deducible_base, data.totals.deducible_quota]} />
                </Box>
            </div>

            {/* Resumen en bullets */}
            <section
                aria-labelledby="resumen-heading"
                className="rounded-lg border border-border bg-card p-4"
            >
                <h2 id="resumen-heading" className="text-sm font-semibold text-foreground mb-2">
                    Resumen
                </h2>
                <ul className="space-y-1.5">
                    {data.explanation.bullets.map((b) => (
                        <li key={b} className="flex items-start gap-2 text-xs text-foreground">
                            <span aria-hidden="true" className="text-primary mt-0.5">▸</span>
                            {b}
                        </li>
                    ))}
                </ul>
                <p className="mt-3 text-xs text-muted-foreground italic leading-relaxed">
                    {data.explanation.footer}
                </p>
            </section>

            {/* Acciones */}
            <div className="flex items-center justify-between pt-4 border-t border-border">
                <Link
                    href="/bienvenida"
                    className="text-sm text-muted-foreground hover:text-foreground"
                >
                    ← Volver al wizard
                </Link>
                <Link
                    href="/ventas/facturas"
                    className="inline-flex items-center gap-1.5 px-4 py-2 rounded-md bg-primary text-foreground text-sm font-medium hover:bg-primary/90"
                >
                    Crear mi primera factura real →
                </Link>
            </div>
        </div>
    );
}

function Box({ title, children }: { title: string; children: React.ReactNode }) {
    return (
        <div className="rounded-lg border border-border bg-card p-4">
            <h3 className="text-xs font-semibold text-foreground uppercase tracking-wider mb-3">
                {title}
            </h3>
            {children}
        </div>
    );
}

function Table({
    rows,
    totals,
}: {
    rows: { rate: number; base: number; quota: number }[];
    totals: [number, number];
}) {
    const fmt = (n: number) =>
        n.toLocaleString("es-ES", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    return (
        <table className="w-full text-xs">
            <thead>
                <tr className="text-muted-foreground border-b border-border">
                    <th className="text-left font-medium pb-1.5">Tipo</th>
                    <th className="text-right font-medium pb-1.5">Base</th>
                    <th className="text-right font-medium pb-1.5">Cuota</th>
                </tr>
            </thead>
            <tbody>
                {rows.map((r) => (
                    <tr key={r.rate} className="border-b border-border/40">
                        <td className="py-1.5 text-foreground">{r.rate}%</td>
                        <td className="py-1.5 text-right text-foreground tabular-nums">{fmt(r.base)} €</td>
                        <td className="py-1.5 text-right text-foreground tabular-nums">{fmt(r.quota)} €</td>
                    </tr>
                ))}
                <tr>
                    <td className="pt-2 font-semibold text-foreground">Total</td>
                    <td className="pt-2 text-right font-semibold text-foreground tabular-nums">{fmt(totals[0])} €</td>
                    <td className="pt-2 text-right font-semibold text-foreground tabular-nums">{fmt(totals[1])} €</td>
                </tr>
            </tbody>
        </table>
    );
}
