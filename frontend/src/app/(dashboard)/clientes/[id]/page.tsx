"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, type Client, type Invoice } from "@/lib/api";
import {
    ArrowLeft, User, Mail, MapPin, Hash, FileText, CheckCircle2,
    Clock, XCircle, Loader2, Plus, ExternalLink
} from "lucide-react";
import Link from "next/link";

const fmt = (n: number) => n.toLocaleString("es-ES", { style: "currency", currency: "EUR" });

const STATUS_ICONS: Record<string, React.ReactNode> = {
    paid: <CheckCircle2 className="w-4 h-4 text-emerald-400" />,
    pending: <Clock className="w-4 h-4 text-amber-400" />,
    cancelled: <XCircle className="w-4 h-4 text-rose-400" />,
    draft: <FileText className="w-4 h-4 text-zinc-400" />,
};

const STATUS_LABELS: Record<string, { label: string; color: string; bg: string; border: string }> = {
    paid: { label: "Pagada", color: "text-emerald-400", bg: "bg-emerald-500/10", border: "border-emerald-500/20" },
    pending: { label: "Pendiente", color: "text-amber-400", bg: "bg-amber-500/10", border: "border-amber-500/20" },
    cancelled: { label: "Cancelada", color: "text-rose-400", bg: "bg-rose-500/10", border: "border-rose-500/20" },
    draft: { label: "Borrador", color: "text-zinc-400", bg: "bg-zinc-500/10", border: "border-zinc-500/20" },
};

export default function ClientDetailPage() {
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
        ]).then(([clients, invs]) => {
            const found = clients.find(c => c.id === id) || null;
            setClient(found);
            setInvoices(invs);
        }).catch(console.error)
            .finally(() => setLoading(false));
    }, [id]);

    if (loading) {
        return (
            <div className="flex items-center justify-center py-32 text-zinc-500 gap-2">
                <Loader2 className="w-5 h-5 animate-spin" /> Cargando contacto…
            </div>
        );
    }

    if (!client) {
        return (
            <div className="p-8 max-w-4xl mx-auto text-center">
                <p className="text-zinc-500">Contacto no encontrado.</p>
                <button onClick={() => router.back()} className="mt-4 text-indigo-400 hover:text-indigo-300 transition-colors text-sm">
                    Volver
                </button>
            </div>
        );
    }

    const totalFacturado = invoices.reduce((acc, inv) => acc + inv.amount_total, 0);
    const totalCobrado = invoices.filter(i => i.status === "paid").reduce((acc, inv) => acc + inv.amount_total, 0);
    const pendiente = invoices.filter(i => i.status === "pending").reduce((acc, inv) => acc + inv.amount_total, 0);

    // Build timeline combining invoices
    const timeline = invoices.map(inv => ({
        date: inv.date,
        type: "invoice" as const,
        title: `Factura ${inv.invoice_number || "sin número"}`,
        subtitle: STATUS_LABELS[inv.status]?.label || inv.status,
        amount: inv.amount_total,
        status: inv.status,
        id: inv.id,
    })).sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());

    return (
        <div className="p-8 max-w-5xl mx-auto space-y-8">
            {/* Back */}
            <button onClick={() => router.back()} className="flex items-center gap-2 text-zinc-500 hover:text-white transition-colors text-sm">
                <ArrowLeft className="w-4 h-4" /> Volver a contactos
            </button>

            {/* Header */}
            <div className="bg-[#111113] border border-[#27272a] rounded-2xl p-8 flex items-start gap-6">
                <div className="w-16 h-16 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center flex-shrink-0">
                    <User className="w-8 h-8 text-indigo-400" />
                </div>
                <div className="flex-1">
                    <div className="flex items-start justify-between">
                        <div>
                            <h1 className="text-2xl font-bold text-white">{client.name}</h1>
                            <div className="flex flex-wrap items-center gap-4 mt-2">
                                {client.nif && (
                                    <span className="flex items-center gap-1.5 text-sm text-zinc-400">
                                        <Hash className="w-3.5 h-3.5 text-zinc-600" /> {client.nif}
                                    </span>
                                )}
                                {client.email && (
                                    <span className="flex items-center gap-1.5 text-sm text-zinc-400">
                                        <Mail className="w-3.5 h-3.5 text-zinc-600" /> {client.email}
                                    </span>
                                )}
                                {(client.city || client.address) && (
                                    <span className="flex items-center gap-1.5 text-sm text-zinc-400">
                                        <MapPin className="w-3.5 h-3.5 text-zinc-600" /> {client.city || client.address}
                                    </span>
                                )}
                            </div>
                        </div>
                        <Link
                            href={`/ventas/facturas/nueva?client=${client.id}`}
                            className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm px-4 py-2 rounded-xl transition-colors"
                        >
                            <Plus className="w-4 h-4" /> Nueva factura
                        </Link>
                    </div>
                </div>
            </div>

            {/* KPIs */}
            <div className="grid grid-cols-3 gap-4">
                <div className="bg-[#111113] border border-[#27272a] rounded-2xl p-5">
                    <p className="text-xs text-zinc-500 uppercase tracking-wider mb-1">Total facturado</p>
                    <p className="text-xl font-bold text-white">{fmt(totalFacturado)}</p>
                    <p className="text-xs text-zinc-600 mt-1">{invoices.length} facturas</p>
                </div>
                <div className="bg-[#111113] border border-[#27272a] rounded-2xl p-5">
                    <p className="text-xs text-zinc-500 uppercase tracking-wider mb-1">Cobrado</p>
                    <p className="text-xl font-bold text-emerald-400">{fmt(totalCobrado)}</p>
                    <p className="text-xs text-zinc-600 mt-1">{invoices.filter(i => i.status === "paid").length} facturas pagadas</p>
                </div>
                <div className={`rounded-2xl p-5 border ${pendiente > 0 ? "bg-amber-500/10 border-amber-500/20" : "bg-[#111113] border-[#27272a]"}`}>
                    <p className={`text-xs uppercase tracking-wider mb-1 ${pendiente > 0 ? "text-amber-400" : "text-zinc-500"}`}>Pendiente de cobro</p>
                    <p className={`text-xl font-bold ${pendiente > 0 ? "text-amber-400" : "text-white"}`}>{fmt(pendiente)}</p>
                    <p className="text-xs text-zinc-600 mt-1">{invoices.filter(i => i.status === "pending").length} facturas</p>
                </div>
            </div>

            {/* Timeline */}
            <div>
                <h2 className="text-base font-bold text-white mb-4">Historial de actividad</h2>
                {timeline.length === 0 ? (
                    <div className="bg-[#111113] border border-[#27272a] rounded-2xl p-12 text-center">
                        <FileText className="w-10 h-10 text-zinc-700 mx-auto mb-3" />
                        <p className="text-zinc-500 text-sm">Aún no hay actividad con este contacto.</p>
                    </div>
                ) : (
                    <div className="relative">
                        {/* Vertical line */}
                        <div className="absolute left-6 top-0 bottom-0 w-px bg-[#27272a]" />

                        <div className="space-y-4 pl-16">
                            {timeline.map((event, i) => {
                                const st = STATUS_LABELS[event.status];
                                return (
                                    <div key={i} className="relative">
                                        {/* Dot */}
                                        <div className="absolute -left-10 top-3 w-8 h-8 rounded-full bg-[#111113] border border-[#27272a] flex items-center justify-center">
                                            {STATUS_ICONS[event.status]}
                                        </div>
                                        {/* Card */}
                                        <div className="bg-[#111113] border border-[#27272a] rounded-xl p-4 hover:border-[#3f3f46] transition-colors">
                                            <div className="flex items-center justify-between">
                                                <div className="flex items-center gap-3">
                                                    <div>
                                                        <p className="text-sm font-medium text-white">{event.title}</p>
                                                        <p className="text-xs text-zinc-500 mt-0.5">
                                                            {new Date(event.date).toLocaleDateString("es-ES", { day: "numeric", month: "long", year: "numeric" })}
                                                        </p>
                                                    </div>
                                                    <span className={`text-xs px-2 py-0.5 rounded-full ${st?.bg} ${st?.border} border ${st?.color}`}>
                                                        {st?.label}
                                                    </span>
                                                </div>
                                                <div className="flex items-center gap-3">
                                                    <span className="text-sm font-bold text-white font-mono">{fmt(event.amount)}</span>
                                                    <Link
                                                        href={`/ventas/facturas/${event.id}`}
                                                        className="p-1.5 rounded-lg hover:bg-white/10 text-zinc-500 hover:text-white transition-colors"
                                                    >
                                                        <ExternalLink className="w-3.5 h-3.5" />
                                                    </Link>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
