"use client";

import { useState, useEffect, useCallback } from "react";
import {
    Loader2, Plus, Trash2, Eye, EyeOff, ChevronRight,
} from "lucide-react";
import {
    emailMarketingApi,
    type EmailTemplate,
} from "@/lib/api/email_marketing";
import { useToastStore } from "@/stores/toast";
import { logError } from "@/lib/logger";
import { errMsg, VARS_HINT } from "./constants";

// ── Tab: Plantillas ────────────────────────────────────────────────────────────

export default function TabTemplates() {
    const toast = useToastStore();
    const [templates, setTemplates] = useState<EmailTemplate[]>([]);
    const [loading, setLoading] = useState(true);
    const [editing, setEditing] = useState<EmailTemplate | null>(null);
    const [form, setForm] = useState({ name: "", subject: "", html_body: "" });
    const [saving, setSaving] = useState(false);
    const [preview, setPreview] = useState(false);

    const load = useCallback(async () => {
        try { setTemplates(await emailMarketingApi.templates.list()); }
        catch (err) { logError("email-marketing/templates", err); } finally { setLoading(false); }
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
            toast.success("Plantilla guardada");
        } catch (err) { toast.error(errMsg(err, "Error al guardar la plantilla")); } finally { setSaving(false); }
    };

    const remove = async (id: string) => {
        try {
            await emailMarketingApi.templates.delete(id);
            setTemplates((prev) => prev.filter((t) => t.id !== id));
        } catch (err) { toast.error(errMsg(err, "Error al eliminar la plantilla")); }
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
