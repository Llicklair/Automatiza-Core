import type { Client } from "@/lib/api";
import { useTranslations } from "next-intl";

interface InvoiceHeaderProps {
    clients: Client[];
    clientId: string;
    setClientId: (v: string) => void;
    invoiceNumber: string;
    setInvoiceNumber: (v: string) => void;
    date: string;
    setDate: (v: string) => void;
    dueDate: string;
    setDueDate: (v: string) => void;
    notes: string;
    setNotes: (v: string) => void;
}

export default function InvoiceHeader({
    clients, clientId, setClientId, invoiceNumber, setInvoiceNumber,
    date, setDate, dueDate, setDueDate, notes, setNotes,
}: InvoiceHeaderProps) {
    const t = useTranslations("ventas");

    return (
        <div className="bg-card border border-border rounded-2xl p-6 grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
                <label className="block text-xs font-medium text-muted-foreground mb-1.5">{t("client")} *</label>
                <select
                    value={clientId}
                    onChange={e => setClientId(e.target.value)}
                    required
                    className="w-full bg-muted border border-border rounded-xl px-3 py-2.5 text-foreground text-sm outline-none focus:border-primary/20"
                >
                    <option value="">Seleccionar cliente...</option>
                    {clients.map(c => (
                        <option key={c.id} value={c.id}>{c.name}{c.nif ? ` (${c.nif})` : ""}</option>
                    ))}
                </select>
            </div>
            <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1.5">{t("invoiceNumber")}</label>
                <input
                    type="text"
                    value={invoiceNumber}
                    onChange={e => setInvoiceNumber(e.target.value)}
                    placeholder="Ej: F-2024-001 (opcional)"
                    className="w-full bg-muted border border-border rounded-xl px-3 py-2.5 text-foreground text-sm outline-none focus:border-primary/20"
                />
            </div>
            <div>{/* spacer */}</div>
            <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1.5">{t("issueDate")} *</label>
                <input
                    type="date"
                    value={date}
                    onChange={e => setDate(e.target.value)}
                    required
                    className="w-full bg-muted border border-border rounded-xl px-3 py-2.5 text-foreground text-sm outline-none focus:border-primary/20"
                />
            </div>
            <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1.5">{t("dueDate")}</label>
                <input
                    type="date"
                    value={dueDate}
                    onChange={e => setDueDate(e.target.value)}
                    className="w-full bg-muted border border-border rounded-xl px-3 py-2.5 text-foreground text-sm outline-none focus:border-primary/20"
                />
            </div>
            <div className="sm:col-span-2">
                <label className="block text-xs font-medium text-muted-foreground mb-1.5">{t("internalNotes")}</label>
                <textarea
                    value={notes}
                    onChange={e => setNotes(e.target.value)}
                    rows={2}
                    placeholder="Observaciones o condiciones de pago..."
                    className="w-full bg-muted border border-border rounded-xl px-3 py-2.5 text-foreground text-sm outline-none focus:border-primary/20 resize-none"
                />
            </div>
        </div>
    );
}
