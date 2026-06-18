"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { api, type JournalEntry } from "@/lib/api";
import { logError } from "@/lib/logger";

type Translate = ReturnType<typeof useTranslations>;

const accountNames = (t: Translate): Record<string, string> => ({
    "600": t("perdidasGanancias.account600"),
    "601": t("perdidasGanancias.account601"),
    "602": t("perdidasGanancias.account602"),
    "606": t("perdidasGanancias.account606"),
    "610": t("perdidasGanancias.account610"),
    "620": t("perdidasGanancias.account620"),
    "621": t("perdidasGanancias.account621"),
    "622": t("perdidasGanancias.account622"),
    "623": t("perdidasGanancias.account623"),
    "624": t("perdidasGanancias.account624"),
    "625": t("perdidasGanancias.account625"),
    "626": t("perdidasGanancias.account626"),
    "627": t("perdidasGanancias.account627"),
    "628": t("perdidasGanancias.account628"),
    "629": t("perdidasGanancias.account629"),
    "630": t("perdidasGanancias.account630"),
    "640": t("perdidasGanancias.account640"),
    "641": t("perdidasGanancias.account641"),
    "642": t("perdidasGanancias.account642"),
    "649": t("perdidasGanancias.account649"),
    "650": t("perdidasGanancias.account650"),
    "660": t("perdidasGanancias.account660"),
    "681": t("perdidasGanancias.account681"),
    "682": t("perdidasGanancias.account682"),
    "700": t("perdidasGanancias.account700"),
    "701": t("perdidasGanancias.account701"),
    "702": t("perdidasGanancias.account702"),
    "703": t("perdidasGanancias.account703"),
    "704": t("perdidasGanancias.account704"),
    "705": t("perdidasGanancias.account705"),
    "706": t("perdidasGanancias.account706"),
    "708": t("perdidasGanancias.account708"),
    "709": t("perdidasGanancias.account709"),
    "740": t("perdidasGanancias.account740"),
    "746": t("perdidasGanancias.account746"),
    "751": t("perdidasGanancias.account751"),
    "760": t("perdidasGanancias.account760"),
    "761": t("perdidasGanancias.account761"),
    "762": t("perdidasGanancias.account762"),
    "769": t("perdidasGanancias.account769"),
    "790": t("perdidasGanancias.account790"),
});

export { accountNames };

export function usePyG() {
    const t = useTranslations("contabilidad");
    const [entries, setEntries] = useState<JournalEntry[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        api.accounting.journal.list()
            .then(setEntries)
            .catch(err => logError("contabilidad/pyl", err))
            .finally(() => setLoading(false));
    }, []);

    const ACCOUNT_NAMES = accountNames(t);
    const balances: Record<string, { name: string; debit: number; credit: number; group: string }> = {};
    entries.forEach(entry => {
        entry.lines.forEach(line => {
            const g = line.account_code.substring(0, 1);
            if (!["6", "7"].includes(g)) return;
            const code3 = line.account_code.substring(0, 3);
            if (!balances[code3]) {
                balances[code3] = {
                    name: ACCOUNT_NAMES[code3] || line.account_name || t("perdidasGanancias.accountFallback", { code: code3 }),
                    debit: 0, credit: 0, group: g,
                };
            }
            balances[code3].debit += Number(line.debit);
            balances[code3].credit += Number(line.credit);
        });
    });

    const incomeAccounts = Object.entries(balances)
        .filter(([_, b]) => b.group === "7")
        .sort(([a], [b]) => a.localeCompare(b));
    const expenseAccounts = Object.entries(balances)
        .filter(([_, b]) => b.group === "6")
        .sort(([a], [b]) => a.localeCompare(b));

    const totalIncome = incomeAccounts.reduce((acc, [_, b]) => acc + (b.credit - b.debit), 0);
    const totalExpense = expenseAccounts.reduce((acc, [_, b]) => acc + (b.debit - b.credit), 0);
    const result = totalIncome - totalExpense;
    const margin = totalIncome > 0 ? ((result / totalIncome) * 100).toFixed(1) : "0.0";
    const noData = !loading && entries.length === 0;

    return { loading, noData, incomeAccounts, expenseAccounts, totalIncome, totalExpense, result, margin };
}
