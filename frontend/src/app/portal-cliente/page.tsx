"use client";

import { useEffect, useState } from "react";
import { Download, FileText, Loader2, LogOut } from "lucide-react";
import { clientPortal } from "@/lib/api/client_portal";
import type { PortalClientData } from "@/lib/api/client_portal";
import { useToast } from "@/stores/toast";

const fmt = (n: number) =>
    new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" }).format(n);

const fmtDate = (d: string | null) =>
    d ? new Date(d).toLocaleDateString("es-ES", { day: "2-digit", month: "short", year: "numeric" }) : "—";

const STATUS_LABEL: Record<string, { label: string; cls: string }> = {
    draft:  { label: "Borrador",  cls: "bg-muted/40 text-muted-foreground" },
    sent:   { label: "Enviada",   cls: "bg-blue-500/10 text-blue-400" },
    paid:   { label: "Pagada",    cls: "bg-emerald-500/10 text-emerald-400" },
    overdue:{ label: "Vencida",   cls: "bg-red-500/10 text-red-400" },
    accepted: { label: "Aceptado", cls: "bg-emerald-500/10 text-emerald-400" },
    rejected: { label: "Rechazado", cls: "bg-red-500/10 text-red-400" },
};

type PageState = "loading" | "auth_error" | "ready" | "error";

export default function PortalClientePage() {
    const [state, setState] = useState<PageState>("loading");
    const [data, setData] = useState<PortalClientData | null>(null);
    const [downloading, setDownloading] = useState<string | null>(null);
    const [tab, setTab] = useState<"invoices" | "quotes">("invoices");
    const toast = useToast();

    useEffect(() => {
        (async () => {
            const params = new URLSearchParams(window.location.search);
            const rawToken = params.get("token");

            // Try existing session first
            if (clientPortal.isAuthenticated()) {
                try {
                    setData(await clientPortal.me());
                    setState("ready");
                    return;
                } catch {
                    clientPortal.logout();
                }
            }

            if (!rawToken) {
                setState("auth_error");
                return;
            }

            const ok = await clientPortal.authenticate(rawToken);
            if (!ok) {
                setState("auth_error");
                return;
            }

            try {
                setData(await clientPortal.me());
                setState("ready");
            } catch {
                setState("error");
            }
        })();
    }, []);

    const handleDownload = async (invoiceId: string, invoiceNumber: string | null) => {
        setDownloading(invoiceId);
        try {
            await clientPortal.downloadInvoicePdf(invoiceId, invoiceNumber);
        } catch {
            toast.error("Error al descargar la factura");
        } finally {
            setDownloading(null);
        }
    };

    const handleLogout = () => {
        clientPortal.logout();
        window.location.reload();
    };

    if (state === "loading") {
        return (
            <div className="min-h-screen bg-gray-950 flex items-center justify-center">
                <div className="flex items-center gap-3 text-gray-400">
                    <Loader2 className="w-5 h-5 animate-spin" />
                    <span className="text-sm">Accediendo al portal…</span>
                </div>
            </div>
        );
    }

    if (state === "auth_error") {
        return (
            <div className="min-h-screen bg-gray-950 flex items-center justify-center p-4">
                <div className="bg-gray-900 border border-gray-800 rounded-2xl p-8 max-w-sm w-full text-center space-y-3">
                    <div className="text-4xl">🔒</div>
                    <h1 className="text-white font-semibold text-lg">Enlace inválido o expirado</h1>
                    <p className="text-gray-400 text-sm">
                        Este enlace no es válido o ya ha expirado. Contacta con la empresa para solicitar un nuevo acceso.
                    </p>
                </div>
            </div>
        );
    }

    if (state === "error" || !data) {
        return (
            <div className="min-h-screen bg-gray-950 flex items-center justify-center p-4">
                <div className="bg-gray-900 border border-gray-800 rounded-2xl p-8 max-w-sm w-full text-center space-y-3">
                    <p className="text-gray-400 text-sm">Error al cargar tus datos. Inténtalo de nuevo.</p>
                </div>
            </div>
        );
    }

    const { client, invoices, quotes } = data;

    return (
        <div className="min-h-screen bg-gray-950 text-gray-100">
            {/* Header */}
            <header className="border-b border-gray-800 bg-gray-900">
                <div className="max-w-3xl mx-auto px-4 py-4 flex items-center justify-between">
                    <div>
                        <h1 className="font-semibold text-white text-lg">{client.name}</h1>
                        {client.email && <p className="text-xs text-gray-400">{client.email}</p>}
                    </div>
                    <button
                        onClick={handleLogout}
                        className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-white transition-colors"
                    >
                        <LogOut className="w-3.5 h-3.5" /> Cerrar sesión
                    </button>
                </div>
            </header>

            <main className="max-w-3xl mx-auto px-4 py-8 space-y-6">
                {/* Tabs */}
                <div className="flex gap-1 p-1 rounded-xl bg-gray-900 border border-gray-800 w-fit">
                    {(["invoices", "quotes"] as const).map((t) => (
                        <button
                            key={t}
                            onClick={() => setTab(t)}
                            className={`px-5 py-2 rounded-lg text-sm font-medium transition-all
                                ${tab === t ? "bg-indigo-600 text-white shadow" : "text-gray-400 hover:text-white"}`}
                        >
                            {t === "invoices" ? `Facturas (${invoices.length})` : `Presupuestos (${quotes.length})`}
                        </button>
                    ))}
                </div>

                {/* Invoices */}
                {tab === "invoices" && (
                    invoices.length === 0 ? (
                        <div className="flex flex-col items-center justify-center h-40 rounded-xl border border-gray-800 gap-2 text-gray-500">
                            <FileText className="w-6 h-6 opacity-40" />
                            <p className="text-sm">No hay facturas</p>
                        </div>
                    ) : (
                        <div className="rounded-xl border border-gray-800 bg-gray-900 overflow-hidden">
                            <table className="w-full text-sm">
                                <thead>
                                    <tr className="border-b border-gray-800 text-gray-500 text-xs uppercase tracking-wide">
                                        <th className="px-4 py-3 text-left">Nº Factura</th>
                                        <th className="px-4 py-3 text-left">Fecha</th>
                                        <th className="px-4 py-3 text-left">Vencimiento</th>
                                        <th className="px-4 py-3 text-right">Importe</th>
                                        <th className="px-4 py-3 text-center">Estado</th>
                                        <th className="px-4 py-3 text-right">PDF</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-gray-800">
                                    {invoices.map((inv) => {
                                        const st = STATUS_LABEL[inv.status] ?? { label: inv.status, cls: "bg-muted/40 text-muted-foreground" };
                                        return (
                                            <tr key={inv.id} className="hover:bg-gray-800/40">
                                                <td className="px-4 py-3 font-mono font-medium text-white">
                                                    {inv.invoice_number ?? "S/N"}
                                                </td>
                                                <td className="px-4 py-3 text-gray-400">{fmtDate(inv.date)}</td>
                                                <td className="px-4 py-3 text-gray-400">{fmtDate(inv.due_date)}</td>
                                                <td className="px-4 py-3 text-right font-semibold tabular-nums text-white">
                                                    {fmt(inv.amount_total)}
                                                </td>
                                                <td className="px-4 py-3 text-center">
                                                    <span className={`inline-block px-2 py-0.5 rounded-full text-xs ${st.cls}`}>
                                                        {st.label}
                                                    </span>
                                                </td>
                                                <td className="px-4 py-3 text-right">
                                                    <button
                                                        onClick={() => handleDownload(inv.id, inv.invoice_number)}
                                                        disabled={downloading === inv.id}
                                                        className="text-indigo-400 hover:text-indigo-300 disabled:opacity-40"
                                                        title="Descargar PDF"
                                                    >
                                                        {downloading === inv.id
                                                            ? <Loader2 className="w-4 h-4 animate-spin" />
                                                            : <Download className="w-4 h-4" />}
                                                    </button>
                                                </td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                    )
                )}

                {/* Quotes */}
                {tab === "quotes" && (
                    quotes.length === 0 ? (
                        <div className="flex flex-col items-center justify-center h-40 rounded-xl border border-gray-800 gap-2 text-gray-500">
                            <FileText className="w-6 h-6 opacity-40" />
                            <p className="text-sm">No hay presupuestos</p>
                        </div>
                    ) : (
                        <div className="rounded-xl border border-gray-800 bg-gray-900 overflow-hidden">
                            <table className="w-full text-sm">
                                <thead>
                                    <tr className="border-b border-gray-800 text-gray-500 text-xs uppercase tracking-wide">
                                        <th className="px-4 py-3 text-left">Nº</th>
                                        <th className="px-4 py-3 text-left">Fecha</th>
                                        <th className="px-4 py-3 text-right">Importe</th>
                                        <th className="px-4 py-3 text-center">Estado</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-gray-800">
                                    {quotes.map((q) => {
                                        const st = STATUS_LABEL[q.status] ?? { label: q.status, cls: "" };
                                        return (
                                            <tr key={q.id} className="hover:bg-gray-800/40">
                                                <td className="px-4 py-3 font-mono text-white">{q.quote_number ?? "S/N"}</td>
                                                <td className="px-4 py-3 text-gray-400">{fmtDate(q.date)}</td>
                                                <td className="px-4 py-3 text-right font-semibold text-white tabular-nums">
                                                    {fmt(q.amount_total)}
                                                </td>
                                                <td className="px-4 py-3 text-center">
                                                    <span className={`inline-block px-2 py-0.5 rounded-full text-xs ${st.cls}`}>
                                                        {st.label}
                                                    </span>
                                                </td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                    )
                )}

                <p className="text-xs text-gray-600 text-center">
                    Portal de cliente — acceso seguro y confidencial
                </p>
            </main>
        </div>
    );
}
