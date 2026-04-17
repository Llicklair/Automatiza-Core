"use client";

import { useEffect, useState } from "react";
import { api, type JournalEntry } from "@/lib/api";
import { logError } from "@/lib/logger";

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

export interface AccountNode {
    code: string;
    name: string;
    debit: number;
    credit: number;
}

export interface GroupNode {
    group: string;
    name: string;
    accounts: AccountNode[];
}

export function useCuadroCuentas() {
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
        accounts: g.accounts.filter(a => !q || a.code.includes(q) || a.name.toLowerCase().includes(q)),
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

    return { loading, noData, search, setSearch, expanded, filteredGroups, toggle, q };
}
