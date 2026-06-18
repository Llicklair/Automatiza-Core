"use client";

import dynamic from "next/dynamic";
import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { FileText, Loader2, Trash2, Eye, FileCode2, Upload, ExternalLink, Copy, PenLine } from "lucide-react";
import { sanitizeHTML } from "@/components/GenerativeUI";
import { documents, ContractPreviewHtml, ContractTemplate } from "@/lib/api/documents";
import { erp } from "@/lib/api/erp";
import { hr } from "@/lib/api/hr";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";
import { cn } from "@/lib/utils";
import { buildContractVariables } from "./templateOptions";

const ContractTemplateEditor = dynamic(
    () => import("@/components/ContractTemplateEditor"),
    { ssr: false }
);

type EntityOption = { id: string; name: string };
type GeneratePanel = {
    tplId: string;
    entityType: "client" | "employee";
    entityId: string;
    entities: EntityOption[];
    loadingEntities: boolean;
    generating: boolean;
};

export default function ContratosTab() {
    const t = useTranslations("plantillas");
    const CONTRACT_VARIABLES = buildContractVariables(t);
    const { show: showToast } = useToastStore();
    const [templates, setTemplates] = useState<ContractTemplate[]>([]);
    const [loading, setLoading] = useState(true);
    const [uploading, setUploading] = useState(false);
    const [panel, setPanel] = useState<GeneratePanel | null>(null);
    const [previewFor, setPreviewFor] = useState<string | null>(null);
    const [previewData, setPreviewData] = useState<ContractPreviewHtml | null>(null);
    const [previewLoading, setPreviewLoading] = useState(false);
    const [editorModal, setEditorModal] = useState<{ id: string; fileName: string; html: string } | null>(null);
    const [openingEditorId, setOpeningEditorId] = useState<string | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const load = async () => {
        setLoading(true);
        try {
            const data = await documents.contractTemplates.list();
            setTemplates(data);
        } catch {
            showToast(t("contracts.toasts.loadError"), "error");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

    const openEditor = async (tpl: ContractTemplate) => {
        if (!tpl.file_name.toLowerCase().endsWith(".docx")) {
            showToast(t("contracts.toasts.editorDocxOnly"), "warning");
            return;
        }
        setOpeningEditorId(tpl.id);
        try {
            const data = await documents.contractTemplates.previewHtml(tpl.id);
            setEditorModal({ id: tpl.id, fileName: tpl.file_name, html: data.html_editable });
        } catch (err: unknown) {
            showToast(err instanceof Error ? err.message : t("contracts.toasts.loadTemplateError"), "error");
        } finally {
            setOpeningEditorId(null);
        }
    };

    const togglePreview = async (tplId: string) => {
        if (previewFor === tplId) { setPreviewFor(null); setPreviewData(null); return; }
        setPreviewFor(tplId);
        setPreviewLoading(true);
        setPreviewData(null);
        try {
            const data = await documents.contractTemplates.previewHtml(tplId);
            setPreviewData(data);
        } catch (err: unknown) {
            showToast(err instanceof Error ? err.message : t("contracts.toasts.previewError"), "error");
            setPreviewFor(null);
        } finally {
            setPreviewLoading(false);
        }
    };

    const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;
        setUploading(true);
        try {
            await documents.contractTemplates.upload(file);
            showToast(t("contracts.toasts.uploadSuccess"), "success");
            await load();
        } catch (err: any) {
            showToast(err?.message ?? t("contracts.toasts.uploadError"), "error");
        } finally {
            setUploading(false);
            if (fileInputRef.current) fileInputRef.current.value = "";
        }
    };

    const handleOpen = (tpl: ContractTemplate) => {
        if (typeof window !== "undefined" && (window as any).electronAPI?.openTemplateNative) {
            (window as any).electronAPI.openTemplateNative(tpl.file_path);
        } else {
            showToast(t("contracts.toasts.desktopOnly"), "warning");
        }
    };

    const handleDelete = async (tpl: ContractTemplate) => {
        const confirmed = await showConfirm({
            title: t("contracts.confirmDelete.title"),
            message: t("contracts.confirmDelete.message", { name: tpl.file_name }),
            confirmLabel: t("contracts.confirmDelete.confirmLabel"),
            confirmVariant: "danger",
        });
        if (!confirmed) return;
        try {
            await documents.contractTemplates.delete(tpl.id);
            showToast(t("contracts.toasts.deleteSuccess"), "success");
            await load();
        } catch {
            showToast(t("contracts.toasts.deleteError"), "error");
        }
    };

    const openGeneratePanel = async (tplId: string, entityType: "client" | "employee") => {
        setPanel({ tplId, entityType, entityId: "", entities: [], loadingEntities: true, generating: false });
        try {
            let entities: EntityOption[];
            if (entityType === "client") {
                const data = await erp.clients.list({ limit: 100 });
                entities = data.map((c: any) => ({ id: c.id, name: c.name }));
            } else {
                const data = await hr.employees.list();
                entities = data.map((e: any) => ({ id: e.id, name: e.name }));
            }
            setPanel(p => p ? { ...p, entities, loadingEntities: false } : null);
        } catch {
            showToast(t("contracts.toasts.entitiesError"), "error");
            setPanel(p => p ? { ...p, loadingEntities: false } : null);
        }
    };

    const handleGenerate = async () => {
        if (!panel || !panel.entityId) return;
        setPanel(p => p ? { ...p, generating: true } : null);
        try {
            const blob = await documents.contractTemplates.generate(panel.tplId, panel.entityType, panel.entityId);
            const tpl = templates.find(t => t.id === panel.tplId);
            const baseName = tpl?.file_name.replace(/\.[^.]+$/, "") ?? "contrato";
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url; a.download = `${baseName}_BORRADOR.docx`; a.click();
            URL.revokeObjectURL(url);
            showToast(t("contracts.toasts.generateSuccess"), "success");
            setPanel(null);
        } catch (err: any) {
            showToast(err?.message ?? t("contracts.toasts.generateError"), "error");
        } finally {
            setPanel(p => p ? { ...p, generating: false } : null);
        }
    };

    const copyVariable = (key: string) => {
        navigator.clipboard.writeText(key).catch(() => {});
        showToast(t("contracts.toasts.copied", { key }), "success");
    };

    return (
        <div className="flex gap-6">
            {editorModal && (
                <ContractTemplateEditor
                    templateId={editorModal.id}
                    fileName={editorModal.fileName}
                    initialHtml={editorModal.html}
                    onClose={() => setEditorModal(null)}
                    onSaved={() => void load()}
                />
            )}
            <div className="flex-1 space-y-3">
                <div className="flex items-center justify-between mb-2">
                    <p className="text-xs text-muted-foreground">
                        {t.rich("contracts.intro", {
                            code: (chunks) => <code className="text-primary">{chunks}</code>,
                        })}
                    </p>
                    <button onClick={() => fileInputRef.current?.click()} disabled={uploading}
                        className="flex items-center gap-2 px-3 py-1.5 bg-primary hover:bg-primary text-foreground text-xs font-medium rounded-lg transition-colors disabled:opacity-50">
                        {uploading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Upload className="w-3.5 h-3.5" />}
                        {t("contracts.uploadDocx")}
                    </button>
                    <input ref={fileInputRef} type="file" accept=".docx,.doc,.odt" className="hidden" onChange={handleUpload} />
                </div>

                {loading ? (
                    <div className="flex items-center justify-center py-12">
                        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
                    </div>
                ) : templates.length === 0 ? (
                    <div onClick={() => fileInputRef.current?.click()}
                        className="flex flex-col items-center justify-center py-16 border-2 border-dashed border-border rounded-xl cursor-pointer hover:border-border transition-colors">
                        <FileCode2 className="w-10 h-10 text-muted-foreground mb-3" />
                        <p className="text-muted-foreground text-sm font-medium">{t("contracts.emptyTitle")}</p>
                        <p className="text-muted-foreground text-xs mt-1">{t("contracts.emptyHint")}</p>
                    </div>
                ) : (
                    <div className="space-y-2">
                        {templates.map(tpl => (
                            <div key={tpl.id} className="bg-card border border-border rounded-xl overflow-hidden">
                                <div className="flex items-center gap-3 p-3 group">
                                    <FileCode2 className="w-8 h-8 text-primary flex-shrink-0" />
                                    <div className="flex-1 min-w-0">
                                        <p className="text-sm text-foreground font-medium truncate">{tpl.file_name}</p>
                                        <p className="text-xs text-muted-foreground">{(tpl.file_size / 1024).toFixed(1)} KB</p>
                                    </div>
                                    <div className="flex items-center gap-1">
                                        <button onClick={() => panel?.tplId === tpl.id ? setPanel(null) : openGeneratePanel(tpl.id, "client")}
                                            className="flex items-center gap-1.5 px-2.5 py-1.5 bg-primary/20 border border-primary/20 text-primary hover:bg-primary/20 text-xs rounded-lg transition-colors">
                                            <FileText className="w-3.5 h-3.5" /> {t("contracts.generateDraft")}
                                        </button>
                                        <button type="button" onClick={() => void openEditor(tpl)} disabled={!!openingEditorId}
                                            className="flex items-center gap-1.5 px-2.5 py-1.5 border border-emerald-600/50 text-emerald-300/90 hover:bg-emerald-950/40 text-xs rounded-lg transition-colors disabled:opacity-50"
                                            title={t("contracts.editTitle")}>
                                            {openingEditorId === tpl.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <PenLine className="w-3.5 h-3.5" />}
                                            {t("contracts.edit")}
                                        </button>
                                        <button type="button" onClick={() => void togglePreview(tpl.id)} disabled={previewLoading && previewFor === tpl.id}
                                            className="flex items-center gap-1.5 px-2.5 py-1.5 border border-border text-foreground hover:bg-muted text-xs rounded-lg transition-colors disabled:opacity-50"
                                            title={t("contracts.previewTitle")}>
                                            {previewLoading && previewFor === tpl.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Eye className="w-3.5 h-3.5" />}
                                            {t("contracts.previewBtn")}
                                        </button>
                                        <button onClick={() => handleOpen(tpl)}
                                            className="flex items-center gap-1.5 px-2.5 py-1.5 border border-border text-muted-foreground hover:text-foreground text-xs rounded-lg transition-colors">
                                            <ExternalLink className="w-3.5 h-3.5" />
                                        </button>
                                        <button onClick={() => handleDelete(tpl)}
                                            className="p-1.5 text-muted-foreground hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all rounded-lg hover:bg-red-500/10">
                                            <Trash2 className="w-3.5 h-3.5" />
                                        </button>
                                    </div>
                                </div>

                                {previewFor === tpl.id && (
                                    <div className="border-t border-border p-3 bg-background space-y-3">
                                        <p className="text-xs text-muted-foreground">
                                            {t.rich("contracts.previewNote", {
                                                code: (chunks) => <code className="text-amber-400/90">{chunks}</code>,
                                            })}
                                        </p>
                                        {previewLoading ? (
                                            <div className="flex items-center gap-2 text-muted-foreground text-sm py-8 justify-center">
                                                <Loader2 className="w-5 h-5 animate-spin" /> {t("contracts.converting")}
                                            </div>
                                        ) : previewData ? (
                                            <div className="flex flex-col lg:flex-row gap-4">
                                                <div className="flex-1 min-h-[180px] max-h-[min(480px,55vh)] overflow-y-auto rounded-lg border border-border bg-card p-4 text-sm text-foreground [&_.apx-docx-var]:ring-1 [&_.apx-docx-var]:ring-amber-500/30"
                                                    dangerouslySetInnerHTML={{ __html: sanitizeHTML(previewData.html) }} />
                                                <div className="w-full lg:w-52 shrink-0 space-y-2">
                                                    <p className="text-[10px] text-muted-foreground uppercase tracking-wide font-medium">{t("contracts.varsInDoc")}</p>
                                                    {previewData.warnings.length > 0 && (
                                                        <div className="text-[10px] text-amber-400/90 bg-amber-500/10 rounded-lg p-2 space-y-1">
                                                            {previewData.warnings.slice(0, 6).map((w, i) => <p key={i} className="leading-snug">{w}</p>)}
                                                        </div>
                                                    )}
                                                    <ul className="text-xs space-y-1.5 max-h-48 overflow-y-auto">
                                                        {previewData.variables_detected.length === 0 ? (
                                                            <li className="text-muted-foreground">
                                                                {t.rich("contracts.noVarsDetected", {
                                                                    code: (chunks) => <code>{chunks}</code>,
                                                                })}
                                                            </li>
                                                        ) : (
                                                            previewData.variables_detected.map(v => (
                                                                <li key={v}><code className="text-amber-400 font-mono text-[11px]">{`{{${v}}}`}</code></li>
                                                            ))
                                                        )}
                                                    </ul>
                                                </div>
                                            </div>
                                        ) : null}
                                    </div>
                                )}

                                {panel?.tplId === tpl.id && (
                                    <div className="border-t border-border p-3 bg-background space-y-3">
                                        <p className="text-xs text-muted-foreground font-medium">{t("contracts.generateFor")}</p>
                                        <div className="flex gap-2">
                                            {(["client", "employee"] as const).map(type => (
                                                <button key={type} onClick={() => openGeneratePanel(tpl.id, type)}
                                                    className={cn("flex-1 py-1.5 text-xs rounded-lg border transition-colors",
                                                        panel.entityType === type ? "border-primary bg-primary/20 text-primary" : "border-border text-muted-foreground hover:border-border")}>
                                                    {type === "client" ? t("contracts.client") : t("contracts.employee")}
                                                </button>
                                            ))}
                                        </div>
                                        {panel.loadingEntities ? (
                                            <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                                <Loader2 className="w-3.5 h-3.5 animate-spin" /> {t("contracts.loading")}
                                            </div>
                                        ) : (
                                            <select value={panel.entityId}
                                                onChange={e => setPanel(p => p ? { ...p, entityId: e.target.value } : null)}
                                                className="w-full bg-card border border-border rounded-lg px-2 py-1.5 text-xs text-foreground focus:outline-none focus:border-primary">
                                                <option value="">{panel.entityType === "client" ? t("contracts.selectClient") : t("contracts.selectEmployee")}</option>
                                                {panel.entities.map(e => <option key={e.id} value={e.id}>{e.name}</option>)}
                                            </select>
                                        )}
                                        <div className="flex gap-2">
                                            <button onClick={handleGenerate} disabled={!panel.entityId || panel.generating}
                                                className="flex-1 flex items-center justify-center gap-1.5 py-1.5 bg-primary hover:bg-primary text-foreground text-xs font-medium rounded-lg transition-colors disabled:opacity-50">
                                                {panel.generating ? <><Loader2 className="w-3.5 h-3.5 animate-spin" /> {t("contracts.generating")}</> : <><FileText className="w-3.5 h-3.5" /> {t("contracts.downloadDraft")}</>}
                                            </button>
                                            <button onClick={() => setPanel(null)}
                                                className="px-3 py-1.5 border border-border text-muted-foreground text-xs rounded-lg hover:text-foreground transition-colors">
                                                {t("contracts.cancel")}
                                            </button>
                                        </div>
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                )}
            </div>

            <div className="w-64 flex-shrink-0">
                <p className="text-xs text-muted-foreground font-medium mb-3 uppercase tracking-wider">{t("contracts.availableVars")}</p>
                <div className="bg-card border border-border rounded-xl p-3 space-y-1">
                    {CONTRACT_VARIABLES.map(v => (
                        <button key={v.key} onClick={() => copyVariable(v.key)}
                            className="w-full flex items-start gap-2 p-2 rounded-lg hover:bg-border transition-colors text-left group" title={t("contracts.clickToCopy")}>
                            <Copy className="w-3 h-3 text-muted-foreground group-hover:text-primary mt-0.5 flex-shrink-0 transition-colors" />
                            <div>
                                <code className="text-xs text-primary font-mono">{v.key}</code>
                                <p className="text-[10px] text-muted-foreground mt-0.5">{v.desc}</p>
                            </div>
                        </button>
                    ))}
                </div>
            </div>
        </div>
    );
}
