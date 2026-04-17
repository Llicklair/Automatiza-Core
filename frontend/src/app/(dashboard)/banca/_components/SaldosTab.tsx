"use client";

import { useEffect } from "react";
import { AlertTriangle, Building2, CreditCard, Link2, RefreshCw, WifiOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { EmptyState } from "@/components/shared/EmptyState";
import { useAgentPolling, extractOutput } from "../_hooks/useAgentPolling";
import { AgentLoader } from "./BancaCharts";

interface Saldo { account_id: string; iban: string; nombre: string; saldo: number; moneda: string; error?: string; }

export function SaldosTab() {
    const { launch, status, result, error } = useAgentPolling();
    const output = extractOutput(result);
    const saldos = (output.saldos ?? output.balances ?? []) as Saldo[];
    const alertas = (output.alertas ?? []) as string[];
    const isDemo = alertas.some(a => a.toLowerCase().includes("demo"));
    const totalSaldo = saldos.reduce((s, c) => s + (c.saldo ?? 0), 0);

    useEffect(() => { launch("saldo balance cuentas"); }, []); // eslint-disable-line react-hooks/exhaustive-deps

    if (status === "creating" || status === "polling") return <AgentLoader label="Consultando cuentas…" />;

    return (
        <div className="space-y-6">
            {isDemo && (
                <div className="flex items-center gap-3 px-4 py-3 rounded-xl border border-warning/20 bg-warning/5 text-warning text-sm">
                    <WifiOff className="w-4 h-4 flex-shrink-0" />
                    <span>Banco no conectado — datos de demostración. <a href="/integraciones" className="underline hover:opacity-80">Conectar banco real</a></span>
                </div>
            )}

            {error && (
                <div className="px-4 py-3 rounded-xl border border-destructive/20 bg-destructive/5 text-destructive text-sm">{error}</div>
            )}

            <Card className="border-primary/20 bg-gradient-to-br from-primary/10 to-transparent">
                <CardContent className="p-7">
                    <p className="text-xs text-muted-foreground uppercase tracking-widest mb-2">Saldo total consolidado</p>
                    <p className="text-5xl font-bold text-foreground tabular-nums">
                        {totalSaldo.toLocaleString("es-ES", { minimumFractionDigits: 2 })}
                        <span className="text-2xl text-muted-foreground ml-2">€</span>
                    </p>
                    {saldos.length > 0 && (
                        <p className="text-xs text-muted-foreground mt-3">{saldos.length} cuenta{saldos.length !== 1 ? "s" : ""} vinculada{saldos.length !== 1 ? "s" : ""}</p>
                    )}
                </CardContent>
            </Card>

            {saldos.length > 0 ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    {saldos.map((acc) => (
                        <Card key={acc.account_id} className="hover:border-primary/30 transition">
                            <CardContent className="p-6 flex items-start gap-4">
                                <div className="p-3 rounded-xl bg-primary/10 border border-primary/20 flex-shrink-0">
                                    <Building2 className="w-5 h-5 text-primary" />
                                </div>
                                <div className="flex-1 min-w-0">
                                    <p className="text-foreground font-medium text-sm truncate">{acc.nombre}</p>
                                    <p className="text-xs text-muted-foreground font-mono mt-0.5 truncate">{acc.iban}</p>
                                    <p className={`text-2xl font-bold mt-3 tabular-nums ${acc.saldo < 1000 ? "text-destructive" : "text-emerald-400"}`}>
                                        {(acc.saldo ?? 0).toLocaleString("es-ES", { minimumFractionDigits: 2 })}€
                                    </p>
                                </div>
                                {acc.saldo < 1000 && (
                                    <AlertTriangle className="w-4 h-4 text-warning flex-shrink-0 mt-1" />
                                )}
                            </CardContent>
                        </Card>
                    ))}
                </div>
            ) : (
                <EmptyState
                    icon={CreditCard}
                    title="Sin cuentas disponibles"
                    description="Conecta tu banco para ver tus cuentas y saldos en tiempo real."
                    action={
                        <Button variant="outline" asChild>
                            <a href="/integraciones"><Link2 className="mr-2 h-4 w-4" /> Conectar banco</a>
                        </Button>
                    }
                />
            )}

            {alertas.filter(a => !a.toLowerCase().includes("demo")).map((a, i) => (
                <div key={i} className="flex items-center gap-3 px-4 py-3 rounded-xl border border-warning/20 bg-warning/5 text-warning text-sm">
                    <AlertTriangle className="w-4 h-4 flex-shrink-0" /> {a}
                </div>
            ))}

            <Button variant="ghost" size="sm" onClick={() => launch("saldo balance cuentas")} className="text-muted-foreground">
                <RefreshCw className="mr-2 h-3.5 w-3.5" /> Actualizar
            </Button>
        </div>
    );
}
