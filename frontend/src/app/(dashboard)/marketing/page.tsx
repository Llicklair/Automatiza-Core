"use client";

import { useState, useEffect, useCallback } from "react";
import {
    Megaphone, Link2, PenSquare, CalendarClock, Sparkles,
    Loader2, Send, ImageIcon, Clock,
    CheckCircle2, AlertCircle, Trash2, Plus,
} from "lucide-react";
import { marketingApi, SocialAccount, ScheduledPost } from "@/lib/api/marketing";
import { PLATFORM_ICONS } from "@/components/ui/social-icons";
import { useToastStore } from "@/stores/toast";
import { logError } from "@/lib/logger";

// ── Plataformas ────────────────────────────────────────────────────────────────

const PLATFORMS = [
    {
        id: "instagram",
        name: "Instagram",
        limit: 2200,
        colorClass: "text-pink-400 bg-pink-500/10 border-pink-500/20",
        iconBg: "bg-pink-500/15",
    },
    {
        id: "facebook",
        name: "Facebook",
        limit: 63206,
        colorClass: "text-blue-400 bg-blue-500/10 border-blue-500/20",
        iconBg: "bg-blue-500/15",
    },
    {
        id: "linkedin",
        name: "LinkedIn",
        limit: 3000,
        colorClass: "text-sky-400 bg-sky-500/10 border-sky-500/20",
        iconBg: "bg-sky-500/15",
    },
    {
        id: "twitter",
        name: "X (Twitter)",
        limit: 280,
        colorClass: "text-zinc-300 bg-zinc-500/10 border-zinc-500/20",
        iconBg: "bg-zinc-500/15",
    },
] as const;

const STATUS_CONFIG = {
    draft:     { label: "Borrador",    color: "text-muted-foreground bg-muted/50 border-border" },
    scheduled: { label: "Programado",  color: "text-blue-400 bg-blue-500/10 border-blue-500/20" },
    published: { label: "Publicado",   color: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20" },
    failed:    { label: "Error",       color: "text-red-400 bg-red-500/10 border-red-500/20" },
};

// ── Tabs ───────────────────────────────────────────────────────────────────────

const TABS = [
    { key: "cuentas",     label: "Cuentas",     icon: Link2 },
    { key: "crear",       label: "Crear post",  icon: PenSquare },
    { key: "programados", label: "Programados",  icon: CalendarClock },
    { key: "plan-ia",     label: "Plan IA",     icon: Sparkles },
] as const;

type TabKey = typeof TABS[number]["key"];

// ── Page ───────────────────────────────────────────────────────────────────────

export default function MarketingPage() {
    const [tab, setTab] = useState<TabKey>("cuentas");

    return (
        <div className="p-6 max-w-5xl mx-auto space-y-5">
            {/* Header */}
            <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-pink-500/10 border border-pink-500/20">
                    <Megaphone className="w-5 h-5 text-pink-400" />
                </div>
                <div>
                    <h1 className="text-lg font-semibold text-foreground">Marketing &amp; Redes Sociales</h1>
                    <p className="text-xs text-muted-foreground">Conecta tus redes, programa posts y genera contenido con IA</p>
                </div>
            </div>

            {/* Tabs */}
            <div className="flex gap-1 border-b border-border">
                {TABS.map(({ key, label, icon: Icon }) => (
                    <button
                        key={key}
                        onClick={() => setTab(key)}
                        className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px ${
                            tab === key
                                ? "border-pink-500 text-pink-400"
                                : "border-transparent text-muted-foreground hover:text-foreground"
                        }`}
                    >
                        <Icon className="w-3.5 h-3.5" />
                        {label}
                    </button>
                ))}
            </div>

            {tab === "cuentas"     && <TabCuentas />}
            {tab === "crear"       && <TabCrear />}
            {tab === "programados" && <TabProgramados />}
            {tab === "plan-ia"     && <TabPlanIA />}
        </div>
    );
}

// ── Tab: Cuentas ───────────────────────────────────────────────────────────────

function TabCuentas() {
    const [accounts, setAccounts] = useState<SocialAccount[]>([]);
    const [loading, setLoading] = useState(true);
    const [connecting, setConnecting] = useState<string | null>(null);
    const [connectError, setConnectError] = useState<string | null>(null);

    const load = useCallback(async () => {
        try {
            const data = await marketingApi.accounts.list();
            setAccounts(data);
        } catch {
            // sin cuentas aún
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { load(); }, [load]);

    // Refresca cuando el popup OAuth cierra con éxito (postMessage cross-origin)
    useEffect(() => {
        const handler = (e: MessageEvent) => {
            if (e.data?.type === "oauth-complete") load();
        };
        window.addEventListener("message", handler);
        return () => window.removeEventListener("message", handler);
    }, [load]);

    const connect = async (platform: string) => {
        setConnecting(platform);
        setConnectError(null);
        try {
            const { auth_url } = await marketingApi.accounts.connect(platform);
            // En Electron los OAuth de redes sociales abren en el browser del sistema.
            // window.open devuelve null pero el browser real maneja el flujo.
            // En Electron: IPC → shell.openExternal (100% fiable). En browser: window.open normal.
            const eAPI = (window as typeof window & { electronAPI?: { openExternal?: (u: string) => Promise<void> } }).electronAPI;
            if (eAPI?.openExternal) {
                await eAPI.openExternal(auth_url);
            } else {
                window.open(auth_url, "_blank", "width=600,height=700");
            }
            // Polling hasta 60s para detectar cuando el callback llegue al backend
            const before = accounts.map((a) => a.id);
            let attempts = 0;
            const iv = setInterval(async () => {
                attempts++;
                try {
                    const fresh = await marketingApi.accounts.list();
                    if (fresh.some((a) => !before.includes(a.id))) {
                        setAccounts(fresh);
                        clearInterval(iv);
                    }
                } catch { /* ignore */ }
                if (attempts >= 30) clearInterval(iv);
            }, 2000);
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : "Error al conectar";
            setConnectError(msg);
        } finally {
            setConnecting(null);
        }
    };

    const disconnect = async (id: string) => {
        try {
            await marketingApi.accounts.disconnect(id);
            setAccounts((prev) => prev.filter((a) => a.id !== id));
        } catch (err) {
            setConnectError(err instanceof Error ? err.message : "Error al desconectar la cuenta");
        }
    };

    return (
        <div className="space-y-4">
        {connectError && (
            <div className="flex items-center gap-2 text-red-400 text-xs bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
                <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
                {connectError}
            </div>
        )}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {PLATFORMS.map((p) => {
                const Icon = PLATFORM_ICONS[p.id];
                const account = accounts.find((a) => a.platform === p.id && a.is_active);
                const isConnecting = connecting === p.id;

                return (
                    <div key={p.id} className="bg-card border border-border rounded-xl p-4 flex items-start gap-4">
                        <div className={`p-2.5 rounded-xl ${p.iconBg} flex-shrink-0`}>
                            <Icon className={`w-5 h-5 ${p.colorClass.split(" ")[0]}`} />
                        </div>
                        <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-foreground">{p.name}</p>
                            {account ? (
                                <>
                                    <p className="text-xs text-muted-foreground truncate mt-0.5">
                                        {account.account_name ?? account.account_id}
                                    </p>
                                    <div className="flex items-center gap-1.5 mt-2">
                                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                                        <span className="text-[11px] text-emerald-400">Conectado</span>
                                        <button
                                            onClick={() => disconnect(account.id)}
                                            className="ml-auto text-[11px] text-muted-foreground hover:text-red-400 transition-colors"
                                        >
                                            Desconectar
                                        </button>
                                    </div>
                                </>
                            ) : (
                                <>
                                    <p className="text-xs text-muted-foreground mt-0.5">No conectado</p>
                                    <button
                                        onClick={() => connect(p.id)}
                                        disabled={isConnecting}
                                        className={`mt-2 flex items-center gap-1.5 text-[11px] px-3 py-1.5 rounded-lg border transition-colors ${p.colorClass} hover:opacity-80 disabled:opacity-50`}
                                    >
                                        {isConnecting
                                            ? <Loader2 className="w-3 h-3 animate-spin" />
                                            : <Plus className="w-3 h-3" />}
                                        Conectar
                                    </button>
                                </>
                            )}
                        </div>
                    </div>
                );
            })}
        </div>
        </div>
    );
}

// ── Tab: Crear post ────────────────────────────────────────────────────────────

function TabCrear() {
    const toast = useToastStore();
    const [accounts, setAccounts] = useState<SocialAccount[]>([]);
    const [selectedAccount, setSelectedAccount] = useState("");
    const [content, setContent] = useState("");
    const [imageUrl, setImageUrl] = useState("");
    const [scheduleAt, setScheduleAt] = useState("");
    const [publishNow, setPublishNow] = useState(true);
    const [loading, setLoading] = useState(false);
    const [success, setSuccess] = useState(false);

    const selectedPlatform = PLATFORMS.find(
        (p) => p.id === accounts.find((a) => a.id === selectedAccount)?.platform
    );
    const charLimit = selectedPlatform?.limit ?? 2200;
    const overLimit = content.length > charLimit;

    useEffect(() => {
        marketingApi.accounts.list()
            .then(setAccounts)
            .catch((err) => logError("marketing/crear-load-accounts", err));
    }, []);

    const submit = async () => {
        if (!selectedAccount || !content.trim()) return;
        setLoading(true);
        try {
            await marketingApi.posts.create({
                social_account_id: selectedAccount,
                platform: accounts.find((a) => a.id === selectedAccount)?.platform ?? "",
                content: content.trim(),
                image_url: imageUrl.trim() || undefined,
                scheduled_at: publishNow ? undefined : scheduleAt || undefined,
            });
            setSuccess(true);
            setContent("");
            setImageUrl("");
            setTimeout(() => setSuccess(false), 3000);
        } catch (err) {
            logError("marketing/crear-post", err);
            toast.error(err instanceof Error ? err.message : "No se pudo crear la publicación.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="space-y-4 max-w-2xl">
            {/* Cuenta */}
            <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground">Cuenta</label>
                {accounts.length === 0 ? (
                    <p className="text-xs text-muted-foreground bg-card border border-border rounded-lg px-3 py-2">
                        Conecta al menos una cuenta en la pestaña <strong>Cuentas</strong> primero.
                    </p>
                ) : (
                    <select
                        value={selectedAccount}
                        onChange={(e) => setSelectedAccount(e.target.value)}
                        className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-pink-500/50"
                    >
                        <option value="">Selecciona una cuenta…</option>
                        {accounts.map((a) => (
                            <option key={a.id} value={a.id}>
                                {a.account_name ?? a.account_id} · {a.platform}
                            </option>
                        ))}
                    </select>
                )}
            </div>

            {/* Contenido */}
            <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                    <label className="text-xs font-medium text-muted-foreground">Contenido</label>
                    <span className={`text-[11px] ${overLimit ? "text-red-400" : "text-muted-foreground"}`}>
                        {content.length} / {charLimit.toLocaleString()}
                    </span>
                </div>
                <textarea
                    value={content}
                    onChange={(e) => setContent(e.target.value)}
                    rows={5}
                    placeholder="Escribe el texto del post…"
                    className="w-full bg-background border border-border rounded-lg px-3 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-pink-500/50 resize-none"
                />
            </div>

            {/* Imagen */}
            <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground">URL de imagen (opcional)</label>
                <div className="flex gap-2">
                    <ImageIcon className="w-4 h-4 text-muted-foreground mt-2.5 flex-shrink-0" />
                    <input
                        type="url"
                        value={imageUrl}
                        onChange={(e) => setImageUrl(e.target.value)}
                        placeholder="https://…"
                        className="flex-1 bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-pink-500/50"
                    />
                </div>
            </div>

            {/* Programación */}
            <div className="space-y-2">
                <label className="text-xs font-medium text-muted-foreground">Publicación</label>
                <div className="flex gap-3">
                    <label className="flex items-center gap-2 cursor-pointer">
                        <input type="radio" checked={publishNow} onChange={() => setPublishNow(true)} className="accent-pink-500" />
                        <span className="text-sm text-foreground">Publicar ahora</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                        <input type="radio" checked={!publishNow} onChange={() => setPublishNow(false)} className="accent-pink-500" />
                        <span className="text-sm text-foreground">Programar</span>
                    </label>
                </div>
                {!publishNow && (
                    <input
                        type="datetime-local"
                        value={scheduleAt}
                        onChange={(e) => setScheduleAt(e.target.value)}
                        className="bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-pink-500/50"
                    />
                )}
            </div>

            {success && (
                <div className="flex items-center gap-2 text-emerald-400 text-sm bg-emerald-500/10 border border-emerald-500/20 rounded-lg px-3 py-2">
                    <CheckCircle2 className="w-4 h-4" />
                    Post {publishNow ? "publicado" : "programado"} correctamente.
                </div>
            )}

            <button
                onClick={submit}
                disabled={loading || !selectedAccount || !content.trim() || overLimit}
                className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-pink-600 hover:bg-pink-500 disabled:opacity-50 text-white text-sm font-medium transition-colors"
            >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                {loading ? "Enviando…" : publishNow ? "Publicar" : "Programar"}
            </button>
        </div>
    );
}

// ── Tab: Programados ───────────────────────────────────────────────────────────

function TabProgramados() {
    const toast = useToastStore();
    const [posts, setPosts] = useState<ScheduledPost[]>([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState<string>("all");

    const load = useCallback(async () => {
        try {
            const data = await marketingApi.posts.list(filter !== "all" ? { status: filter } : undefined);
            setPosts(data);
        } catch (err) {
            logError("marketing/programados", err);
        } finally {
            setLoading(false);
        }
    }, [filter]);

    useEffect(() => { load(); }, [load]);

    const remove = async (id: string) => {
        try {
            await marketingApi.posts.delete(id);
            setPosts((prev) => prev.filter((p) => p.id !== id));
        } catch (err) {
            toast.error(err instanceof Error ? err.message : "Error al eliminar la publicación");
        }
    };

    const fmt = (iso: string | null) => iso
        ? new Date(iso).toLocaleString("es-ES", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })
        : "—";

    return (
        <div className="space-y-4">
            {/* Filtro */}
            <div className="flex gap-2 flex-wrap">
                {(["all", "scheduled", "published", "draft", "failed"] as const).map((s) => (
                    <button
                        key={s}
                        onClick={() => setFilter(s)}
                        className={`text-[11px] px-3 py-1.5 rounded-full border transition-colors ${
                            filter === s
                                ? "border-pink-500 text-pink-400 bg-pink-500/10"
                                : "border-border text-muted-foreground hover:text-foreground"
                        }`}
                    >
                        {s === "all" ? "Todos" : STATUS_CONFIG[s as keyof typeof STATUS_CONFIG]?.label ?? s}
                    </button>
                ))}
            </div>

            {loading && (
                <div className="flex justify-center py-10">
                    <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
                </div>
            )}

            {!loading && posts.length === 0 && (
                <div className="flex flex-col items-center justify-center py-16 text-center">
                    <CalendarClock className="w-8 h-8 text-muted-foreground/30 mb-3" />
                    <p className="text-sm text-muted-foreground">No hay posts en este estado</p>
                </div>
            )}

            <div className="space-y-3">
                {posts.map((post) => {
                    const cfg = STATUS_CONFIG[post.status];
                    const platCfg = PLATFORMS.find((p) => p.id === post.platform);
                    return (
                        <div key={post.id} className="bg-card border border-border rounded-xl p-4 space-y-2">
                            <div className="flex items-center justify-between gap-2">
                                <div className="flex items-center gap-2 flex-wrap">
                                    <span className={`text-[10px] px-2 py-0.5 rounded-full border font-medium ${platCfg?.colorClass ?? "text-muted-foreground border-border"}`}>
                                        {platCfg?.name ?? post.platform}
                                    </span>
                                    <span className={`text-[10px] px-2 py-0.5 rounded-full border font-medium ${cfg?.color}`}>
                                        {cfg?.label}
                                    </span>
                                </div>
                                <div className="flex items-center gap-3">
                                    <span className="text-[11px] text-muted-foreground flex items-center gap-1">
                                        <Clock className="w-3 h-3" />
                                        {fmt(post.scheduled_at ?? post.published_at)}
                                    </span>
                                    {post.status !== "published" && (
                                        <button onClick={() => remove(post.id)} className="text-muted-foreground hover:text-red-400 transition-colors">
                                            <Trash2 className="w-3.5 h-3.5" />
                                        </button>
                                    )}
                                </div>
                            </div>
                            <p className="text-sm text-foreground line-clamp-3 leading-relaxed">{post.content}</p>
                            {post.error_message && (
                                <div className="flex items-start gap-1.5 text-[11px] text-red-400">
                                    <AlertCircle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
                                    {post.error_message}
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

// ── Tab: Plan IA ───────────────────────────────────────────────────────────────

function TabPlanIA() {
    const toast = useToastStore();
    const [prompt, setPrompt] = useState("");
    const [generating, setGenerating] = useState(false);
    const [publishingAll, setPublishingAll] = useState(false);
    const [publishing, setPublishing] = useState<Set<string>>(new Set());
    const [summary, setSummary] = useState<string | null>(null);
    const [drafts, setDrafts] = useState<ScheduledPost[]>([]);
    const [error, setError] = useState<string | null>(null);

    const generate = async () => {
        if (!prompt.trim() || generating) return;
        setGenerating(true);
        setError(null);
        setSummary(null);
        setDrafts([]);
        try {
            const resp = await marketingApi.agent.generatePlan(prompt);
            setSummary(resp.summary);
            if (resp.post_ids.length > 0) {
                const allDrafts = await marketingApi.posts.list({ status: "draft" });
                setDrafts(allDrafts.filter((p) => resp.post_ids.includes(p.id)));
            }
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "Error al generar el plan");
        } finally {
            setGenerating(false);
        }
    };

    const publishOne = async (id: string) => {
        setPublishing((prev) => new Set([...prev, id]));
        try {
            const updated = await marketingApi.posts.publish(id);
            setDrafts((prev) => prev.map((p) => (p.id === id ? updated : p)));
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : "Error al publicar";
            setDrafts((prev) =>
                prev.map((p) => (p.id === id ? { ...p, status: "failed" as const, error_message: msg } : p))
            );
        } finally {
            setPublishing((prev) => { const s = new Set(prev); s.delete(id); return s; });
        }
    };

    const publishAll = async () => {
        const ids = drafts.filter((d) => d.status !== "published").map((d) => d.id);
        if (!ids.length) return;
        setPublishingAll(true);
        try {
            const result = await marketingApi.posts.publishBatch(ids);
            setDrafts((prev) =>
                prev.map((p) => {
                    if (result.published.includes(p.id)) return { ...p, status: "published" as const, error_message: null };
                    if (result.failed.includes(p.id)) return { ...p, status: "failed" as const };
                    return p;
                })
            );
        } catch (err) {
            logError("marketing/publish-all", err);
            toast.error(err instanceof Error ? err.message : "No se pudieron publicar los borradores.");
        }
        setPublishingAll(false);
    };

    const removePost = async (id: string) => {
        try {
            await marketingApi.posts.delete(id);
            setDrafts((prev) => prev.filter((p) => p.id !== id));
        } catch (err) {
            logError("marketing/remove-post", err);
            toast.error(err instanceof Error ? err.message : "No se pudo eliminar el borrador.");
        }
    };

    const pendingCount = drafts.filter((d) => d.status !== "published").length;

    return (
        <div className="space-y-4 max-w-3xl">
            {/* Input */}
            <div className="bg-card border border-border rounded-xl p-4 space-y-3">
                <label className="text-xs font-medium text-muted-foreground">Describe el plan de contenidos que necesitas</label>
                <div className="flex gap-2">
                    <input
                        type="text"
                        value={prompt}
                        onChange={(e) => setPrompt(e.target.value)}
                        placeholder="Ej: Plan semanal para el lanzamiento del producto X con posts en Instagram y LinkedIn…"
                        className="flex-1 bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-pink-500/50"
                        onKeyDown={(e) => e.key === "Enter" && !generating && generate()}
                        disabled={generating}
                    />
                    <button
                        onClick={generate}
                        disabled={generating || !prompt.trim()}
                        className="flex items-center gap-2 px-4 py-2 rounded-lg bg-pink-600 hover:bg-pink-500 disabled:opacity-50 text-white text-sm font-medium transition-colors whitespace-nowrap"
                    >
                        {generating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                        {generating ? "Generando…" : "Generar plan"}
                    </button>
                </div>
                {generating && (
                    <p className="text-xs text-muted-foreground animate-pulse">
                        La IA analiza tu catálogo, busca imágenes y crea los borradores…
                    </p>
                )}
            </div>

            {error && (
                <div className="flex items-center gap-2 text-red-400 text-sm bg-red-500/10 border border-red-500/20 rounded-xl p-3">
                    <AlertCircle className="w-4 h-4 flex-shrink-0" />
                    {error}
                </div>
            )}

            {/* Resumen + botón global */}
            {summary && (
                <div className="bg-card border border-border rounded-xl p-4 space-y-3">
                    <p className="text-sm text-foreground leading-relaxed whitespace-pre-wrap">{summary}</p>
                    {pendingCount > 0 && (
                        <button
                            onClick={publishAll}
                            disabled={publishingAll}
                            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-pink-600 hover:bg-pink-500 disabled:opacity-50 text-white text-sm font-medium transition-colors"
                        >
                            {publishingAll ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                            Publicar todo ahora ({pendingCount})
                        </button>
                    )}
                </div>
            )}

            {/* Cards de borradores */}
            {drafts.length > 0 && (
                <div className="space-y-3">
                    {drafts.map((post) => {
                        const platCfg = PLATFORMS.find((p) => p.id === post.platform);
                        const Icon = PLATFORM_ICONS[post.platform] ?? Megaphone;
                        const isPending = publishing.has(post.id);
                        const isPublished = post.status === "published";
                        const isFailed = post.status === "failed";
                        return (
                            <div
                                key={post.id}
                                className={`bg-card border rounded-xl p-4 space-y-3 transition-colors ${
                                    isPublished ? "border-emerald-500/30" : isFailed ? "border-red-500/30" : "border-border"
                                }`}
                            >
                                {/* Header */}
                                <div className="flex items-center justify-between gap-2">
                                    <div className="flex items-center gap-2 flex-wrap">
                                        <div className={`p-1.5 rounded-lg ${platCfg?.iconBg ?? "bg-muted"}`}>
                                            <Icon className={`w-3.5 h-3.5 ${platCfg?.colorClass?.split(" ")[0] ?? "text-muted-foreground"}`} />
                                        </div>
                                        <span className="text-xs font-medium text-foreground">{platCfg?.name ?? post.platform}</span>
                                        {isPublished && (
                                            <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                                                Publicado
                                            </span>
                                        )}
                                        {isFailed && (
                                            <span className="text-[10px] px-2 py-0.5 rounded-full bg-red-500/10 text-red-400 border border-red-500/20">
                                                Error
                                            </span>
                                        )}
                                    </div>
                                    <div className="flex items-center gap-2">
                                        {post.scheduled_at && (
                                            <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                                                <Clock className="w-3 h-3" />
                                                {new Date(post.scheduled_at).toLocaleString("es-ES", {
                                                    day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit",
                                                })}
                                            </span>
                                        )}
                                        {!isPublished && (
                                            <button
                                                onClick={() => removePost(post.id)}
                                                className="text-muted-foreground hover:text-red-400 transition-colors"
                                            >
                                                <Trash2 className="w-3.5 h-3.5" />
                                            </button>
                                        )}
                                    </div>
                                </div>

                                {/* Imagen */}
                                {post.image_url && (
                                    // eslint-disable-next-line @next/next/no-img-element
                                    <img
                                        src={post.image_url}
                                        alt="Vista previa"
                                        className="w-full h-36 object-cover rounded-lg"
                                        onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                                    />
                                )}

                                {/* Contenido */}
                                <p className="text-sm text-foreground leading-relaxed whitespace-pre-wrap">{post.content}</p>

                                {post.error_message && (
                                    <div className="flex items-start gap-1.5 text-[11px] text-red-400">
                                        <AlertCircle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
                                        {post.error_message}
                                    </div>
                                )}

                                {!isPublished && (
                                    <button
                                        onClick={() => publishOne(post.id)}
                                        disabled={isPending}
                                        className="flex items-center gap-1.5 text-[11px] px-3 py-1.5 rounded-lg bg-pink-600/20 hover:bg-pink-600/40 text-pink-400 border border-pink-500/20 transition-colors disabled:opacity-50"
                                    >
                                        {isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : <Send className="w-3 h-3" />}
                                        Publicar ahora
                                    </button>
                                )}

                                {isPublished && post.platform_post_id && (
                                    <span className="text-[10px] text-emerald-400/60">ID: {post.platform_post_id}</span>
                                )}
                            </div>
                        );
                    })}
                </div>
            )}

            {/* Estado vacío */}
            {!summary && !generating && !error && (
                <div className="flex flex-col items-center justify-center py-16 text-center">
                    <div className="p-4 rounded-2xl bg-pink-500/5 border border-pink-500/10 mb-4">
                        <Sparkles className="w-8 h-8 text-pink-500/40" />
                    </div>
                    <p className="text-sm text-muted-foreground mb-1">Sin planes generados aún</p>
                    <p className="text-xs text-muted-foreground">
                        La IA analiza tu catálogo, busca imágenes y crea borradores listos para publicar
                    </p>
                </div>
            )}
        </div>
    );
}
