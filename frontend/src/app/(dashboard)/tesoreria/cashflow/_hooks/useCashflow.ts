"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { api, type Invoice, type Payroll } from "@/lib/api";
import { logError } from "@/lib/logger";

export type CashflowEvent = {
    date: Date;
    type: "in" | "out";
    amount: number;
    description: string;
    ref: string;
};

export type CashflowFilter = "all" | "in" | "out";

export function useCashflow() {
    const t = useTranslations("tesoreria");
    const [invoices, setInvoices] = useState<Invoice[]>([]);
    const [payrolls, setPayrolls] = useState<Payroll[]>([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState<CashflowFilter>("all");

    const loadData = async () => {
        setLoading(true);
        try {
            const [inv, pay] = await Promise.all([
                api.erp.invoices.list(),
                api.hr.payrolls.list(),
            ]);
            setInvoices(inv);
            setPayrolls(pay);
        } catch (error) {
            logError("tesoreria/cashflow/page", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadData();
    }, []);

    // Build unified cashflow timeline
    const timelineEvents: CashflowEvent[] = [];

    invoices.forEach((inv) => {
        if (inv.status === "draft" || inv.status === "cancelled") return;
        const isIncome = inv.invoice_type === "emitida" || inv.invoice_type === "venta";
        const dateObj = new Date(inv.due_date || inv.date);
        timelineEvents.push({
            date: dateObj,
            type: isIncome ? "in" : "out",
            amount: Number(inv.amount_total) || 0,
            description: t("cashflow.invoiceDescription", { name: inv.client?.name || t("cashflow.defaultClient") }),
            ref: inv.invoice_number || inv.id.substring(0, 8),
        });
    });

    payrolls.forEach((pay) => {
        timelineEvents.push({
            date: new Date(pay.issue_date),
            type: "out",
            amount: Number(pay.net_salary) || 0,
            description: t("cashflow.payrollDescription", { name: pay.employee?.name || t("cashflow.defaultEmployee") }),
            ref: `PAY-${pay.id.substring(0, 5).toUpperCase()}`,
        });
    });

    timelineEvents.sort((a, b) => a.date.getTime() - b.date.getTime());

    const totalIn = timelineEvents.filter((e) => e.type === "in").reduce((acc, curr) => acc + curr.amount, 0);
    const totalOut = timelineEvents.filter((e) => e.type === "out").reduce((acc, curr) => acc + curr.amount, 0);
    const netFlow = totalIn - totalOut;

    const visibleEvents = timelineEvents
        .filter((e) => filter === "all" || e.type === filter)
        .sort((a, b) => b.date.getTime() - a.date.getTime());

    return { loading, filter, setFilter, totalIn, totalOut, netFlow, visibleEvents };
}
