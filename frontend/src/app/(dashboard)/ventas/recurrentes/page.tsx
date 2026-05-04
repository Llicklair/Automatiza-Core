"use client";

import { useRecurrentes, fmt } from "./_hooks/useRecurrentes";
import RecurringList from "./_components/RecurringList";
import RecurringModal from "./_components/RecurringModal";
import { RefreshCw, Plus, Search, Loader2, AlertCircle } from "lucide-react";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function RecurrentesPage() {
    const {
        recurrings, filtered, loading, search, setSearch,
        showModal, setShowModal, editingId, saving, runningId, deletingId,
        form, setForm, clients,
        setLine, addLine, removeLine, lineTotal, totalAmount,
        openNew, openEdit,
        handleSubmit, handleToggleActive, handleRun, handleDelete,
        dueToday, estimatedMonthly,
        t, tc,
    } = useRecurrentes();

    return (
        <div className="p-8 max-w-[1400px] mx-auto space-y-6">
            <PageHeader
                title={t("recurring")}
                description={t("recurringDescription")}
                icon={RefreshCw}
                actions={
                    <Button onClick={openNew}>
                        <Plus className="w-4 h-4 mr-2" /> {t("newRecurring")}
                    </Button>
                }
            />

            <div className="grid grid-cols-3 gap-4">
                <div className="bg-card border border-border rounded-2xl p-5">
                    <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">{t("recurringActiveTemplates")}</p>
                    <p className="text-2xl font-bold text-foreground">{recurrings.filter(r => r.is_active).length}</p>
                </div>
                <div className={`rounded-2xl p-5 border ${dueToday > 0 ? "bg-amber-500/10 border-amber-500/20" : "bg-card border-border"}`}>
                    <p className={`text-xs uppercase tracking-wider mb-1 ${dueToday > 0 ? "text-amber-400" : "text-muted-foreground"}`}>{t("recurringDueToday")}</p>
                    <p className={`text-2xl font-bold ${dueToday > 0 ? "text-amber-400" : "text-foreground"}`}>{dueToday}</p>
                </div>
                <div className="bg-card border border-border rounded-2xl p-5">
                    <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">{t("recurringEstimatedMonthly")}</p>
                    <p className="text-xl font-bold text-emerald-400">{fmt(estimatedMonthly)}</p>
                </div>
            </div>

            {dueToday > 0 && (
                <div className="flex items-center gap-3 bg-amber-500/10 border border-amber-500/20 rounded-xl p-4">
                    <AlertCircle className="w-5 h-5 text-amber-400 flex-shrink-0" />
                    <p className="text-sm text-amber-300">{t("recurringDueWarning", { count: dueToday })}</p>
                </div>
            )}

            <div className="relative">
                <Search className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
                <Input
                    placeholder={t("recurringSearchPlaceholder")}
                    value={search}
                    onChange={e => setSearch(e.target.value)}
                    className="pl-9"
                />
            </div>

            {loading ? (
                <div className="flex items-center justify-center py-24 text-muted-foreground gap-2">
                    <Loader2 className="w-5 h-5 animate-spin" /> {tc("loading")}
                </div>
            ) : filtered.length === 0 ? (
                <div className="bg-card border border-border rounded-2xl p-16 flex flex-col items-center text-center">
                    <RefreshCw className="w-12 h-12 text-muted-foreground mb-4" />
                    <h2 className="text-lg font-bold text-foreground mb-2">{recurrings.length === 0 ? t("recurringEmptyTitle") : tc("noResults")}</h2>
                    <p className="text-sm text-muted-foreground max-w-sm">
                        {recurrings.length === 0 ? t("recurringEmptyDescription") : t("recurringNoResults", { search })}
                    </p>
                    {recurrings.length === 0 && (
                        <Button onClick={openNew} className="mt-6">{t("createTemplate")}</Button>
                    )}
                </div>
            ) : (
                <RecurringList
                    items={filtered}
                    runningId={runningId}
                    deletingId={deletingId}
                    onRun={handleRun}
                    onToggleActive={handleToggleActive}
                    onEdit={openEdit}
                    onDelete={handleDelete}
                    t={t}
                />
            )}

            {showModal && (
                <RecurringModal
                    form={form} setForm={setForm} editingId={editingId}
                    clients={clients} saving={saving}
                    lineTotal={lineTotal} totalAmount={totalAmount}
                    onSubmit={handleSubmit} onClose={() => setShowModal(false)}
                    setLine={setLine} addLine={addLine} removeLine={removeLine}
                    t={t} tc={tc}
                />
            )}
        </div>
    );
}
