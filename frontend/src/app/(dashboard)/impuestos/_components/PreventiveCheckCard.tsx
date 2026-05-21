"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, Info, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import type {
    PreventiveCheckResult,
    PreventiveFinding,
    PreventiveSeverity,
} from "@/lib/api/modelosAeat";

interface Props {
    quarter: number;
    year: number;
}

const SEVERITY_STYLES: Record<
    PreventiveSeverity,
    { icon: typeof AlertTriangle; bg: string; border: string; text: string; label: string }
> = {
    high: {
        icon: AlertTriangle,
        bg: "bg-red-50",
        border: "border-red-300",
        text: "text-red-900",
        label: "Crítico",
    },
    medium: {
        icon: Info,
        bg: "bg-amber-50",
        border: "border-amber-300",
        text: "text-amber-900",
        label: "Atención",
    },
    low: {
        icon: Info,
        bg: "bg-sky-50",
        border: "border-sky-300",
        text: "text-sky-900",
        label: "Aviso",
    },
};

function FindingRow({ f }: { f: PreventiveFinding }) {
    const s = SEVERITY_STYLES[f.severity];
    const Icon = s.icon;
    return (
        <div className={`flex gap-3 rounded-md border ${s.border} ${s.bg} p-3 ${s.text}`}>
            <Icon className="h-5 w-5 shrink-0 mt-0.5" />
            <div className="flex-1 space-y-1">
                <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide opacity-75">
                    <span>{s.label}</span>
                    <span className="opacity-50">·</span>
                    <span className="font-mono">{f.code}</span>
                </div>
                <div className="text-sm font-medium">{f.message}</div>
                <div className="text-sm opacity-90">→ {f.suggested_action}</div>
                {f.source_invoice_ids.length > 0 && (
                    <div className="text-xs opacity-70 font-mono">
                        {f.source_invoice_ids.length} factura(s) afectada(s)
                    </div>
                )}
            </div>
        </div>
    );
}

export function PreventiveCheckCard({ quarter, year }: Props) {
    const [data, setData] = useState<PreventiveCheckResult | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        setLoading(true);
        setError(null);
        api.modelosAeat
            .preventiveCheck(quarter, year)
            .then(setData)
            .catch((e: Error) => setError(e.message || "Error al chequear el trimestre"))
            .finally(() => setLoading(false));
    }, [quarter, year]);

    return (
        <section className="rounded-lg border border-slate-200 bg-white p-4 space-y-3">
            <header className="flex items-center justify-between">
                <div>
                    <h3 className="text-sm font-semibold text-slate-800">
                        Asistente fiscal preventivo · {quarter}T {year}
                    </h3>
                    <p className="text-xs text-slate-500">
                        Hallazgos detectados antes de cerrar el 303.
                    </p>
                </div>
                {data && (
                    <div className="flex gap-2 text-xs">
                        {(["high", "medium", "low"] as PreventiveSeverity[]).map((sev) => {
                            const n = data.count_by_severity[sev] ?? 0;
                            if (!n) return null;
                            const cls = SEVERITY_STYLES[sev];
                            return (
                                <span
                                    key={sev}
                                    className={`px-2 py-0.5 rounded-full border ${cls.border} ${cls.bg} ${cls.text} font-mono`}
                                >
                                    {n} {cls.label.toLowerCase()}
                                </span>
                            );
                        })}
                    </div>
                )}
            </header>

            {loading && (
                <div className="flex items-center gap-2 text-sm text-slate-500">
                    <Loader2 className="h-4 w-4 animate-spin" /> Analizando facturas del trimestre…
                </div>
            )}

            {error && (
                <div className="flex items-center gap-2 text-sm text-red-700">
                    <AlertTriangle className="h-4 w-4" /> {error}
                </div>
            )}

            {!loading && !error && data && data.findings.length === 0 && (
                <div className="flex items-center gap-2 rounded-md bg-emerald-50 border border-emerald-200 p-3 text-sm text-emerald-900">
                    <CheckCircle2 className="h-5 w-5" />
                    Sin riesgos detectados. El trimestre parece listo para presentar.
                </div>
            )}

            {!loading && !error && data && data.findings.length > 0 && (
                <div className="space-y-2">
                    {data.findings.map((f) => (
                        <FindingRow key={`${f.code}-${f.message}`} f={f} />
                    ))}
                </div>
            )}
        </section>
    );
}
