"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { api, type JournalEntry } from "@/lib/api";
import { logError } from "@/lib/logger";

const groupNames = (t: ReturnType<typeof useTranslations>): Record<string, string> => ({
    "1": t("cuadroCuentas.grupo1"),
    "2": t("cuadroCuentas.grupo2"),
    "3": t("cuadroCuentas.grupo3"),
    "4": t("cuadroCuentas.grupo4"),
    "5": t("cuadroCuentas.grupo5"),
    "6": t("cuadroCuentas.grupo6"),
    "7": t("cuadroCuentas.grupo7"),
    "8": t("cuadroCuentas.grupo8"),
    "9": t("cuadroCuentas.grupo9"),
});

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
    const t = useTranslations("contabilidad");
    const [entries, setEntries] = useState<JournalEntry[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState("");
    const [expanded, setExpanded] = useState<Set<string>>(new Set(["4", "5", "6", "7"]));

    const GROUP_NAMES = groupNames(t);

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
                accountMap[code3] = { code: code3, name: line.account_name || t("cuadroCuentas.cuentaFallback", { code: code3 }), debit: 0, credit: 0 };
            }
            accountMap[code3].debit += Number(line.debit);
            accountMap[code3].credit += Number(line.credit);
        });
    });

    const groupMap: Record<string, GroupNode> = {};
    Object.values(accountMap).forEach(acct => {
        const g = acct.code.substring(0, 1);
        if (!groupMap[g]) {
            groupMap[g] = { group: g, name: GROUP_NAMES[g] || t("cuadroCuentas.grupoFallback", { group: g }), accounts: [] };
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
