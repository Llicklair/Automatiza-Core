"use client";

import { Suspense } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { useTranslations } from "next-intl";
import { useNuevaFactura } from "./_hooks/useNuevaFactura";
import InvoiceHeader from "./_components/InvoiceHeader";
import InvoiceLinesTable from "./_components/InvoiceLinesTable";
import InvoiceTotals from "./_components/InvoiceTotals";

function NuevaFacturaContent() {
    const t = useTranslations("ventas");
    const {
        clients, products, clientId, setClientId,
        invoiceNumber, setInvoiceNumber, date, setDate,
        dueDate, setDueDate, notes, setNotes,
        fiscalRegime, setFiscalRegime,
        lines, submitting, totals,
        addLine, removeLine, updateLine, fillFromProduct, handleSubmit,
    } = useNuevaFactura();

    return (
        <div className="p-8 max-w-5xl mx-auto space-y-8">
            <div className="flex items-center gap-4">
                <Link href="/ventas/facturas" className="p-2 -ml-2 rounded-xl text-muted-foreground hover:text-foreground hover:bg-accent/50 transition-colors">
                    <ArrowLeft className="w-5 h-5" />
                </Link>
                <div>
                    <h1 className="text-3xl font-bold text-foreground">{t("newInvoice")}</h1>
                    <p className="text-muted-foreground text-sm">{t("newInvoiceDescription")}</p>
                </div>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6">
                <InvoiceHeader clients={clients} clientId={clientId} setClientId={setClientId}
                    invoiceNumber={invoiceNumber} setInvoiceNumber={setInvoiceNumber}
                    date={date} setDate={setDate} dueDate={dueDate} setDueDate={setDueDate}
                    notes={notes} setNotes={setNotes}
                    fiscalRegime={fiscalRegime} setFiscalRegime={setFiscalRegime} />

                <InvoiceLinesTable lines={lines} products={products}
                    onAddLine={addLine} onRemoveLine={removeLine}
                    onUpdateLine={updateLine} onFillFromProduct={fillFromProduct} />

                <InvoiceTotals totals={totals} submitting={submitting} />
            </form>
        </div>
    );
}

export default function NuevaFacturaPage() {
    return (
        <Suspense fallback={<div className="p-8 text-muted-foreground">Cargando...</div>}>
            <NuevaFacturaContent />
        </Suspense>
    );
}
