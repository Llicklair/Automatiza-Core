"use client";

import { useState, useEffect, useRef } from "react";
import { Mail, Send, Bot, AlertCircle, CheckCircle2, Loader2, Paperclip, X, FileText, Inbox, RefreshCw, HardDrive, Folder, Sparkles, Flame, FileSpreadsheet, MessageSquare, Truck, Users, Megaphone, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import type { EmailStatus, InboxMessage, EmailDetail, DriveFile, EmailClassification, EmailCategory } from "@/lib/api/messaging";

const CATEGORY_META: Record<EmailCategory, { label: string; icon: typeof Mail; tone: string }> = {
    urgente:   { label: "Urgente",    icon: Flame,           tone: "bg-rose-500/15 text-rose-500 border-rose-500/30" },
    factura:   { label: "Factura",    icon: FileSpreadsheet, tone: "bg-emerald-500/15 text-emerald-500 border-emerald-500/30" },
    consulta:  { label: "Consulta",   icon: MessageSquare,   tone: "bg-primary/15 text-primary border-primary/30" },
    proveedor: { label: "Proveedor",  icon: Truck,           tone: "bg-amber-500/15 text-amber-500 border-amber-500/30" },
    rrhh:      { label: "RRHH",       icon: Users,           tone: "bg-violet-500/15 text-violet-500 border-violet-500/30" },
    marketing: { label: "Marketing",  icon: Megaphone,       tone: "bg-muted text-muted-foreground border-border" },
    spam:      { label: "Spam",       icon: Trash2,          tone: "bg-muted/40 text-muted-foreground/70 border-border line-through" },
    otro:      { label: "Otro",       icon: Mail,            tone: "bg-muted text-muted-foreground border-border" },
};
import type { Document } from "@/lib/api/documents";

function formatBytes(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(dateStr: string): string {
    if (!dateStr) return "";
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    const now = new Date();
    const sameDay = d.toDateString() === now.toDateString();
    if (sameDay) {
        return d.toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" });
    }
    return d.toLocaleDateString("es-ES", { day: "2-digit", month: "short" });
}

const TABS = [
    { key: "bandeja", label: "Bandeja", icon: Inbox },
    { key: "componer", label: "Componer", icon: Send },
    { key: "ia", label: "Instrucción IA", icon: Bot },
] as const;
type TabKey = (typeof TABS)[number]["key"];

export default function CorreosPage() {
    const [activeTab, setActiveTab] = useState<TabKey>("bandeja");
    const [status, setStatus] = useState<EmailStatus | null>(null);

    // Compose form
    const [to, setTo] = useState("");
    const [subject, setSubject] = useState("");
    const [body, setBody] = useState("");
    const [attachments, setAttachments] = useState<Document[]>([]);
    const [uploading, setUploading] = useState(false);
    const fileRef = useRef<HTMLInputElement>(null);

    // AI instruct form
    const [instruction, setInstruction] = useState("");

    // Inbox
    const [inboxMessages, setInboxMessages] = useState<InboxMessage[] | null>(null);
    const [inboxLoading, setInboxLoading] = useState(false);
    const [inboxProvider, setInboxProvider] = useState<"gmail" | "outlook" | null>(null);
    const [selectedMsg, setSelectedMsg] = useState<EmailDetail | null>(null);
    const [classMap, setClassMap] = useState<Record<string, EmailClassification>>({});
    const [classLoading, setClassLoading] = useState(false);
    const [draftLoading, setDraftLoading] = useState(false);
    const [draftError, setDraftError] = useState<string | null>(null);
    const [bodyLoading, setBodyLoading] = useState(false);

    // Drive picker
    const [showDrive, setShowDrive] = useState(false);
    const [driveFiles, setDriveFiles] = useState<DriveFile[] | null>(null);
    const [driveLoading, setDriveLoading] = useState(false);
    const [driveQuery, setDriveQuery] = useState("");
    const [importingId, setImportingId] = useState<string | null>(null);

    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<{ ok: boolean; message: string } | null>(null);

    useEffect(() => {
        api.messaging.email.status().then(setStatus).catch(() => null);
    }, []);

    async function classifyInbox(msgs: InboxMessage[]) {
        if (msgs.length === 0) return;
        setClassLoading(true);
        try {
            const res = await api.messaging.email.classify(
                msgs.map((m) => ({ id: m.id, from: m.from, subject: m.subject, snippet: m.snippet })),
            );
            const map: Record<string, EmailClassification> = {};
            for (const item of res.items) map[item.id] = item;
            setClassMap(map);
        } catch {
            // Silencioso: la bandeja sigue funcional sin clasificación.
        } finally {
            setClassLoading(false);
        }
    }

    async function handleDraftReply() {
        if (!selectedMsg) return;
        setDraftLoading(true);
        setDraftError(null);
        try {
            const draft = await api.messaging.email.draftReply(selectedMsg.id);
            // Pre-rellenar composer y cambiar de pestaña
            setTo(selectedMsg.from);
            setSubject(draft.subject || `Re: ${selectedMsg.subject}`);
            setBody(draft.body);
            setSelectedMsg(null);
            setActiveTab("componer");
        } catch (e) {
            setDraftError(e instanceof Error ? e.message : "No se pudo redactar el borrador");
        } finally {
            setDraftLoading(false);
        }
    }

    async function loadInbox() {
        setInboxLoading(true);
        try {
            const res = await api.messaging.email.inbox(20);
            setInboxMessages(res.messages);
            setInboxProvider(res.provider);
            // Lanzar clasificación IA en segundo plano (no bloquea la UI)
            classifyInbox(res.messages);
        } catch (err) {
            setResult({ ok: false, message: err instanceof Error ? err.message : "Error al cargar la bandeja" });
            setInboxMessages([]);
        } finally {
            setInboxLoading(false);
        }
    }

    useEffect(() => {
        if (activeTab === "bandeja" && inboxMessages === null) {
            loadInbox();
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [activeTab]);

    async function openMessage(id: string) {
        setBodyLoading(true);
        setSelectedMsg(null);
        try {
            const detail = await api.messaging.email.getMessage(id);
            setSelectedMsg(detail);
        } catch (err) {
            setResult({ ok: false, message: err instanceof Error ? err.message : "Error al cargar el mensaje" });
        } finally {
            setBodyLoading(false);
        }
    }

    async function handleSend(e: React.FormEvent) {
        e.preventDefault();
        setLoading(true);
        setResult(null);
        try {
            const ids = attachments.map((a) => a.id);
            const res = await api.messaging.email.send(to, subject, body, ids.length ? ids : undefined);
            setResult({ ok: true, message: res.result });
            setTo(""); setSubject(""); setBody(""); setAttachments([]);
        } catch (err: unknown) {
            setResult({ ok: false, message: err instanceof Error ? err.message : "Error al enviar" });
        } finally {
            setLoading(false);
        }
    }

    async function handleAttach(e: React.ChangeEvent<HTMLInputElement>) {
        const files = Array.from(e.target.files ?? []);
        if (files.length === 0) return;
        setUploading(true);
        try {
            const uploaded = await Promise.all(
                files.map((f) => api.documents.upload(f, "email-attachment"))
            );
            setAttachments((prev) => [...prev, ...uploaded]);
        } catch (err: unknown) {
            setResult({ ok: false, message: err instanceof Error ? err.message : "Error al subir el archivo" });
        } finally {
            setUploading(false);
            if (fileRef.current) fileRef.current.value = "";
        }
    }

    function removeAttachment(id: string) {
        setAttachments((prev) => prev.filter((a) => a.id !== id));
    }

    async function openDrivePicker() {
        setShowDrive(true);
        if (driveFiles === null) {
            await loadDrive("");
        }
    }

    async function loadDrive(q: string) {
        setDriveLoading(true);
        try {
            const res = await api.messaging.drive.list("root", q);
            setDriveFiles(res.files);
        } catch (err) {
            setResult({ ok: false, message: err instanceof Error ? err.message : "Error al listar Drive" });
            setDriveFiles([]);
        } finally {
            setDriveLoading(false);
        }
    }

    async function attachFromDrive(file: DriveFile) {
        if (file.is_folder) return;
        setImportingId(file.id);
        try {
            const doc = await api.messaging.drive.attachAsDocument(file.id);
            setAttachments((prev) => [...prev, doc]);
            setShowDrive(false);
        } catch (err) {
            setResult({ ok: false, message: err instanceof Error ? err.message : "Error al importar de Drive" });
        } finally {
            setImportingId(null);
        }
    }

    async function handleInstruct(e: React.FormEvent) {
        e.preventDefault();
        setLoading(true);
        setResult(null);
        try {
            const res = await api.messaging.email.instruct(instruction);
            setResult({ ok: res.success, message: res.action });
            if (res.success) setInstruction("");
        } catch (err: unknown) {
            setResult({ ok: false, message: err instanceof Error ? err.message : "Error al procesar instrucción" });
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="max-w-3xl mx-auto px-4 py-8 space-y-6">
            {/* Header */}
            <div className="flex items-start justify-between">
                <div>
                    <h1 className="text-xl font-semibold text-foreground flex items-center gap-2">
                        <Mail className="w-6 h-6 text-violet-400" /> Correos
                    </h1>
                    <p className="text-xs text-muted-foreground mt-1">Envía correos o instruye al agente de email</p>
                </div>
                {status && (
                    <div className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full border ${
                        status.configured
                            ? "bg-green-500/10 text-green-400 border-green-500/30"
                            : "bg-amber-500/10 text-amber-400 border-amber-500/30"
                    }`}>
                        {status.configured
                            ? <><CheckCircle2 className="w-3.5 h-3.5" /> Conectado</>
                            : <><AlertCircle className="w-3.5 h-3.5" /> Sin credenciales</>
                        }
                    </div>
                )}
            </div>

            {/* Config warning */}
            {status && !status.configured && (
                <div className="flex gap-2 text-sm text-amber-400 bg-amber-500/10 border border-amber-500/20 rounded-lg px-4 py-3">
                    <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
                    <span>No hay credenciales de email configuradas. Configura Gmail, Outlook o SMTP en <strong>Configuración &rsaquo; Integraciones</strong>. Los envíos funcionarán en modo demo.</span>
                </div>
            )}

            {/* Tabs */}
            <div className="flex gap-1 border-b border-border">
                {TABS.map(tab => {
                    const Icon = tab.icon;
                    const isActive = activeTab === tab.key;
                    return (
                        <button
                            key={tab.key}
                            onClick={() => { setActiveTab(tab.key); setResult(null); }}
                            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px ${
                                isActive
                                    ? "border-violet-500 text-foreground"
                                    : "border-transparent text-muted-foreground hover:text-foreground hover:border-border"
                            }`}
                        >
                            <Icon className="w-4 h-4" />
                            {tab.label}
                        </button>
                    );
                })}
            </div>

            {/* Result banner */}
            {result && (
                <div className={`flex gap-2 text-sm rounded-lg px-4 py-3 border ${
                    result.ok
                        ? "bg-green-500/10 text-green-400 border-green-500/20"
                        : "bg-red-500/10 text-red-400 border-red-500/20"
                }`}>
                    {result.ok ? <CheckCircle2 className="w-4 h-4 mt-0.5 shrink-0" /> : <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />}
                    <span>{result.message}</span>
                </div>
            )}

            {/* Inbox tab */}
            {activeTab === "bandeja" && (
                <div className="space-y-3">
                    <div className="flex items-center justify-between">
                        <p className="text-xs text-muted-foreground">
                            {inboxProvider === "gmail" && "Bandeja de Gmail"}
                            {inboxProvider === "outlook" && "Bandeja de Outlook"}
                            {inboxProvider === null && !inboxLoading && "Sin proveedor configurado"}
                            {inboxLoading && "Cargando bandeja…"}
                        </p>
                        <button
                            type="button"
                            onClick={loadInbox}
                            disabled={inboxLoading}
                            className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground disabled:opacity-50"
                        >
                            {inboxLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
                            Refrescar
                        </button>
                    </div>

                    {!inboxLoading && inboxProvider === null && (
                        <div className="flex flex-col items-center justify-center h-40 gap-2 text-muted-foreground border border-dashed border-border rounded-lg">
                            <Inbox className="w-8 h-8 opacity-30" />
                            <p className="text-sm">No hay proveedor de correo configurado</p>
                            <p className="text-xs max-w-xs text-center">
                                Conecta Gmail u Outlook en <strong>Configuración &rsaquo; Mensajería</strong>
                                para ver tu bandeja aquí.
                            </p>
                        </div>
                    )}

                    {!inboxLoading && inboxMessages?.length === 0 && inboxProvider !== null && (
                        <div className="flex flex-col items-center justify-center h-40 gap-2 text-muted-foreground border border-dashed border-border rounded-lg">
                            <Inbox className="w-8 h-8 opacity-30" />
                            <p className="text-sm">Bandeja vacía</p>
                        </div>
                    )}

                    {inboxMessages && inboxMessages.length > 0 && (
                        <ul className="rounded-lg border border-border overflow-hidden divide-y divide-border">
                            {inboxMessages.map((m) => {
                                const cls = classMap[m.id];
                                const meta = cls ? CATEGORY_META[cls.category] : null;
                                const CatIcon = meta?.icon;
                                return (
                                    <li key={m.id}>
                                        <button
                                            type="button"
                                            onClick={() => openMessage(m.id)}
                                            className="w-full text-left px-4 py-3 hover:bg-muted/30 transition-colors flex items-start gap-3"
                                        >
                                            {m.unread && <span className="mt-1.5 w-2 h-2 rounded-full bg-violet-500 shrink-0" aria-label="No leído" />}
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center gap-2">
                                                    <span className={`text-sm truncate ${m.unread ? "font-semibold text-foreground" : "text-foreground"}`}>
                                                        {m.from || "(sin remitente)"}
                                                    </span>
                                                    {meta && CatIcon && (
                                                        <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-medium rounded border uppercase tracking-wider ${meta.tone}`}>
                                                            <CatIcon className="w-3 h-3" />
                                                            {meta.label}
                                                            {cls.urgency >= 4 && <span className="ml-0.5">·{cls.urgency}/5</span>}
                                                        </span>
                                                    )}
                                                    <span className="text-[11px] text-muted-foreground ml-auto shrink-0 tabular-nums">
                                                        {formatDate(m.date)}
                                                    </span>
                                                </div>
                                                <p className={`text-sm truncate ${m.unread ? "text-foreground" : "text-muted-foreground"}`}>
                                                    {m.subject || "(sin asunto)"}
                                                </p>
                                                <p className="text-xs text-muted-foreground truncate mt-0.5">
                                                    {cls?.suggested_action ? `🤖 ${cls.suggested_action}` : m.snippet}
                                                </p>
                                            </div>
                                        </button>
                                    </li>
                                );
                            })}
                        </ul>
                    )}

                    {/* Detail modal */}
                    {(selectedMsg || bodyLoading) && (
                        <div
                            className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4"
                            onClick={() => { setSelectedMsg(null); setBodyLoading(false); }}
                        >
                            <div
                                className="bg-background border border-border rounded-xl max-w-2xl w-full max-h-[85vh] overflow-hidden flex flex-col"
                                onClick={(e) => e.stopPropagation()}
                            >
                                <div className="flex items-start justify-between gap-4 p-5 border-b border-border">
                                    {bodyLoading || !selectedMsg ? (
                                        <div className="flex items-center gap-2 text-muted-foreground text-sm">
                                            <Loader2 className="w-4 h-4 animate-spin" /> Cargando…
                                        </div>
                                    ) : (
                                        <div className="min-w-0 flex-1">
                                            <h3 className="text-base font-semibold text-foreground truncate">{selectedMsg.subject || "(sin asunto)"}</h3>
                                            <p className="text-xs text-muted-foreground mt-1">
                                                <strong className="text-foreground/80">De:</strong> {selectedMsg.from}
                                            </p>
                                            <p className="text-xs text-muted-foreground">
                                                <strong className="text-foreground/80">Para:</strong> {selectedMsg.to || "—"}
                                            </p>
                                            <p className="text-[11px] text-muted-foreground mt-1">{formatDate(selectedMsg.date)}</p>
                                        </div>
                                    )}
                                    <button
                                        onClick={() => { setSelectedMsg(null); setBodyLoading(false); }}
                                        className="text-muted-foreground hover:text-foreground"
                                        aria-label="Cerrar"
                                    >
                                        <X className="w-4 h-4" />
                                    </button>
                                </div>
                                <div className="p-5 overflow-auto flex-1">
                                    {selectedMsg && (
                                        selectedMsg.provider === "outlook" && /<[a-z][^>]*>/i.test(selectedMsg.body)
                                            ? <div className="prose prose-sm dark:prose-invert max-w-none" dangerouslySetInnerHTML={{ __html: selectedMsg.body }} />
                                            : <pre className="whitespace-pre-wrap text-sm text-foreground font-sans">{selectedMsg.body}</pre>
                                    )}
                                </div>
                                {selectedMsg && (
                                    <div className="p-4 border-t border-border bg-muted/20 flex items-center justify-between gap-3">
                                        <div className="text-xs text-muted-foreground">
                                            {draftError ? <span className="text-rose-400">{draftError}</span> : "Genera un borrador y revísalo antes de enviar."}
                                        </div>
                                        <button
                                            onClick={handleDraftReply}
                                            disabled={draftLoading}
                                            className="inline-flex items-center gap-2 h-9 px-3 rounded-md bg-primary text-primary-foreground text-sm font-medium hover:brightness-110 transition disabled:opacity-50"
                                        >
                                            {draftLoading
                                                ? <><Loader2 className="w-4 h-4 animate-spin" /> Redactando…</>
                                                : <><Sparkles className="w-4 h-4" /> Borrador IA</>}
                                        </button>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* Compose tab */}
            {activeTab === "componer" && (
                <form onSubmit={handleSend} className="space-y-4">
                    <div className="space-y-1">
                        <label className="text-xs font-medium text-muted-foreground">Para</label>
                        <input
                            type="email"
                            required
                            value={to}
                            onChange={e => setTo(e.target.value)}
                            placeholder="destinatario@ejemplo.com"
                            className="w-full bg-card border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-violet-500"
                        />
                    </div>
                    <div className="space-y-1">
                        <label className="text-xs font-medium text-muted-foreground">Asunto</label>
                        <input
                            type="text"
                            required
                            value={subject}
                            onChange={e => setSubject(e.target.value)}
                            placeholder="Asunto del correo"
                            className="w-full bg-card border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-violet-500"
                        />
                    </div>
                    <div className="space-y-1">
                        <label className="text-xs font-medium text-muted-foreground">Mensaje</label>
                        <textarea
                            required
                            rows={6}
                            value={body}
                            onChange={e => setBody(e.target.value)}
                            placeholder="Escribe el contenido del correo..."
                            className="w-full bg-card border border-border rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-violet-500"
                        />
                    </div>

                    {/* Attachments */}
                    <div className="space-y-2">
                        <div className="flex items-center justify-between">
                            <label className="text-xs font-medium text-muted-foreground">
                                Adjuntos {attachments.length > 0 && `(${attachments.length})`}
                            </label>
                            <div className="flex items-center gap-3">
                                <button
                                    type="button"
                                    onClick={() => fileRef.current?.click()}
                                    disabled={uploading}
                                    className="flex items-center gap-1.5 text-xs text-violet-400 hover:text-violet-300 disabled:opacity-50"
                                >
                                    {uploading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Paperclip className="w-3.5 h-3.5" />}
                                    Adjuntar archivo
                                </button>
                                {status?.providers.gmail && (
                                    <button
                                        type="button"
                                        onClick={openDrivePicker}
                                        className="flex items-center gap-1.5 text-xs text-violet-400 hover:text-violet-300"
                                    >
                                        <HardDrive className="w-3.5 h-3.5" />
                                        Desde Drive
                                    </button>
                                )}
                                <input
                                    ref={fileRef}
                                    type="file"
                                    multiple
                                    className="hidden"
                                    onChange={handleAttach}
                                />
                            </div>
                        </div>
                        {attachments.length > 0 && (
                            <ul className="space-y-1.5">
                                {attachments.map((a) => (
                                    <li
                                        key={a.id}
                                        className="flex items-center gap-2 px-3 py-2 bg-card border border-border rounded-lg text-xs"
                                    >
                                        <FileText className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
                                        <span className="flex-1 truncate text-foreground">{a.file_name}</span>
                                        <span className="text-muted-foreground tabular-nums">{formatBytes(a.file_size)}</span>
                                        <button
                                            type="button"
                                            onClick={() => removeAttachment(a.id)}
                                            className="text-muted-foreground hover:text-foreground"
                                            aria-label="Quitar adjunto"
                                        >
                                            <X className="w-3.5 h-3.5" />
                                        </button>
                                    </li>
                                ))}
                            </ul>
                        )}
                    </div>

                    <button
                        type="submit"
                        disabled={loading || uploading}
                        className="flex items-center gap-2 px-4 py-2 bg-violet-600 hover:bg-violet-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
                    >
                        {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                        Enviar correo
                    </button>
                </form>
            )}

            {/* AI instruct tab */}
            {activeTab === "ia" && (
                <form onSubmit={handleInstruct} className="space-y-4">
                    <p className="text-sm text-muted-foreground">
                        Dile al agente qué hacer con el correo en lenguaje natural. Ejemplos: &ldquo;Muéstrame los correos no leídos&rdquo;, &ldquo;Envía un resumen de facturas pendientes a contabilidad@empresa.com&rdquo;.
                    </p>
                    <textarea
                        required
                        rows={4}
                        value={instruction}
                        onChange={e => setInstruction(e.target.value)}
                        placeholder="Instrucción para el agente de email..."
                        className="w-full bg-card border border-border rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-violet-500"
                    />
                    <button
                        type="submit"
                        disabled={loading}
                        className="flex items-center gap-2 px-4 py-2 bg-violet-600 hover:bg-violet-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
                    >
                        {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Bot className="w-4 h-4" />}
                        Ejecutar instrucción
                    </button>
                </form>
            )}

            {/* Drive picker modal */}
            {showDrive && (
                <div
                    className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4"
                    onClick={() => setShowDrive(false)}
                >
                    <div
                        className="bg-background border border-border rounded-xl max-w-2xl w-full max-h-[85vh] overflow-hidden flex flex-col"
                        onClick={(e) => e.stopPropagation()}
                    >
                        <div className="flex items-center justify-between p-4 border-b border-border">
                            <h3 className="text-base font-semibold text-foreground flex items-center gap-2">
                                <HardDrive className="w-4 h-4 text-violet-400" />
                                Adjuntar desde Google Drive
                            </h3>
                            <button
                                onClick={() => setShowDrive(false)}
                                className="text-muted-foreground hover:text-foreground"
                                aria-label="Cerrar"
                            >
                                <X className="w-4 h-4" />
                            </button>
                        </div>
                        <div className="p-4 border-b border-border">
                            <input
                                type="text"
                                value={driveQuery}
                                onChange={(e) => setDriveQuery(e.target.value)}
                                onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); loadDrive(driveQuery); } }}
                                placeholder="Buscar archivo… (Enter para buscar)"
                                className="w-full bg-card border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-violet-500"
                            />
                        </div>
                        <div className="overflow-auto flex-1">
                            {driveLoading && (
                                <div className="flex items-center justify-center h-40 text-muted-foreground gap-2 text-sm">
                                    <Loader2 className="w-4 h-4 animate-spin" /> Cargando…
                                </div>
                            )}
                            {!driveLoading && driveFiles?.length === 0 && (
                                <div className="flex flex-col items-center justify-center h-40 gap-2 text-muted-foreground text-sm">
                                    <HardDrive className="w-7 h-7 opacity-30" />
                                    Sin archivos
                                </div>
                            )}
                            {!driveLoading && driveFiles && driveFiles.length > 0 && (
                                <ul className="divide-y divide-border">
                                    {driveFiles.map((f) => (
                                        <li key={f.id}>
                                            <button
                                                type="button"
                                                onClick={() => attachFromDrive(f)}
                                                disabled={f.is_folder || importingId === f.id}
                                                className="w-full text-left px-4 py-3 hover:bg-muted/30 transition-colors flex items-center gap-3 disabled:opacity-50"
                                            >
                                                {f.is_folder ? <Folder className="w-4 h-4 text-muted-foreground shrink-0" /> : <FileText className="w-4 h-4 text-muted-foreground shrink-0" />}
                                                <span className="flex-1 truncate text-sm text-foreground">{f.name}</span>
                                                {f.size != null && (
                                                    <span className="text-xs text-muted-foreground tabular-nums">{formatBytes(f.size)}</span>
                                                )}
                                                {importingId === f.id && <Loader2 className="w-3.5 h-3.5 animate-spin text-muted-foreground" />}
                                            </button>
                                        </li>
                                    ))}
                                </ul>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
