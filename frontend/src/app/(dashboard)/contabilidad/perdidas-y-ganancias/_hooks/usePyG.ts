"use client";

import { useEffect, useState } from "react";
import { api, type JournalEntry } from "@/lib/api";
import { logError } from "@/lib/logger";

const ACCOUNT_NAMES: Record<string, string> = {
    "600": "Compras de mercaderías",
    "601": "Compras de materias primas",
    "602": "Compras de otros aprovisionamientos",
    "606": "Descuentos sobre compras",
    "610": "Variación de existencias de mercaderías",
    "620": "Gastos en investigación y desarrollo",
    "621": "Arrendamientos y cánones",
    "622": "Reparaciones y conservación",
    "623": "Servicios de profesionales independientes",
    "624": "Transportes",
    "625": "Primas de seguros",
    "626": "Servicios bancarios y similares",
    "627": "Publicidad, propaganda y relaciones públicas",
    "628": "Suministros (luz, agua, internet)",
    "629": "Otros servicios",
    "630": "Impuesto sobre beneficios",
    "640": "Sueldos y salarios",
    "641": "Indemnizaciones",
    "642": "Seguridad Social a cargo de la empresa",
    "649": "Otros gastos sociales",
    "650": "Pérdidas de créditos comerciales incobrables",
    "660": "Gastos financieros",
    "681": "Amortización del inmovilizado material",
    "682": "Amortización del inmovilizado intangible",
    "700": "Ventas de mercaderías",
    "701": "Ventas de productos terminados",
    "702": "Ventas de productos semiterminados",
    "703": "Ventas de subproductos y residuos",
    "704": "Ventas de envases y embalajes",
    "705": "Prestaciones de servicios",
    "706": "Descuentos sobre ventas",
    "708": "Devoluciones de ventas",
    "709": "Rappels sobre ventas",
    "740": "Subvenciones, donaciones y legados",
    "746": "Subvenciones, donaciones y legados transferidos al resultado",
    "751": "Resultados de operaciones en común",
    "760": "Ingresos de participaciones en instrumentos de patrimonio",
    "761": "Ingresos de valores representativos de deuda",
    "762": "Ingresos de créditos",
    "769": "Otros ingresos financieros",
    "790": "Reversión del deterioro de activos",
};

export { ACCOUNT_NAMES };

export function usePyG() {
    const [entries, setEntries] = useState<JournalEntry[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        api.accounting.journal.list()
            .then(setEntries)
            .catch(err => logError("contabilidad/pyl", err))
            .finally(() => setLoading(false));
    }, []);

    const balances: Record<string, { name: string; debit: number; credit: number; group: string }> = {};
    entries.forEach(entry => {
        entry.lines.forEach(line => {
            const g = line.account_code.substring(0, 1);
            if (!["6", "7"].includes(g)) return;
            const code3 = line.account_code.substring(0, 3);
            if (!balances[code3]) {
                balances[code3] = {
                    name: ACCOUNT_NAMES[code3] || line.account_name || `Cuenta ${code3}`,
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
