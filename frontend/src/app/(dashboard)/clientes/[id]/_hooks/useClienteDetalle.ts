"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, type Client, type Invoice } from "@/lib/api";
import { logError } from "@/lib/logger";

export type ClienteTimelineEvent = {
    date: string;
    type: "invoice";
    title: string;
    subtitle: string;
    amount: number;
    status: string;
    id: string;
};

const STATUS_LABEL_KEYS: Record<string, string> = {
    paid: "paid",
    pending: "pending",
    cancelled: "cancelled",
    draft: "draft",
};

export function useClienteDetalle(tLabel: (key: any) => string) {
    const { id } = useParams<{ id: string }>();
    const router = useRouter();
    const [client, setClient] = useState<Client | null>(null);
    const [invoices, setInvoices] = useState<Invoice[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!id) return;
        Promise.all([
            api.erp.clients.list({ limit: 200 }),
            api.erp.clients.invoices(id),
        ])
            .then(([clients, invs]) => {
                const found = clients.find((c) => c.id === id) || null;
                setClient(found);
                setInvoices(invs);
            })
            .catch((err) => logError("clientes/detalle", err))
            .finally(() => setLoading(false));
    }, [id]);

    const totalFacturado = invoices.reduce((acc, inv) => acc + inv.amount_total, 0);
    const totalCobrado = invoices
        .filter((i) => i.status === "paid")
        .reduce((acc, inv) => acc + inv.amount_total, 0);
    const pendiente = invoices
        .filter((i) => i.status === "pending")
        .reduce((acc, inv) => acc + inv.amount_total, 0);

    const timeline: ClienteTimelineEvent[] = invoices
        .map((inv) => ({
            date: inv.date,
            type: "invoice" as const,
            title: `${tLabel("invoiceLabel")} ${inv.invoice_number || tLabel("invoiceNoNumber")}`,
            subtitle: STATUS_LABEL_KEYS[inv.status]
                ? tLabel(STATUS_LABEL_KEYS[inv.status] as any)
                : inv.status,
            amount: inv.amount_total,
            status: inv.status,
            id: inv.id,
        }))
        .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());

    return {
        id,
        router,
        client,
        invoices,
        loading,
        totalFacturado,
        totalCobrado,
        pendiente,
        timeline,
    };
}
