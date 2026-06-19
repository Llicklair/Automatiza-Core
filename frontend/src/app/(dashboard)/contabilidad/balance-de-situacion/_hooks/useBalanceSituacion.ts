"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { api, type JournalEntry } from "@/lib/api";
import { logError } from "@/lib/logger";

export interface AccountBalance {
    code: string;
    name: string;
    saldo: number;
    side: "activo" | "pasivo" | "patrimonio" | "result";
    section: string;
    subsection: string;
}

type Translate = ReturnType<typeof useTranslations>;

function classify(code: string, t: Translate): { section: string; subsection: string; side: "activo" | "pasivo" | "patrimonio" | "result" } {
    const g = code.charAt(0);
    const sub2 = code.substring(0, 2);

    if (g === "6" || g === "7") return { section: t("balance.sectionPatrimonioNeto"), subsection: t("balance.subResultadoEjercicio"), side: "result" };
    if (g === "1") return { section: t("balance.sectionPatrimonioNeto"), subsection: t("balance.subCapitalReservas"), side: "patrimonio" };
    if (g === "2") return { section: t("balance.sectionActivoNoCorriente"), subsection: t("balance.subInmovilizado"), side: "activo" };
    if (g === "3") return { section: t("balance.sectionActivoCorriente"), subsection: t("balance.subExistencias"), side: "activo" };

    if (sub2 === "43" || sub2 === "44") return { section: t("balance.sectionActivoCorriente"), subsection: t("balance.subDeudoresComerciales"), side: "activo" };
    if (sub2 === "40" || sub2 === "41") return { section: t("balance.sectionPasivoCorriente"), subsection: t("balance.subAcreedoresComerciales"), side: "pasivo" };
    if (g === "4") {
        const n = parseInt(sub2);
        if (n >= 47) return { section: t("balance.sectionPasivoCorriente"), subsection: t("balance.subAdministracionesPublicas"), side: "pasivo" };
        return { section: t("balance.sectionActivoCorriente"), subsection: t("balance.subOtrasCuentasDeudoras"), side: "activo" };
    }

    if (sub2 === "57" || sub2 === "56") return { section: t("balance.sectionActivoCorriente"), subsection: t("balance.subTesoreria"), side: "activo" };
    if (sub2 === "52" || sub2 === "53") return { section: t("balance.sectionPasivoCorriente"), subsection: t("balance.subDeudasFinancierasCp"), side: "pasivo" };
    if (sub2 === "50" || sub2 === "51") return { section: t("balance.sectionPasivoNoCorriente"), subsection: t("balance.subDeudasFinancierasLp"), side: "pasivo" };
    if (g === "5") return { section: t("balance.sectionActivoCorriente"), subsection: t("balance.subInversionesFinancieras"), side: "activo" };

    return { section: t("balance.sectionActivoCorriente"), subsection: t("balance.subOtrosActivos"), side: "activo" };
}

export function useBalanceSituacion() {
    const t = useTranslations("contabilidad");
    const [entries, setEntries] = useState<JournalEntry[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        api.accounting.journal.list()
            .then(setEntries)
            .catch(err => logError("contabilidad/balance", err))
            .finally(() => setLoading(false));
    }, []);

    const accountMap: Record<string, AccountBalance> = {};
    entries.forEach(entry => {
        entry.lines.forEach(line => {
            const code3 = line.account_code.substring(0, 3);
            const cls = classify(line.account_code, t);
            if (!accountMap[code3]) {
                accountMap[code3] = { code: code3, name: line.account_name || t("balance.cuentaFallback", { code: code3 }), saldo: 0, ...cls };
            }
            accountMap[code3].saldo += Number(line.debit) - Number(line.credit);
        });
    });

    Object.values(accountMap).forEach(acc => {
        if (acc.side === "pasivo" || acc.side === "patrimonio") {
            acc.saldo = -acc.saldo;
        }
        if (acc.side === "result") {
            const g = acc.code.charAt(0);
            if (g === "7") acc.saldo = -acc.saldo;
        }
    });

    const accounts = Object.values(accountMap).filter(a => Math.abs(a.saldo) > 0.005);

    const ingresosTotal = accounts.filter(a => a.code.charAt(0) === "7").reduce((s, a) => s + a.saldo, 0);
    const gastosTotal = accounts.filter(a => a.code.charAt(0) === "6").reduce((s, a) => s + Math.abs(a.saldo), 0);
    const resultadoEjercicio = ingresosTotal - gastosTotal;

    function groupBySub(filter: (a: AccountBalance) => boolean) {
        const subs: Record<string, AccountBalance[]> = {};
        accounts.filter(filter).forEach(acc => {
            if (!subs[acc.subsection]) subs[acc.subsection] = [];
            subs[acc.subsection].push(acc);
        });
        return Object.entries(subs).map(([subsection, accs]) => ({ subsection, accounts: accs }));
    }

    const activoItems = groupBySub(a => a.side === "activo");
    const pasivoItems = groupBySub(a => a.side === "pasivo");
    const pnItems = groupBySub(a => a.side === "patrimonio");

    const totalActivo = accounts.filter(a => a.side === "activo").reduce((s, a) => s + a.saldo, 0);
    const totalPasivo = accounts.filter(a => a.side === "pasivo").reduce((s, a) => s + a.saldo, 0);
    const totalPN = accounts.filter(a => a.side === "patrimonio").reduce((s, a) => s + a.saldo, 0) + resultadoEjercicio;
    const totalPasivoPN = totalPasivo + totalPN;
    const isEmpty = entries.length === 0;

    return {
        loading, isEmpty,
        activoItems, pasivoItems, pnItems,
        totalActivo, totalPasivo, totalPN, totalPasivoPN,
        resultadoEjercicio,
    };
}
