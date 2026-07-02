"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { useTranslations } from "next-intl";
import { api, type Invoice, type Payroll, type Task } from "@/lib/api";
import { format } from "date-fns";
import { es } from "date-fns/locale";
import { logError } from "@/lib/logger";
import { useToastStore } from "@/stores/toast";

const fmt = (v: number) =>
    new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" }).format(v);

export type RemesaType = "cobros" | "pagos" | "nominas";

export interface RemesaItem {
    id: string;
    type: RemesaType;
    label: string;
    sublabel: string;
    amount: number;
    date: string;
    selected: boolean;
}

export const TYPE_CONFIG = {
    cobros: { label: "Cobros (B2B)", color: "text-emerald-400", border: "border-emerald-500", bg: "bg-emerald-500/10" },
    pagos: { label: "Pagos a proveedores", color: "text-red-400", border: "border-red-500", bg: "bg-red-500/10" },
    nominas: { label: "Transferencias nominas", color: "text-blue-400", border: "border-blue-500", bg: "bg-blue-500/10" },
} as const;

function useAgentTask() {
    const t = useTranslations("tesoreria");
    const [status, setStatus] = useState<"idle" | "creating" | "polling" | "done" | "failed">("idle");
    const [error, setError] = useState<string | null>(null);
    const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

    const stop = useCallback(() => {
        if (intervalRef.current) { clearInterval(intervalRef.current); intervalRef.current = null; }
    }, []);

    const launch = useCallback(async (intent: string) => {
        stop(); setError(null); setStatus("creating");
        // Pre-traducidos aquí: dentro del interval `t` queda sombreado por la Task.
        const doneMsg = t("remesaModal.successTitle");
        const failMsg = t("remesaModal.unknownError");
        try {
            const task = await api.tasks.create("banking", intent);
            setStatus("polling");
            intervalRef.current = setInterval(async () => {
                try {
                    const t: Task = await api.tasks.get(task.id);
                    if (t.status === "done" || t.status === "failed" || t.status === "cancelled") {
                        stop();
                        setStatus(t.status === "done" ? "done" : "failed");
                        if (t.error_message) setError(t.error_message);
                        // Toast global: el aviso llega aunque el usuario haya navegado.
                        if (t.status === "done") useToastStore.getState().success(doneMsg);
                        else useToastStore.getState().error(t.error_message || failMsg);
                    }
                } catch { /* keep polling */ }
            }, 2000);
        } catch (e) {
            setStatus("failed");
            const msg = e instanceof Error ? e.message : t("remesas.errorCreatingTask");
            setError(msg);
            useToastStore.getState().error(msg);
        }
    }, [stop, t]);

    useEffect(() => () => stop(), [stop]);
    return { launch, status, error, reset: () => { stop(); setStatus("idle"); setError(null); } };
}

export function useRemesas() {
    const t = useTranslations("tesoreria");
    const [loading, setLoading] = useState(true);
    const [items, setItems] = useState<RemesaItem[]>([]);
    const [activeType, setActiveType] = useState<RemesaType>("pagos");
    const [showModal, setShowModal] = useState(false);
    const agent = useAgentTask();

    const loadData = useCallback(async () => {
        setLoading(true);
        try {
            const [inv, pay] = await Promise.all([
                api.erp.invoices.list(),
                api.hr.payrolls.list(),
            ]);

            const newItems: RemesaItem[] = [];

            inv.filter(i => (i.invoice_type === "issued" || i.invoice_type === "emitida" || i.invoice_type === "venta") && i.status === "pending")
                .forEach(i => newItems.push({
                    id: i.id, type: "cobros",
                    label: i.client?.name || t("remesas.invoiceLabel", { number: i.invoice_number || i.id.slice(0, 6) }),
                    sublabel: t("remesas.invoiceSublabel", { number: i.invoice_number || i.id.slice(0, 8) }),
                    amount: Number(i.amount_total),
                    date: i.due_date || i.date,
                    selected: false,
                }));

            inv.filter(i => (i.invoice_type === "received" || i.invoice_type === "recibida" || i.invoice_type === "compra") && i.status !== "paid" && i.status !== "cancelled")
                .forEach(i => newItems.push({
                    id: i.id, type: "pagos",
                    label: i.client?.name || t("remesas.supplierFallback"),
                    sublabel: t("remesas.invoiceSublabel", { number: i.invoice_number || i.id.slice(0, 8) }),
                    amount: Number(i.amount_total),
                    date: i.due_date || i.date,
                    selected: false,
                }));

            pay.filter(p => p.status === "sent")
                .forEach(p => newItems.push({
                    id: p.id, type: "nominas",
                    label: p.employee?.name || t("remesas.employeeFallback"),
                    sublabel: t("remesas.payrollSublabel", { period: format(new Date(p.period_start), "MMM yyyy", { locale: es }) }),
                    amount: Number(p.net_salary),
                    date: p.period_end,
                    selected: false,
                }));

            setItems(newItems);
        } catch (e) {
            logError("tesoreria/remesas/page", e);
        } finally {
            setLoading(false);
        }
    }, [t]);

    useEffect(() => { loadData(); }, [loadData]);

    const filtered = items.filter(i => i.type === activeType);
    const selected = items.filter(i => i.selected);
    const totalSelected = selected.reduce((s, i) => s + i.amount, 0);

    const toggle = (id: string) =>
        setItems(prev => prev.map(i => i.id === id ? { ...i, selected: !i.selected } : i));

    const selectAll = () =>
        setItems(prev => prev.map(i => i.type === activeType ? { ...i, selected: true } : i));

    const deselectAll = () =>
        setItems(prev => prev.map(i => i.type === activeType ? { ...i, selected: false } : i));

    const clearSelection = () =>
        setItems(prev => prev.map(i => ({ ...i, selected: false })));

    const handleGenerar = async () => {
        if (selected.length === 0) return;
        const cobrosItems = selected.filter(i => i.type === "cobros");
        const pagosItems = selected.filter(i => i.type === "pagos");
        const nominasItems = selected.filter(i => i.type === "nominas");

        let intent = `Genera un fichero de remesa SEPA para el banco con los siguientes conceptos:\n`;
        if (cobrosItems.length) intent += `- Cobros (SEPA B2B) por ${fmt(cobrosItems.reduce((s, i) => s + i.amount, 0))} de ${cobrosItems.length} factura(s) emitida(s): ${cobrosItems.map(i => i.sublabel).join(", ")}.\n`;
        if (pagosItems.length) intent += `- Pagos a proveedores por ${fmt(pagosItems.reduce((s, i) => s + i.amount, 0))} de ${pagosItems.length} factura(s) recibida(s): ${pagosItems.map(i => i.label).join(", ")}.\n`;
        if (nominasItems.length) intent += `- Transferencias de nominas por ${fmt(nominasItems.reduce((s, i) => s + i.amount, 0))} para ${nominasItems.map(i => i.label).join(", ")}.\n`;
        intent += `Total remesa: ${fmt(totalSelected)}. Genera el XML SEPA y registra la operacion.`;

        await agent.launch(intent);
        setShowModal(true);
    };

    return {
        loading, items, activeType, setActiveType, showModal, setShowModal,
        agent, filtered, selected, totalSelected,
        toggle, selectAll, deselectAll, clearSelection, handleGenerar,
    };
}
