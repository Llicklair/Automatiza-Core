"use client";

import { FolderTree, Search, ChevronRight, ChevronDown, Loader2, BookOpen } from "lucide-react";
import { useCuadroCuentas } from "./_hooks/useCuadroCuentas";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const fmt = (n: number) => n.toLocaleString("es-ES", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export default function CuadroCuentasPage() {
    const { loading, noData, search, setSearch, expanded, filteredGroups, toggle, q } = useCuadroCuentas();

    return (
        <div className="p-8 max-w-[1400px] mx-auto space-y-6">
            <PageHeader
                title="Cuadro de Cuentas (PGC)"
                description="Plan General Contable de España — cuentas con actividad real en el libro diario."
                icon={FolderTree}
                actions={
                    <div className="flex items-center gap-3">
                        {noData && (
                            <div className="flex items-center gap-2 bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs px-3 py-2 rounded-xl">
                                <BookOpen className="w-4 h-4" /> Sin asientos registrados
                            </div>
                        )}
                        <div className="relative">
                            <Search className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
                            <Input
                                placeholder="Buscar código 430, 700..."
                                value={search}
                                onChange={e => setSearch(e.target.value)}
                                className="pl-9 w-56"
                            />
                        </div>
                    </div>
                }
            />

            {loading ? (
                <div className="flex items-center justify-center py-24 text-muted-foreground gap-2">
                    <Loader2 className="w-5 h-5 animate-spin" /> Cargando cuentas…
                </div>
            ) : filteredGroups.length === 0 ? (
                <div className="bg-card border border-border rounded-2xl p-16 flex flex-col items-center text-center">
                    <FolderTree className="w-12 h-12 text-muted-foreground mb-4" />
                    <h2 className="text-lg font-bold text-foreground mb-2">
                        {noData ? "Sin movimientos contables" : "Sin resultados"}
                    </h2>
                    <p className="text-sm text-muted-foreground max-w-md">
                        {noData
                            ? "Las cuentas PGC aparecerán aquí automáticamente cuando se registren facturas o asientos en el libro diario."
                            : `No hay cuentas que coincidan con "${search}"`}
                    </p>
                </div>
            ) : (
                <div className="bg-card border border-border rounded-2xl overflow-hidden shadow-xl shadow-black/20">
                    <div className="grid grid-cols-12 gap-4 px-6 py-3 border-b border-border text-xs font-medium text-muted-foreground uppercase tracking-wide bg-muted">
                        <div className="col-span-5">Cuenta</div>
                        <div className="col-span-3 text-right">Debe</div>
                        <div className="col-span-3 text-right">Haber</div>
                        <div className="col-span-1 text-right">Saldo</div>
                    </div>

                    {filteredGroups.map(group => {
                        const isOpen = expanded.has(group.group) || !!q;
                        const groupDebit = group.accounts.reduce((s, a) => s + a.debit, 0);
                        const groupCredit = group.accounts.reduce((s, a) => s + a.credit, 0);
                        const groupSaldo = groupDebit - groupCredit;

                        return (
                            <div key={group.group} className="border-b border-border last:border-0">
                                <Button
                                    variant="ghost"
                                    onClick={() => toggle(group.group)}
                                    className="w-full grid grid-cols-12 gap-4 px-6 py-3.5 h-auto rounded-none text-left"
                                >
                                    <div className="col-span-5 flex items-center gap-2">
                                        {isOpen
                                            ? <ChevronDown className="w-4 h-4 text-muted-foreground group-hover:text-foreground flex-shrink-0" />
                                            : <ChevronRight className="w-4 h-4 text-muted-foreground group-hover:text-foreground flex-shrink-0" />
                                        }
                                        <span className="font-bold font-mono text-foreground">Grupo {group.group}</span>
                                        <span className="text-muted-foreground text-sm truncate">{group.name}</span>
                                    </div>
                                    <div className="col-span-3 text-right font-mono text-sm text-muted-foreground">{fmt(groupDebit)}</div>
                                    <div className="col-span-3 text-right font-mono text-sm text-muted-foreground">{fmt(groupCredit)}</div>
                                    <div className={`col-span-1 text-right font-mono text-sm font-semibold ${groupSaldo >= 0 ? "text-foreground" : "text-rose-400"}`}>
                                        {fmt(Math.abs(groupSaldo))}
                                        {groupSaldo < 0 && <span className="text-xs ml-0.5">H</span>}
                                    </div>
                                </Button>

                                {isOpen && group.accounts
                                    .sort((a, b) => a.code.localeCompare(b.code))
                                    .map(acct => {
                                        const saldo = acct.debit - acct.credit;
                                        return (
                                            <div key={acct.code} className="grid grid-cols-12 gap-4 px-6 py-2.5 bg-muted/30 hover:bg-white/[0.01] border-t border-border/50 transition-colors">
                                                <div className="col-span-5 flex items-center gap-2 pl-6">
                                                    <span className="font-bold font-mono text-primary text-sm w-10 flex-shrink-0">{acct.code}</span>
                                                    <span className="text-muted-foreground text-sm truncate">{acct.name}</span>
                                                </div>
                                                <div className="col-span-3 text-right font-mono text-sm text-muted-foreground">{fmt(acct.debit)}</div>
                                                <div className="col-span-3 text-right font-mono text-sm text-muted-foreground">{fmt(acct.credit)}</div>
                                                <div className={`col-span-1 text-right font-mono text-sm ${saldo >= 0 ? "text-foreground" : "text-rose-400"}`}>
                                                    {fmt(Math.abs(saldo))}
                                                    {saldo < 0 && <span className="text-xs ml-0.5">H</span>}
                                                </div>
                                            </div>
                                        );
                                    })
                                }
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
