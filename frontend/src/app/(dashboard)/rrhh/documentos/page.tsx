"use client";

import { useTranslations } from "next-intl";
import { FileText, Plus, Loader2, Send, Wand2 } from "lucide-react";
import { useHRDocumentos, DOC_TYPES, DOC_TEMPLATE_KEYS } from "./_hooks/useHRDocumentos";
import { DocumentCard } from "./_components/DocumentCard";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { PageContainer } from "@/components/shared/PageContainer";

export default function HRDocumentosPage() {
    const t = useTranslations("rrhh");
    const {
        docs, loading, generating, error,
        form, setForm,
        nlText, setNlText,
        employeeFilter, setEmployeeFilter,
        handleNLGenerate, handleGenerate, handleApprove, handleDelete,
    } = useHRDocumentos();

    return (
        <PageContainer>
            <PageHeader
                title={t("documentos.title")}
                description={t("documentos.description")}
                icon={FileText}
            />

            <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
                <div className="lg:col-span-2">
                    <div className="bg-card border border-border rounded-xl p-5 space-y-4 sticky top-6">
                        <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                            <Plus className="w-3.5 h-3.5" /> {t("documentos.generateDocument")}
                        </h2>
                        {/* Atajo NL dentro del formulario: interpreta y rellena los campos de abajo. */}
                        <div className="flex items-center gap-2 bg-background border border-border rounded-lg px-3 py-2">
                            <Wand2 className="w-4 h-4 text-violet-400 shrink-0" />
                            <input
                                value={nlText}
                                onChange={e => setNlText(e.target.value)}
                                onKeyDown={e => e.key === "Enter" && handleNLGenerate()}
                                placeholder={t("documentos.nlPlaceholder")}
                                className="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground focus:outline-none"
                            />
                            <Button size="sm" variant="ghost" onClick={handleNLGenerate} disabled={!nlText.trim()}>
                                <Send className="w-3.5 h-3.5 mr-1.5" />
                                {t("documentos.nlPrepare")}
                            </Button>
                        </div>
                        <p className="text-[11px] text-muted-foreground">{t("documentos.nlHint")}</p>
                        <div className="space-y-1">
                            <label className="text-xs text-muted-foreground">{t("documentos.docType")}</label>
                            <Select
                                value={form.doc_type}
                                onValueChange={v => setForm(f => ({ ...f, doc_type: v, instructions: DOC_TEMPLATE_KEYS[v] ? t(DOC_TEMPLATE_KEYS[v]) : "" }))}
                            >
                                <SelectTrigger className="w-full">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {DOC_TYPES.map(item => <SelectItem key={item.value} value={item.value}>{t(item.labelKey)}</SelectItem>)}
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="space-y-1">
                            <label className="text-xs text-muted-foreground">{t("documentos.employeeName")}</label>
                            <Input
                                value={form.employee_name}
                                onChange={e => setForm(f => ({ ...f, employee_name: e.target.value }))}
                                placeholder={t("documentos.employeeNamePlaceholder")}
                            />
                        </div>
                        <div className="space-y-1">
                            <label className="text-xs text-muted-foreground">{t("documentos.instructions")} <span className="text-muted-foreground/60">{t("documentos.instructionsHint")}</span></label>
                            <textarea value={form.instructions} onChange={e => setForm(f => ({ ...f, instructions: e.target.value }))}
                                placeholder={t("documentos.instructionsPlaceholder")} rows={7}
                                className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-violet-500/50 resize-none" />
                        </div>
                        {error && <p className="text-xs text-red-400">{error}</p>}
                        <div className="p-3 bg-amber-500/5 border border-amber-500/20 rounded-lg">
                            <p className="text-xs text-amber-400/80">{t("documentos.draftWarning")}</p>
                        </div>
                        <Button className="w-full" onClick={handleGenerate} disabled={generating}>
                            {generating && <Loader2 className="w-4 h-4 animate-spin mr-2" />}
                            {generating ? t("documentos.generatingDraft") : t("documentos.generateDraft")}
                        </Button>
                    </div>
                </div>

                <div className="lg:col-span-3 space-y-3">
                    <div className="flex items-center justify-between gap-3">
                        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">{t("documentos.listTitle", { n: docs.length })}</p>
                        <Input
                            value={employeeFilter}
                            onChange={e => setEmployeeFilter(e.target.value)}
                            placeholder={t("documentos.filterByEmployee")}
                            className="w-56 h-8 text-xs"
                        />
                    </div>
                    {loading ? (
                        <div className="flex justify-center py-16"><div className="w-6 h-6 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" /></div>
                    ) : docs.length === 0 ? (
                        <div className="text-center py-16 border-2 border-dashed border-border rounded-xl">
                            <FileText className="w-8 h-8 text-muted-foreground mx-auto mb-3" />
                            <p className="text-muted-foreground text-sm">{t("documentos.empty")}</p>
                        </div>
                    ) : docs.map(doc => (
                        <DocumentCard key={doc.id} doc={doc} onApprove={handleApprove} onDelete={handleDelete} />
                    ))}
                </div>
            </div>
        </PageContainer>
    );
}
