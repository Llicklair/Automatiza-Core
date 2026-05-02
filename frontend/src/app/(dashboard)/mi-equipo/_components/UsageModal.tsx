"use client";

import { useEffect, useState } from "react";
import { aiEmployees, type AIEmployee, type EmployeeUsage } from "@/lib/api/ai_employees";
import { X, Loader2, Activity } from "lucide-react";

function fmtTokens(n: number) {
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
    if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
    return String(n);
}

function fmtDate(iso: string) {
    const d = new Date(iso);
    return d.toLocaleString("es-ES", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
}

export function UsageModal({ employee, onClose }: { employee: AIEmployee; onClose: () => void }) {
    const [data, setData] = useState<EmployeeUsage | null>(null);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        let cancelled = false;
        aiEmployees.usage(employee.id, { limit: 100 })
            .then(r => { if (!cancelled) setData(r); })
            .catch(e => { if (!cancelled) setError(e?.message ?? "Error cargando consumo"); });
        return () => { cancelled = true; };
    }, [employee.id]);

    const limit = employee.budget_limit_usd ?? 0;
    const spent = data?.total_cost_usd ?? 0;
    const pct = limit > 0 ? Math.min(100, (spent / limit) * 100) : 0;
    const barColor = pct >= 90 ? "bg-red-500" : pct >= 70 ? "bg-amber-500" : "bg-emerald-500";

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
            <div className="bg-card border border-border rounded-2xl shadow-xl w-full max-w-2xl max-h-[85vh] flex flex-col">
                <div className="flex items-center justify-between p-5 border-b border-border">
                    <div className="flex items-center gap-2">
                        <Activity className="w-4 h-4 text-violet-400" />
                        <h2 className="font-semibold text-foreground text-sm">Consumo de {employee.name}</h2>
                    </div>
                    <button onClick={onClose} className="p-1 hover:bg-muted rounded-lg">
                        <X className="w-4 h-4 text-muted-foreground" />
                    </button>
                </div>

                {!data && !error && (
                    <div className="flex items-center justify-center p-10">
                        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
                    </div>
                )}
                {error && <p className="p-5 text-xs text-red-400">{error}</p>}
                {data && (
                    <div className="flex-1 overflow-y-auto p-5 space-y-4">
                        {limit > 0 && (
                            <div className="space-y-1.5">
                                <div className="flex items-center justify-between text-xs">
                                    <span className="text-muted-foreground">Presupuesto</span>
                                    <span className="font-medium">${spent.toFixed(4)} / ${limit.toFixed(2)} ({pct.toFixed(0)}%)</span>
                                </div>
                                <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                                    <div className={`h-full ${barColor} transition-all`} style={{ width: `${pct}%` }} />
                                </div>
                            </div>
                        )}

                        <div className="grid grid-cols-3 gap-2">
                            {[
                                { label: "Llamadas", value: String(data.total_calls) },
                                { label: "Tokens", value: fmtTokens(data.total_tokens_in + data.total_tokens_out) },
                                { label: "Coste total", value: `$${data.total_cost_usd.toFixed(4)}` },
                            ].map(({ label, value }) => (
                                <div key={label} className="bg-muted/40 rounded-lg p-3 text-center">
                                    <p className="text-base font-semibold">{value}</p>
                                    <p className="text-[10px] text-muted-foreground">{label}</p>
                                </div>
                            ))}
                        </div>

                        {data.entries.length === 0 ? (
                            <p className="text-center text-xs text-muted-foreground py-6">
                                Aún no hay llamadas registradas para este empleado.
                            </p>
                        ) : (
                            <div className="overflow-x-auto">
                                <table className="w-full text-xs">
                                    <thead className="text-muted-foreground border-b border-border">
                                        <tr>
                                            <th className="text-left py-1.5 pr-3 font-normal">Fecha</th>
                                            <th className="text-left py-1.5 pr-3 font-normal">Provider</th>
                                            <th className="text-right py-1.5 pr-3 font-normal">Tokens in</th>
                                            <th className="text-right py-1.5 pr-3 font-normal">Tokens out</th>
                                            <th className="text-right py-1.5 font-normal">Coste</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {data.entries.map(e => (
                                            <tr key={e.id} className="border-b border-border/50 hover:bg-muted/20">
                                                <td className="py-1.5 pr-3 text-muted-foreground">{fmtDate(e.created_at)}</td>
                                                <td className="py-1.5 pr-3">{e.provider ?? "—"}</td>
                                                <td className="text-right py-1.5 pr-3">{fmtTokens(e.tokens_in)}</td>
                                                <td className="text-right py-1.5 pr-3">{fmtTokens(e.tokens_out)}</td>
                                                <td className="text-right py-1.5 font-medium">${e.cost_usd.toFixed(4)}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
