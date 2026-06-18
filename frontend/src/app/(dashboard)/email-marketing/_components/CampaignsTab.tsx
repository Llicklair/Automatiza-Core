"use client";

import { useState, useEffect, useCallback } from "react";
import { useTranslations } from "next-intl";
import {
    Mail, FileText, Loader2, Plus, Send, Trash2,
    CheckCircle2, Clock, AlertCircle, Eye, EyeOff, Users,
    Calendar,
} from "lucide-react";
import {
    emailMarketingApi,
    type EmailCampaign,
    type EmailTemplate,
} from "@/lib/api/email_marketing";
import { useToastStore } from "@/stores/toast";
import { logError } from "@/lib/logger";
import { errMsg, fmt } from "./constants";

// ── Status config ──────────────────────────────────────────────────────────────

const buildStatusCfg = (t: ReturnType<typeof useTranslations>) => ({
    draft:     { label: t("status.draft"),     color: "text-muted-foreground bg-muted/50 border-border", icon: FileText },
    scheduled: { label: t("status.scheduled"), color: "text-blue-400 bg-blue-500/10 border-blue-500/20", icon: Clock },
    sending:   { label: t("status.sending"),   color: "text-amber-400 bg-amber-500/10 border-amber-500/20", icon: Loader2 },
    sent:      { label: t("status.sent"),      color: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20", icon: CheckCircle2 },
    failed:    { label: t("status.failed"),    color: "text-red-400 bg-red-500/10 border-red-500/20", icon: AlertCircle },
} as const);

// ── Tab: Campañas ──────────────────────────────────────────────────────────────

export default function TabCampaigns() {
    const t = useTranslations("emailMarketing");
    const STATUS_CFG = buildStatusCfg(t);
    const toast = useToastStore();
    const [campaigns, setCampaigns] = useState<EmailCampaign[]>([]);
    const [templates, setTemplates] = useState<EmailTemplate[]>([]);
    const [recipientCount, setRecipientCount] = useState(0);
    const [loading, setLoading] = useState(true);
    const [creating, setCreating] = useState(false);
    const [sending, setSending] = useState<string | null>(null);
    const [form, setForm] = useState({ name: "", subject: "", html_body: "", template_id: "", scheduled_at: "" });
    const [preview, setPreview] = useState(false);

    const load = useCallback(async () => {
        try {
            const [c, t, r] = await Promise.all([
                emailMarketingApi.campaigns.list(),
                emailMarketingApi.templates.list(),
                emailMarketingApi.campaigns.previewCount(),
            ]);
            setCampaigns(c);
            setTemplates(t);
            setRecipientCount(r.count);
        } catch (err) { logError("email-marketing/campaigns", err); } finally { setLoading(false); }
    }, []);

    useEffect(() => { load(); }, [load]);

    const applyTemplate = (id: string) => {
        const tpl = templates.find((tplItem) => tplItem.id === id);
        if (tpl) setForm((f) => ({ ...f, template_id: id, subject: tpl.subject, html_body: tpl.html_body }));
        else setForm((f) => ({ ...f, template_id: "" }));
    };

    const create = async () => {
        if (!form.name || !form.subject || !form.html_body) return;
        setCreating(true);
        try {
            const c = await emailMarketingApi.campaigns.create({
                name: form.name,
                subject: form.subject,
                html_body: form.html_body,
                template_id: form.template_id || undefined,
                scheduled_at: form.scheduled_at || undefined,
            });
            setCampaigns((prev) => [c, ...prev]);
            setForm({ name: "", subject: "", html_body: "", template_id: "", scheduled_at: "" });
            toast.success(t("toasts.created"));
        } catch (err) { toast.error(errMsg(err, t("toasts.createError"))); } finally { setCreating(false); }
    };

    const send = async (id: string) => {
        setSending(id);
        try {
            await emailMarketingApi.campaigns.send(id);
            await load();
            toast.success(t("toasts.sending"));
        } catch (err) { toast.error(errMsg(err, t("toasts.sendError"))); } finally { setSending(null); }
    };

    const remove = async (id: string) => {
        try {
            await emailMarketingApi.campaigns.delete(id);
            setCampaigns((prev) => prev.filter((c) => c.id !== id));
        } catch (err) { toast.error(errMsg(err, t("toasts.deleteError"))); }
    };

    return (
        <div className="space-y-6">
            {/* Formulario nueva campaña */}
            <div className="bg-card border border-border rounded-xl p-5 space-y-4">
                <div className="flex items-center justify-between">
                    <h2 className="text-sm font-semibold text-foreground">{t("form.newCampaign")}</h2>
                    <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                        <Users className="w-3.5 h-3.5" />
                        <span>{t("form.recipients", { count: recipientCount })}</span>
                    </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <input
                        value={form.name}
                        onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                        placeholder={t("form.namePlaceholder")}
                        className="bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-blue-500/50"
                    />
                    <select
                        value={form.template_id}
                        onChange={(e) => applyTemplate(e.target.value)}
                        className="bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-blue-500/50"
                    >
                        <option value="">{t("form.templateOptional")}</option>
                        {templates.map((tpl) => (
                            <option key={tpl.id} value={tpl.id}>{tpl.name}</option>
                        ))}
                    </select>
                </div>

                <input
                    value={form.subject}
                    onChange={(e) => setForm((f) => ({ ...f, subject: e.target.value }))}
                    placeholder={t("form.subjectPlaceholder")}
                    className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-blue-500/50"
                />

                <div className="space-y-1.5">
                    <div className="flex items-center justify-between">
                        <span className="text-xs text-muted-foreground">{t("form.varsHint")}</span>
                        <button
                            onClick={() => setPreview((p) => !p)}
                            className="flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground transition-colors"
                        >
                            {preview ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                            {preview ? t("form.editor") : t("form.preview")}
                        </button>
                    </div>
                    {preview ? (
                        <div
                            className="min-h-[180px] bg-white rounded-lg border border-border p-4 overflow-auto"
                            dangerouslySetInnerHTML={{ __html: form.html_body.replace("{{nombre}}", t("form.sampleName")).replace("{{email}}", "cliente@ejemplo.com") }}
                        />
                    ) : (
                        <textarea
                            value={form.html_body}
                            onChange={(e) => setForm((f) => ({ ...f, html_body: e.target.value }))}
                            rows={7}
                            placeholder={t("form.bodyPlaceholder")}
                            className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-blue-500/50 resize-none font-mono"
                        />
                    )}
                </div>

                <div className="flex items-center gap-3">
                    <div className="flex items-center gap-2 flex-1">
                        <Calendar className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                        <input
                            type="datetime-local"
                            value={form.scheduled_at}
                            onChange={(e) => setForm((f) => ({ ...f, scheduled_at: e.target.value }))}
                            className="bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-blue-500/50"
                        />
                        <span className="text-xs text-muted-foreground">{t("form.emptyForDraft")}</span>
                    </div>
                    <button
                        onClick={create}
                        disabled={creating || !form.name || !form.subject || !form.html_body}
                        className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-sm font-medium transition-colors"
                    >
                        {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                        {t("form.create")}
                    </button>
                </div>
            </div>

            {/* Lista campañas */}
            {loading && <div className="flex justify-center py-10"><Loader2 className="w-5 h-5 animate-spin text-muted-foreground" /></div>}

            {!loading && campaigns.length === 0 && (
                <div className="flex flex-col items-center py-14 text-center">
                    <Mail className="w-8 h-8 text-muted-foreground/30 mb-3" />
                    <p className="text-sm text-muted-foreground">{t("empty.noCampaigns")}</p>
                </div>
            )}

            <div className="space-y-3">
                {campaigns.map((c) => {
                    const cfg = STATUS_CFG[c.status as keyof typeof STATUS_CFG] ?? STATUS_CFG.draft;
                    const StatusIcon = cfg.icon;
                    const canSend = c.status === "draft" || c.status === "scheduled";
                    return (
                        <div key={c.id} className="bg-card border border-border rounded-xl p-4 space-y-3">
                            <div className="flex items-start justify-between gap-3">
                                <div className="min-w-0">
                                    <p className="text-sm font-medium text-foreground truncate">{c.name}</p>
                                    <p className="text-xs text-muted-foreground truncate mt-0.5">{c.subject}</p>
                                </div>
                                <div className="flex items-center gap-2 flex-shrink-0">
                                    <span className={`flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full border font-medium ${cfg.color}`}>
                                        <StatusIcon className={`w-3 h-3 ${c.status === "sending" ? "animate-spin" : ""}`} />
                                        {cfg.label}
                                    </span>
                                    {canSend && (
                                        <button
                                            onClick={() => send(c.id)}
                                            disabled={sending === c.id}
                                            className="flex items-center gap-1 text-[11px] px-3 py-1 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white transition-colors"
                                        >
                                            {sending === c.id ? <Loader2 className="w-3 h-3 animate-spin" /> : <Send className="w-3 h-3" />}
                                            {t("list.send")}
                                        </button>
                                    )}
                                    {c.status !== "sent" && (
                                        <button onClick={() => remove(c.id)} className="text-muted-foreground hover:text-red-400 transition-colors">
                                            <Trash2 className="w-3.5 h-3.5" />
                                        </button>
                                    )}
                                </div>
                            </div>
                            <div className="flex items-center gap-4 text-[11px] text-muted-foreground">
                                <span className="flex items-center gap-1"><Users className="w-3 h-3" />{t("list.recipientsShort", { count: c.total_count })}</span>
                                {c.sent_count > 0 && <span className="text-emerald-400">{t("list.sentCount", { count: c.sent_count })}</span>}
                                {c.failed_count > 0 && <span className="text-red-400">{t("list.failedCount", { count: c.failed_count })}</span>}
                                {c.scheduled_at && <span className="flex items-center gap-1"><Clock className="w-3 h-3" />{fmt(c.scheduled_at)}</span>}
                                {c.sent_at && <span>{t("list.sentAt", { date: fmt(c.sent_at) })}</span>}
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
