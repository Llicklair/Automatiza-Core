"use client";

import { useState, useEffect, useCallback } from "react";
import {
    Megaphone, Link2, PenSquare, CalendarClock, Sparkles,
    Loader2, Send, Hash, ImageIcon, Clock, Calendar,
    CheckCircle2, AlertCircle, Trash2, Plus,
} from "lucide-react";
import { useMarketingPage, PLATFORM_COLORS } from "./_hooks/useMarketingPage";
import { marketingApi, SocialAccount, ScheduledPost } from "@/lib/api/marketing";

// SVG icons para plataformas (lucide-react no incluye redes sociales)
const IgIcon = ({ className }: { className?: string }) => (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98C8.333 23.986 8.741 24 12 24c3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 100 12.324 6.162 6.162 0 000-12.324zM12 16a4 4 0 110-8 4 4 0 010 8zm6.406-11.845a1.44 1.44 0 100 2.881 1.44 1.44 0 000-2.881z"/>
    </svg>
);
const FbIcon = ({ className }: { className?: string }) => (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
        <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
    </svg>
);
const LiIcon = ({ className }: { className?: string }) => (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
        <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
    </svg>
);
const XIcon = ({ className }: { className?: string }) => (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
        <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-4.714-6.231-5.401 6.231H2.744l7.73-8.835L1.254 2.25H8.08l4.253 5.622zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
    </svg>
);

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

const PLATFORM_ICONS: Record<string, React.ElementType> = {
    instagram: IgIcon,
    facebook: FbIcon,
    linkedin: LiIcon,
    twitter: XIcon,
};

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
            const popup = window.open(auth_url, "_blank", "width=600,height=700");
            if (!popup) setConnectError("El navegador bloqueó el popup. Permite popups para esta página.");
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
        } catch {}
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
            .catch(() => {});
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
        } catch {
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
    const [posts, setPosts] = useState<ScheduledPost[]>([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState<string>("all");

    const load = useCallback(async () => {
        try {
            const data = await marketingApi.posts.list(filter !== "all" ? { status: filter } : undefined);
            setPosts(data);
        } catch {
        } finally {
            setLoading(false);
        }
    }, [filter]);

    useEffect(() => { load(); }, [load]);

    const remove = async (id: string) => {
        try {
            await marketingApi.posts.delete(id);
            setPosts((prev) => prev.filter((p) => p.id !== id));
        } catch {}
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
    const { plan, loading, error, prompt, setPrompt, generatePlan } = useMarketingPage();

    return (
        <div className="space-y-4 max-w-3xl">
            <div className="bg-card border border-border rounded-xl p-4 space-y-3">
                <label className="text-xs font-medium text-muted-foreground">Instrucciones (opcional)</label>
                <div className="flex gap-2">
                    <input
                        type="text"
                        value={prompt}
                        onChange={(e) => setPrompt(e.target.value)}
                        placeholder="Ej: Plan semanal enfocado en el lanzamiento del producto X…"
                        className="flex-1 bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-pink-500/50"
                        onKeyDown={(e) => e.key === "Enter" && !loading && generatePlan()}
                    />
                    <button
                        onClick={generatePlan}
                        disabled={loading}
                        className="flex items-center gap-2 px-4 py-2 rounded-lg bg-pink-600 hover:bg-pink-500 disabled:opacity-50 text-white text-sm font-medium transition-colors"
                    >
                        {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                        {loading ? "Generando…" : "Generar plan"}
                    </button>
                </div>
            </div>

            {error && !plan && (
                <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 text-sm text-red-300">{error}</div>
            )}

            {plan && (
                <div className="bg-card border border-border rounded-xl p-4">
                    <div className="flex items-center gap-3 mb-1">
                        <Calendar className="w-4 h-4 text-pink-400" />
                        <span className="text-sm font-medium text-foreground">{plan.period}</span>
                    </div>
                    {plan.focus && <p className="text-xs text-muted-foreground ml-7">{plan.focus}</p>}
                </div>
            )}

            {plan && plan.posts.length > 0 && (
                <div className="grid gap-3">
                    {plan.posts.map((post, i) => (
                        <div key={i} className="bg-card border border-border rounded-xl p-4 space-y-3">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <span className="text-xs font-medium text-foreground">{post.day}</span>
                                    <span className={`text-[10px] px-2 py-0.5 rounded-full border font-medium ${PLATFORM_COLORS[post.platform] ?? "bg-muted text-muted-foreground border-border"}`}>
                                        {post.platform}
                                    </span>
                                    {post.product && (
                                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20">
                                            {post.product}
                                        </span>
                                    )}
                                </div>
                                <div className="flex items-center gap-1 text-muted-foreground">
                                    <Clock className="w-3 h-3" />
                                    <span className="text-[10px]">{post.best_time}</span>
                                </div>
                            </div>
                            <p className="text-sm text-foreground leading-relaxed whitespace-pre-wrap">{post.text}</p>
                            {post.hashtags?.length > 0 && (
                                <div className="flex items-center gap-1.5 flex-wrap">
                                    <Hash className="w-3 h-3 text-muted-foreground" />
                                    {post.hashtags.map((tag, j) => (
                                        <span key={j} className="text-[10px] text-pink-400/80">{tag}</span>
                                    ))}
                                </div>
                            )}
                            {post.image_idea && (
                                <div className="flex items-start gap-2 bg-background rounded-lg p-2.5">
                                    <ImageIcon className="w-3.5 h-3.5 text-muted-foreground mt-0.5 flex-shrink-0" />
                                    <span className="text-[11px] text-muted-foreground">{post.image_idea}</span>
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}

            {!plan && !loading && !error && (
                <div className="flex flex-col items-center justify-center py-16 text-center">
                    <div className="p-4 rounded-2xl bg-pink-500/5 border border-pink-500/10 mb-4">
                        <Sparkles className="w-8 h-8 text-pink-500/40" />
                    </div>
                    <p className="text-sm text-muted-foreground mb-1">Sin planes generados aún</p>
                    <p className="text-xs text-muted-foreground">La IA analiza tu catálogo y crea un plan de contenidos completo</p>
                </div>
            )}
        </div>
    );
}
