"use client";

import { useEffect, useState } from "react";
import { api, type JournalEntry } from "@/lib/api";
import { logError } from "@/lib/logger";
import { FolderTree, Search, ChevronRight, ChevronDown, Loader2, BookOpen } from "lucide-react";

// PGC group names
const GROUP_NAMES: Record<string, string> = {
    "1": "Financiación básica",
    "2": "Activo no corriente",
    "3": "Existencias",
    "4": "Acreedores y deudores por operaciones comerciales",
    "5": "Cuentas financieras",
    "6": "Compras y gastos",
    "7": "Ventas e ingresos",
    "8": "Gastos imputados al patrimonio neto",
    "9": "Ingresos imputados al patrimonio neto",
};

const fmt = (n: number) => n.toLocaleString("es-ES", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

interface AccountNode {
    code: string;
    name: string;
    debit: number;
    credit: number;
}

interface GroupNode {
    group: string;
    name: string;
    accounts: AccountNode[];
}

export default function CuadroCuentasPage() {
    const [entries, setEntries] = useState<JournalEntry[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState("");
    const [expanded, setExpanded] = useState<Set<string>>(new Set(["4", "5", "6", "7"]));

    useEffect(() => {
        api.accounting.journal.list()
            .then(setEntries)
            .catch(err => logError("contabilidad/cuadro-cuentas", err))
            .finally(() => setLoading(false));
    }, []);

    // Build account tree
    const accountMap: Record<string, AccountNode> = {};
    entries.forEach(entry => {
        entry.lines.forEach(line => {
            const code3 = line.account_code.substring(0, 3);
            if (!accountMap[code3]) {
                accountMap[code3] = { code: code3, name: line.account_name || `Cuenta ${code3}`, debit: 0, credit: 0 };
            }
            accountMap[code3].debit += Number(line.debit);
            accountMap[code3].credit += Number(line.credit);
        });
    });

    // Group by first digit
    const groupMap: Record<string, GroupNode> = {};
    Object.values(accountMap).forEach(acct => {
        const g = acct.code.substring(0, 1);
        if (!groupMap[g]) {
            groupMap[g] = { group: g, name: GROUP_NAMES[g] || `Grupo ${g}`, accounts: [] };
        }
        groupMap[g].accounts.push(acct);
    });

    const groups = Object.values(groupMap).sort((a, b) => a.group.localeCompare(b.group));

    const q = search.toLowerCase();
    const filteredGroups = groups.map(g => ({
        ...g,
        accounts: g.accounts.filter(a =>
            !q || a.code.includes(q) || a.name.toLowerCase().includes(q)
        ),
    })).filter(g => !q || g.group.includes(q) || g.name.toLowerCase().includes(q) || g.accounts.length > 0);

    const toggle = (key: string) => {
        setExpanded(prev => {
            const next = new Set(prev);
            if (next.has(key)) next.delete(key);
            else next.add(key);
            return next;
        });
    };

    const noData = !loading && entries.length === 0;

    return (
        <div className="p-8 max-w-6xl mx-auto space-y-8">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-white tracking-tight">Cuadro de Cuentas (PGC)</h1>
                    <p className="mt-1 text-sm text-zinc-400">
                        Plan General Contable de España — cuentas con actividad real en el libro diario.
                    </p>
                </div>
                <div className="flex items-center gap-3">
                    {noData && (
                        <div className="flex items-center gap-2 bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs px-3 py-2 rounded-xl">
                            <BookOpen className="w-4 h-4" />
                            Sin asientos registrados
                        </div>
                    )}
                    <div className="relative">
                        <Search className="w-4 h-4 text-zinc-500 absolute left-3 top-1/2 -translate-y-1/2" />
                        <input
                            type="text"
                            placeholder="Buscar código 430, 700..."
                            value={search}
                            onChange={e => setSearch(e.target.value)}
                            className="bg-[#18181b] border border-[#3f3f46] text-white text-sm rounded-xl pl-9 pr-4 py-2 w-56 focus:outline-none focus:border-indigo-500 transition-colors"
                        />
                    </div>
                </div>
            </div>

            {loading ? (
                <div className="flex items-center justify-center py-24 text-zinc-500 gap-2">
                    <Loader2 className="w-5 h-5 animate-spin" /> Cargando cuentas…
                </div>
            ) : filteredGroups.length === 0 ? (
                <div className="bg-[#111113] border border-[#27272a] rounded-2xl p-16 flex flex-col items-center text-center">
                    <FolderTree className="w-12 h-12 text-zinc-700 mb-4" />
                    <h2 className="text-lg font-bold text-white mb-2">
                        {noData ? "Sin movimientos contables" : "Sin resultados"}
                    </h2>
                    <p className="text-sm text-zinc-500 max-w-md">
                        {noData
                            ? "Las cuentas PGC aparecerán aquí automáticamente cuando se registren facturas o asientos en el libro diario."
                            : `No hay cuentas que coincidan con "${search}"`}
                    </p>
                </div>
            ) : (
                <div className="bg-[#111113] border border-[#27272a] rounded-2xl overflow-hidden shadow-xl shadow-black/20">
                    {/* Table header */}
                    <div className="grid grid-cols-12 gap-4 px-6 py-3 border-b border-[#27272a] text-xs font-medium text-zinc-500 uppercase tracking-wide bg-[#161618]">
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
                            <div key={group.group} className="border-b border-[#27272a] last:border-0">
                                {/* Group row */}
                                <button
                                    onClick={() => toggle(group.group)}
                                    className="w-full grid grid-cols-12 gap-4 px-6 py-3.5 hover:bg-white/[0.02] transition-colors text-left group"
                                >
                                    <div className="col-span-5 flex items-center gap-2">
                                        {isOpen
                                            ? <ChevronDown className="w-4 h-4 text-zinc-500 group-hover:text-white flex-shrink-0" />
                                            : <ChevronRight className="w-4 h-4 text-zinc-500 group-hover:text-white flex-shrink-0" />
                                        }
                                        <span className="font-bold font-mono text-zinc-200">Grupo {group.group}</span>
                                        <span className="text-zinc-400 text-sm truncate">{group.name}</span>
                                    </div>
                                    <div className="col-span-3 text-right font-mono text-sm text-zinc-400">{fmt(groupDebit)}</div>
                                    <div className="col-span-3 text-right font-mono text-sm text-zinc-400">{fmt(groupCredit)}</div>
                                    <div className={`col-span-1 text-right font-mono text-sm font-semibold ${groupSaldo >= 0 ? "text-zinc-200" : "text-rose-400"}`}>
                                        {fmt(Math.abs(groupSaldo))}
                                        {groupSaldo < 0 && <span className="text-xs ml-0.5">H</span>}
                                    </div>
                                </button>

                                {/* Account rows */}
                                {isOpen && group.accounts
                                    .sort((a, b) => a.code.localeCompare(b.code))
                                    .map(acct => {
                                        const saldo = acct.debit - acct.credit;
                                        return (
                                            <div key={acct.code} className="grid grid-cols-12 gap-4 px-6 py-2.5 bg-[#161618]/30 hover:bg-white/[0.01] border-t border-[#27272a]/50 transition-colors">
                                                <div className="col-span-5 flex items-center gap-2 pl-6">
                                                    <span className="font-bold font-mono text-indigo-400 text-sm w-10 flex-shrink-0">{acct.code}</span>
                                                    <span className="text-zinc-400 text-sm truncate">{acct.name}</span>
                                                </div>
                                                <div className="col-span-3 text-right font-mono text-sm text-zinc-400">{fmt(acct.debit)}</div>
                                                <div className="col-span-3 text-right font-mono text-sm text-zinc-400">{fmt(acct.credit)}</div>
                                                <div className={`col-span-1 text-right font-mono text-sm ${saldo >= 0 ? "text-zinc-300" : "text-rose-400"}`}>
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
