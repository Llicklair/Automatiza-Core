"use client";

import { usePresupuestos } from "./_hooks/usePresupuestos";
import QuotesTable from "./_components/QuotesTable";
import QuoteModal from "./_components/QuoteModal";
import QuoteToast from "./_components/QuoteToast";
import { FileText, Plus, Search, Clock } from "lucide-react";

export default function QuotesPage() {
    const {
        quotes, isLoading, showModal, setShowModal,
        clients, products,
        selectedClient, setSelectedClient,
        validUntil, setValidUntil,
        lines, isSubmitting, convertingId,
        toast, setToast,
        handleCreate, handleConvert, handleDelete, handleStatusChange,
        updateLine, addLine,
        t, tc,
    } = usePresupuestos();

    return (
        <div className="min-h-screen bg-background text-foreground p-8">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-8">
                <div>
                    <h1 className="text-3xl font-light text-foreground flex items-center gap-3">
                        <div className="p-2 bg-primary/10 rounded-xl">
                            <FileText className="w-8 h-8 text-primary" />
                        </div>
                        {t("quotes")}
                    </h1>
                    <p className="text-muted-foreground mt-2 ml-14 text-sm max-w-2xl">
                        {t("quotesDescription")}
                    </p>
                </div>
                <div className="flex gap-3">
                    <button
                        onClick={() => setShowModal(true)}
                        className="flex items-center gap-2 bg-primary hover:bg-primary text-foreground shadow-lg shadow-primary/20 px-5 py-2.5 rounded-full font-medium transition-colors"
                    >
                        <Plus className="w-4 h-4" /> {t("newQuote")}
                    </button>
                    <button className="flex items-center gap-2 bg-card border border-border hover:bg-muted text-foreground px-5 py-2.5 rounded-full font-medium transition-colors">
                        <Clock className="w-4 h-4 text-muted-foreground" /> {t("quoteExpired")}
                    </button>
                </div>
            </div>

            <div className="bg-card border border-border rounded-2xl overflow-hidden shadow-xl">
                <div className="p-4 border-b border-border flex justify-between items-center bg-muted">
                    <div className="relative">
                        <Search className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
                        <input
                            type="text"
                            placeholder={t("quoteSearchPlaceholder")}
                            className="bg-background border border-border text-sm text-foreground rounded-lg pl-10 pr-4 py-2 focus:outline-none focus:border-primary transition-colors w-72"
                        />
                    </div>
                </div>
                <QuotesTable
                    quotes={quotes}
                    isLoading={isLoading}
                    convertingId={convertingId}
                    onConvert={handleConvert}
                    onDelete={handleDelete}
                    onStatusChange={handleStatusChange}
                    t={t}
                />
            </div>

            {showModal && (
                <QuoteModal
                    clients={clients}
                    products={products}
                    selectedClient={selectedClient}
                    onClientChange={setSelectedClient}
                    validUntil={validUntil}
                    onValidUntilChange={setValidUntil}
                    lines={lines}
                    isSubmitting={isSubmitting}
                    onSubmit={handleCreate}
                    onClose={() => setShowModal(false)}
                    onUpdateLine={updateLine}
                    onAddLine={addLine}
                    t={t}
                    tc={tc}
                />
            )}

            {toast && <QuoteToast toast={toast} onClose={() => setToast(null)} />}
        </div>
    );
}
