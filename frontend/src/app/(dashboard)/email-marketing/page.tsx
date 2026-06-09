"use client";

import { useState, useEffect, useCallback } from "react";
import {
    Mail, FileText, BarChart3, Loader2, Plus, Send, Trash2,
    CheckCircle2, Clock, AlertCircle, Eye, EyeOff, Users,
    Calendar, ChevronRight, X,
} from "lucide-react";
import {
    emailMarketingApi,
    type EmailCampaign,
    type EmailTemplate,
} from "@/lib/api/email_marketing";

// ── Tabs ───────────────────────────────────────────────────────────────────────

const TABS = [
    { key: "campaigns", label: "Campañas",   icon: Send },
    { key: "templates", label: "Plantillas", icon: FileText },
    { key: "stats",     label: "Estadísticas", icon: BarChart3 },
] as const;
type TabKey = typeof TABS[number]["key"];

// ── Status config ──────────────────────────────────────────────────────────────

const STATUS_CFG = {
    draft:     { label: "Borrador",   color: "text-muted-foreground bg-muted/50 border-border", icon: FileText },
    scheduled: { label: "Programada", color: "text-blue-400 bg-blue-500/10 border-blue-500/20", icon: Clock },
    sending:   { label: "Enviando",   color: "text-amber-400 bg-amber-500/10 border-amber-500/20", icon: Loader2 },
    sent:      { label: "Enviada",    color: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20", icon: CheckCircle2 },
    failed:    { label: "Error",      color: "text-red-400 bg-red-500/10 border-red-500/20", icon: AlertCircle },
} as const;

const fmt = (iso: string | null) =>
    iso ? new Date(iso).toLocaleString("es-ES", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }) : "—";

// ── TEMPLATE_VARS hint ─────────────────────────────────────────────────────────

const VARS_HINT = "Variables disponibles: {{nombre}}, {{email}}";

// ── Page ───────────────────────────────────────────────────────────────────────

export default function EmailMarketingPage() {
    const [tab, setTab] = useState<TabKey>("campaigns");

    return (
        <div className="p-6 max-w-5xl mx-auto space-y-5">
            <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-blue-500/10 border border-blue-500/20">
                    <Mail className="w-5 h-5 text-blue-400" />
                </div>
                <div>
                    <h1 className="text-lg font-semibold text-foreground">Email Marketing</h1>
                    <p className="text-xs text-muted-foreground">Campañas masivas a tus clientes usando tu cuenta de email configurada</p>
                </div>
            </div>

            <div className="flex gap-1 border-b border-border">
                {TABS.map(({ key, label, icon: Icon }) => (
                    <button
                        key={key}
                        onClick={() => setTab(key)}
                        className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px ${
                            tab === key
                                ? "border-blue-500 text-blue-400"
                                : "border-transparent text-muted-foreground hover:text-foreground"
                        }`}
                    >
                        <Icon className="w-3.5 h-3.5" />
                        {label}
                    </button>
                ))}
            </div>

            {tab === "campaigns" && <TabCampaigns />}
            {tab === "templates" && <TabTemplates />}
            {tab === "stats"     && <TabStats />}
        </div>
    );
}

// ── Tab: Campañas ──────────────────────────────────────────────────────────────

function TabCampaigns() {
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
        } catch {} finally { setLoading(false); }
    }, []);

    useEffect(() => { load(); }, [load]);

    const applyTemplate = (id: string) => {
        const tpl = templates.find((t) => t.id === id);
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
        } catch {} finally { setCreating(false); }
    };

    const send = async (id: string) => {
        setSending(id);
        try {
            await emailMarketingApi.campaigns.send(id);
            await load();
        } catch {} finally { setSending(null); }
    };

    const remove = async (id: string) => {
        try {
            await emailMarketingApi.campaigns.delete(id);
            setCampaigns((prev) => prev.filter((c) => c.id !== id));
        } catch {}
    };

    return (
        <div className="space-y-6">
            {/* Formulario nueva campaña */}
            <div className="bg-card border border-border rounded-xl p-5 space-y-4">
                <div className="flex items-center justify-between">
                    <h2 className="text-sm font-semibold text-foreground">Nueva campaña</h2>
                    <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                        <Users className="w-3.5 h-3.5" />
                        <span>{recipientCount} destinatarios (clientes con email)</span>
                    </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <input
                        value={form.name}
                        onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                        placeholder="Nombre interno de la campaña"
                        className="bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-blue-500/50"
                    />
                    <select
                        value={form.template_id}
                        onChange={(e) => applyTemplate(e.target.value)}
                        className="bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-blue-500/50"
                    >
                        <option value="">Plantilla (opcional)</option>
                        {templates.map((t) => (
                            <option key={t.id} value={t.id}>{t.name}</option>
                        ))}
                    </select>
                </div>

                <input
                    value={form.subject}
                    onChange={(e) => setForm((f) => ({ ...f, subject: e.target.value }))}
                    placeholder="Asunto del email"
                    className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-blue-500/50"
                />

                <div className="space-y-1.5">
                    <div className="flex items-center justify-between">
                        <span className="text-xs text-muted-foreground">{VARS_HINT}</span>
                        <button
                            onClick={() => setPreview((p) => !p)}
                            className="flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground transition-colors"
                        >
                            {preview ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                            {preview ? "Editor" : "Preview"}
                        </button>
                    </div>
                    {preview ? (
                        <div
                            className="min-h-[180px] bg-white rounded-lg border border-border p-4 overflow-auto"
                            dangerouslySetInnerHTML={{ __html: form.html_body.replace("{{nombre}}", "Cliente").replace("{{email}}", "cliente@ejemplo.com") }}
                        />
                    ) : (
                        <textarea
                            value={form.html_body}
                            onChange={(e) => setForm((f) => ({ ...f, html_body: e.target.value }))}
                            rows={7}
                            placeholder="Cuerpo del email (HTML o texto plano)"
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
                        <span className="text-xs text-muted-foreground">Dejar vacío para borrador</span>
                    </div>
                    <button
                        onClick={create}
                        disabled={creating || !form.name || !form.subject || !form.html_body}
                        className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-sm font-medium transition-colors"
                    >
                        {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                        Crear
                    </button>
                </div>
            </div>

            {/* Lista campañas */}
            {loading && <div className="flex justify-center py-10"><Loader2 className="w-5 h-5 animate-spin text-muted-foreground" /></div>}

            {!loading && campaigns.length === 0 && (
                <div className="flex flex-col items-center py-14 text-center">
                    <Mail className="w-8 h-8 text-muted-foreground/30 mb-3" />
                    <p className="text-sm text-muted-foreground">Sin campañas todavía</p>
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
                                            Enviar
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
                                <span className="flex items-center gap-1"><Users className="w-3 h-3" />{c.total_count} dest.</span>
                                {c.sent_count > 0 && <span className="text-emerald-400">{c.sent_count} enviados</span>}
                                {c.failed_count > 0 && <span className="text-red-400">{c.failed_count} fallidos</span>}
                                {c.scheduled_at && <span className="flex items-center gap-1"><Clock className="w-3 h-3" />{fmt(c.scheduled_at)}</span>}
                                {c.sent_at && <span>Enviada {fmt(c.sent_at)}</span>}
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

// ── Tab: Plantillas ────────────────────────────────────────────────────────────

function TabTemplates() {
    const [templates, setTemplates] = useState<EmailTemplate[]>([]);
    const [loading, setLoading] = useState(true);
    const [editing, setEditing] = useState<EmailTemplate | null>(null);
    const [form, setForm] = useState({ name: "", subject: "", html_body: "" });
    const [saving, setSaving] = useState(false);
    const [preview, setPreview] = useState(false);

    const load = useCallback(async () => {
        try { setTemplates(await emailMarketingApi.templates.list()); }
        catch {} finally { setLoading(false); }
    }, []);

    useEffect(() => { load(); }, [load]);

    const openNew = () => {
        setEditing(null);
        setForm({ name: "", subject: "", html_body: "" });
        setPreview(false);
    };

    const openEdit = (t: EmailTemplate) => {
        setEditing(t);
        setForm({ name: t.name, subject: t.subject, html_body: t.html_body });
        setPreview(false);
    };

    const save = async () => {
        if (!form.name || !form.subject || !form.html_body) return;
        setSaving(true);
        try {
            if (editing) {
                const updated = await emailMarketingApi.templates.update(editing.id, form);
                setTemplates((prev) => prev.map((t) => t.id === editing.id ? updated : t));
            } else {
                const created = await emailMarketingApi.templates.create(form);
                setTemplates((prev) => [created, ...prev]);
            }
            setEditing(null);
            setForm({ name: "", subject: "", html_body: "" });
        } catch {} finally { setSaving(false); }
    };

    const remove = async (id: string) => {
        try {
            await emailMarketingApi.templates.delete(id);
            setTemplates((prev) => prev.filter((t) => t.id !== id));
        } catch {}
    };

    const isFormOpen = editing !== null || (form.name !== "" || form.html_body !== "");

    return (
        <div className="space-y-4 max-w-3xl">
            <div className="flex justify-end">
                <button
                    onClick={openNew}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium transition-colors"
                >
                    <Plus className="w-4 h-4" /> Nueva plantilla
                </button>
            </div>

            {/* Editor */}
            <div className="bg-card border border-border rounded-xl p-5 space-y-4">
                <div className="flex items-center justify-between">
                    <h2 className="text-sm font-semibold text-foreground">
                        {editing ? `Editando: ${editing.name}` : "Nueva plantilla"}
                    </h2>
                    <button
                        onClick={() => setPreview((p) => !p)}
                        className="flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground transition-colors"
                    >
                        {preview ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                        {preview ? "Editor" : "Preview"}
                    </button>
                </div>

                <input
                    value={form.name}
                    onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                    placeholder="Nombre de la plantilla"
                    className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-blue-500/50"
                />
                <input
                    value={form.subject}
                    onChange={(e) => setForm((f) => ({ ...f, subject: e.target.value }))}
                    placeholder="Asunto del email"
                    className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-blue-500/50"
                />

                <div className="space-y-1">
                    <p className="text-[11px] text-muted-foreground">{VARS_HINT}</p>
                    {preview ? (
                        <div
                            className="min-h-[180px] bg-white rounded-lg border border-border p-4 overflow-auto"
                            dangerouslySetInnerHTML={{ __html: form.html_body.replace("{{nombre}}", "Cliente").replace("{{email}}", "cliente@ejemplo.com") }}
                        />
                    ) : (
                        <textarea
                            value={form.html_body}
                            onChange={(e) => setForm((f) => ({ ...f, html_body: e.target.value }))}
                            rows={8}
                            placeholder="Cuerpo HTML de la plantilla…"
                            className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-blue-500/50 resize-none font-mono"
                        />
                    )}
                </div>

                <div className="flex justify-end gap-2">
                    {editing && (
                        <button onClick={() => { setEditing(null); setForm({ name: "", subject: "", html_body: "" }); }}
                            className="px-4 py-2 rounded-lg border border-border text-sm text-muted-foreground hover:text-foreground transition-colors">
                            Cancelar
                        </button>
                    )}
                    <button
                        onClick={save}
                        disabled={saving || !form.name || !form.subject || !form.html_body}
                        className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-sm font-medium transition-colors"
                    >
                        {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                        {editing ? "Guardar cambios" : "Crear plantilla"}
                    </button>
                </div>
            </div>

            {/* Lista */}
            {loading && <div className="flex justify-center py-8"><Loader2 className="w-5 h-5 animate-spin text-muted-foreground" /></div>}

            <div className="space-y-2">
                {templates.map((t) => (
                    <div key={t.id} className="bg-card border border-border rounded-xl px-4 py-3 flex items-center justify-between gap-3">
                        <div className="min-w-0">
                            <p className="text-sm font-medium text-foreground truncate">{t.name}</p>
                            <p className="text-xs text-muted-foreground truncate mt-0.5">{t.subject}</p>
                        </div>
                        <div className="flex items-center gap-2 flex-shrink-0">
                            <button onClick={() => openEdit(t)} className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1 transition-colors">
                                <ChevronRight className="w-3.5 h-3.5" /> Editar
                            </button>
                            <button onClick={() => remove(t.id)} className="text-muted-foreground hover:text-red-400 transition-colors">
                                <Trash2 className="w-3.5 h-3.5" />
                            </button>
                        </div>
                    </div>
                ))}
                {!loading && templates.length === 0 && (
                    <p className="text-center text-sm text-muted-foreground py-8">Sin plantillas guardadas</p>
                )}
            </div>
        </div>
    );
}

// ── Tab: Estadísticas ──────────────────────────────────────────────────────────

function TabStats() {
    const [campaigns, setCampaigns] = useState<EmailCampaign[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        emailMarketingApi.campaigns.list()
            .then((data) => setCampaigns(data.filter((c) => c.status === "sent" || c.sent_count > 0)))
            .catch(() => {})
            .finally(() => setLoading(false));
    }, []);

    const totalSent = campaigns.reduce((acc, c) => acc + c.sent_count, 0);
    const totalFailed = campaigns.reduce((acc, c) => acc + c.failed_count, 0);
    const totalRecipients = campaigns.reduce((acc, c) => acc + c.total_count, 0);

    if (loading) return <div className="flex justify-center py-10"><Loader2 className="w-5 h-5 animate-spin text-muted-foreground" /></div>;

    if (campaigns.length === 0) return (
        <div className="flex flex-col items-center py-16 text-center">
            <BarChart3 className="w-8 h-8 text-muted-foreground/30 mb-3" />
            <p className="text-sm text-muted-foreground">Todavía no hay campañas enviadas</p>
        </div>
    );

    return (
        <div className="space-y-6">
            {/* Resumen global */}
            <div className="grid grid-cols-3 gap-4">
                {[
                    { label: "Emails enviados", value: totalSent, color: "text-emerald-400" },
                    { label: "Fallidos", value: totalFailed, color: "text-red-400" },
                    { label: "Tasa de éxito", value: totalRecipients ? `${Math.round((totalSent / totalRecipients) * 100)}%` : "—", color: "text-blue-400" },
                ].map((s) => (
                    <div key={s.label} className="bg-card border border-border rounded-xl p-4 text-center">
                        <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
                        <p className="text-xs text-muted-foreground mt-1">{s.label}</p>
                    </div>
                ))}
            </div>

            {/* Por campaña */}
            <div className="space-y-3">
                {campaigns.map((c) => {
                    const pct = c.total_count ? Math.round((c.sent_count / c.total_count) * 100) : 0;
                    return (
                        <div key={c.id} className="bg-card border border-border rounded-xl p-4 space-y-3">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm font-medium text-foreground">{c.name}</p>
                                    <p className="text-xs text-muted-foreground">{fmt(c.sent_at)}</p>
                                </div>
                                <span className="text-sm font-semibold text-blue-400">{pct}%</span>
                            </div>
                            <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                                <div className="h-full bg-blue-500 rounded-full" style={{ width: `${pct}%` }} />
                            </div>
                            <div className="flex gap-4 text-[11px] text-muted-foreground">
                                <span>{c.total_count} destinatarios</span>
                                <span className="text-emerald-400">{c.sent_count} enviados</span>
                                {c.failed_count > 0 && <span className="text-red-400">{c.failed_count} fallidos</span>}
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
