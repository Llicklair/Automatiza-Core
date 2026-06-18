"use client";

import { useTranslations } from "next-intl";
import { Send, Loader2, CheckCircle2, AlertCircle, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/ui/button";
import { useRemesas, TYPE_CONFIG, type RemesaType } from "./_hooks/useRemesas";
import RemesaItemList from "./_components/RemesaItemList";
import RemesaSummary from "./_components/RemesaSummary";
import RemesaModal from "./_components/RemesaModal";
import RemesaHistorial from "./_components/RemesaHistorial";
import { PageContainer } from "@/components/shared/PageContainer";

const fmt = (v: number) =>
    new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" }).format(v);

export default function RemesasPage() {
    const t = useTranslations("tesoreria");
    const tc = useTranslations("common");
    const {
        loading, items, activeType, setActiveType, showModal, setShowModal,
        toast, setToast, agent, filtered, selected, totalSelected,
        toggle, selectAll, deselectAll, clearSelection, handleGenerar,
    } = useRemesas();

    return (
        <PageContainer className="animate-in fade-in duration-500">
            <PageHeader
                title={t("remesas.title")}
                description={t("remesas.description")}
                icon={Send}
                actions={
                    <Button
                        onClick={handleGenerar}
                        disabled={selected.length === 0 || agent.status === "creating" || agent.status === "polling"}
                    >
                        {(agent.status === "creating" || agent.status === "polling")
                            ? <Loader2 className="w-4 h-4 animate-spin mr-2" />
                            : <Send className="w-4 h-4 mr-2" />}
                        {selected.length > 0 ? t("remesas.generateRemesa", { total: fmt(totalSelected) }) : t("remesas.selectConcepts")}
                    </Button>
                }
            />

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                <div className="lg:col-span-2 space-y-4">
                    {/* Type tabs */}
                    <div className="flex gap-2">
                        {(["pagos", "cobros", "nominas"] as RemesaType[]).map(t => {
                            const c = TYPE_CONFIG[t];
                            const count = items.filter(i => i.type === t).length;
                            return (
                                <Button key={t} variant="ghost" onClick={() => setActiveType(t)}
                                    className={cn("px-4 py-2 h-auto text-sm font-medium border transition-all",
                                        activeType === t ? `${c.color} ${c.border} ${c.bg} hover:${c.bg}` : "text-muted-foreground border-border hover:text-foreground")}>
                                    {c.label} ({count})
                                </Button>
                            );
                        })}
                    </div>

                    <RemesaItemList filtered={filtered} activeType={activeType} loading={loading}
                        onToggle={toggle} onSelectAll={selectAll} onDeselectAll={deselectAll} />
                </div>

                <div className="space-y-5">
                    <RemesaSummary selected={selected} totalSelected={totalSelected} />
                    <RemesaHistorial />
                    <div className="bg-card border border-border rounded-2xl p-5">
                        <h3 className="text-sm font-semibold text-foreground mb-4">{t("remesas.sepaConfigTitle")}</h3>
                        <div className="space-y-3 text-xs">
                            <div className="flex justify-between"><span className="text-muted-foreground">{t("remesas.creditorId")}</span><span className="font-mono text-foreground">ES99000B00000000</span></div>
                            <div className="flex justify-between"><span className="text-muted-foreground">{t("remesas.defaultBank")}</span><span className="text-foreground">BBVA Empresas</span></div>
                            <div className="flex justify-between"><span className="text-muted-foreground">{t("remesas.scheme")}</span><span className="text-foreground">SEPA Credit Transfer (SCT)</span></div>
                            <div className="flex justify-between"><span className="text-muted-foreground">{t("remesas.jointSignature")}</span><span className="text-emerald-400 font-medium">{t("remesas.jointSignatureEnabled")}</span></div>
                        </div>
                    </div>
                    <div className="rounded-2xl border border-blue-500/20 bg-blue-500/5 p-5">
                        <h3 className="text-xs font-semibold text-blue-400 mb-2">{t("remesas.automationTitle")}</h3>
                        <p className="text-xs text-muted-foreground leading-relaxed">
                            {t("remesas.automationDescription")}
                        </p>
                    </div>
                </div>
            </div>

            {showModal && (
                <RemesaModal agentStatus={agent.status} agentError={agent.error}
                    selectedCount={selected.length} totalSelected={totalSelected}
                    onClose={() => setShowModal(false)}
                    onCloseAndReset={() => { setShowModal(false); agent.reset(); clearSelection(); }} />
            )}

            {toast && (
                <div className={cn("fixed bottom-6 right-6 z-50 flex items-center gap-3 px-5 py-3 rounded-2xl shadow-2xl text-sm font-medium",
                    toast.type === "ok" ? "bg-emerald-500/10 border border-emerald-500/20 text-emerald-400" : "bg-red-500/10 border border-red-500/20 text-red-400")}>
                    {toast.type === "ok" ? <CheckCircle2 className="w-5 h-5" /> : <AlertCircle className="w-5 h-5" />}
                    {toast.msg}
                    <Button variant="ghost" size="icon" className="h-6 w-6 opacity-60 hover:opacity-100" onClick={() => setToast(null)} aria-label={tc("close")}><X className="w-4 h-4" aria-hidden="true" /></Button>
                </div>
            )}
        </PageContainer>
    );
}
