"use client";

import { usePresupuestos } from "./_hooks/usePresupuestos";
import QuotesTable from "./_components/QuotesTable";
import QuoteModal from "./_components/QuoteModal";
import QuoteToast from "./_components/QuoteToast";
import { FileText, Plus, Search, Clock } from "lucide-react";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

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
        <div className="p-8 max-w-[1400px] mx-auto space-y-6">
            <PageHeader
                title={t("quotes")}
                description={t("quotesDescription")}
                icon={FileText}
                actions={
                    <div className="flex gap-2">
                        <Button variant="outline" onClick={() => {}}>
                            <Clock className="w-4 h-4 mr-2" /> {t("quoteExpired")}
                        </Button>
                        <Button onClick={() => setShowModal(true)}>
                            <Plus className="w-4 h-4 mr-2" /> {t("newQuote")}
                        </Button>
                    </div>
                }
            />

            <div className="bg-card border border-border rounded-2xl overflow-hidden shadow-xl">
                <div className="p-4 border-b border-border flex justify-between items-center bg-muted/30">
                    <div className="relative">
                        <Search className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
                        <Input
                            placeholder={t("quoteSearchPlaceholder")}
                            className="pl-10 w-72"
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
