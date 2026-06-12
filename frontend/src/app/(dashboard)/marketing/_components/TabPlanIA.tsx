"use client";

import { useState } from "react";
import { Megaphone, Sparkles, Loader2, Send, Clock, AlertCircle, Trash2 } from "lucide-react";
import { marketingApi, ScheduledPost } from "@/lib/api/marketing";
import { PLATFORM_ICONS } from "@/components/ui/social-icons";
import { useToastStore } from "@/stores/toast";
import { logError } from "@/lib/logger";
import { PLATFORMS } from "./constants";

// ── Tab: Plan IA ───────────────────────────────────────────────────────────────

export function TabPlanIA() {
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
                        placeholder="Ej: Plan semanal para el lanzamiento del producto X con posts en Instagram y Facebook…"
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
