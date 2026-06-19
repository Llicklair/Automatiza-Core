"use client";

import { useState, useEffect, useCallback } from "react";
import { useTranslations } from "next-intl";
import { CalendarClock, Loader2, Clock, AlertCircle, Trash2, CalendarDays, List, Send, Pencil } from "lucide-react";
import { marketingApi, ScheduledPost } from "@/lib/api/marketing";
import { useToastStore } from "@/stores/toast";
import { logError } from "@/lib/logger";
import { PLATFORMS } from "./constants";
import { PostsCalendar } from "./PostsCalendar";
import { EditPostModal } from "./EditPostModal";

const STATUS_COLOR = {
    draft:     "text-muted-foreground bg-muted/50 border-border",
    scheduled: "text-blue-400 bg-blue-500/10 border-blue-500/20",
    published: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
    failed:    "text-red-400 bg-red-500/10 border-red-500/20",
} as const;

// ── Tab: Programados ───────────────────────────────────────────────────────────

export function TabProgramados() {
    const t = useTranslations("marketing.programados");
    const ts = useTranslations("marketing.status");
    const tc = useTranslations("marketing.common");
    const toast = useToastStore();
    const [posts, setPosts] = useState<ScheduledPost[]>([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState<string>("all");
    const [view, setView] = useState<"list" | "calendar">("list");
    const [publishing, setPublishing] = useState<Set<string>>(new Set());
    const [editing, setEditing] = useState<ScheduledPost | null>(null);

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
            toast.error(err instanceof Error ? err.message : t("deleteFail"));
        }
    };

    const publishNow = async (id: string) => {
        setPublishing((prev) => new Set([...prev, id]));
        try {
            const updated = await marketingApi.posts.publish(id);
            setPosts((prev) => prev.map((p) => (p.id === id ? updated : p)));
        } catch (err) {
            const msg = err instanceof Error ? err.message : t("publishError");
            setPosts((prev) =>
                prev.map((p) => (p.id === id ? { ...p, status: "failed" as const, error_message: msg } : p))
            );
            toast.error(msg);
        } finally {
            setPublishing((prev) => { const s = new Set(prev); s.delete(id); return s; });
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
                        {s === "all" ? t("filterAll") : ts(s)}
                    </button>
                ))}
            </div>

            {/* Toggle Lista / Calendario */}
            <div className="flex justify-end">
                <div className="inline-flex bg-card border border-border rounded-lg p-0.5">
                    {([["list", t("viewList")], ["calendar", t("viewCalendar")]] as const).map(([v, label]) => (
                        <button
                            key={v}
                            onClick={() => setView(v)}
                            className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-md transition-colors ${
                                view === v ? "bg-pink-500/10 text-pink-400" : "text-muted-foreground hover:text-foreground"
                            }`}
                        >
                            {v === "list" ? <List className="w-3.5 h-3.5" /> : <CalendarDays className="w-3.5 h-3.5" />} {label}
                        </button>
                    ))}
                </div>
            </div>

            {loading && (
                <div className="flex justify-center py-10">
                    <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
                </div>
            )}

            {!loading && posts.length === 0 && (
                <div className="flex flex-col items-center justify-center py-16 text-center">
                    <CalendarClock className="w-8 h-8 text-muted-foreground/30 mb-3" />
                    <p className="text-sm text-muted-foreground">{t("emptyState")}</p>
                </div>
            )}

            {view === "calendar" && <PostsCalendar posts={posts} onRemove={remove} />}

            {view === "list" && (
            <div className="space-y-3">
                {posts.map((post) => {
                    const statusColor = STATUS_COLOR[post.status];
                    const platCfg = PLATFORMS.find((p) => p.id === post.platform);
                    return (
                        <div key={post.id} className="bg-card border border-border rounded-xl p-4 space-y-2">
                            <div className="flex items-center justify-between gap-2">
                                <div className="flex items-center gap-2 flex-wrap">
                                    <span className={`text-[10px] px-2 py-0.5 rounded-full border font-medium ${platCfg?.colorClass ?? "text-muted-foreground border-border"}`}>
                                        {platCfg?.name ?? post.platform}
                                    </span>
                                    <span className={`text-[10px] px-2 py-0.5 rounded-full border font-medium ${statusColor}`}>
                                        {ts(post.status)}
                                    </span>
                                </div>
                                <div className="flex items-center gap-3">
                                    <span className="text-[11px] text-muted-foreground flex items-center gap-1">
                                        <Clock className="w-3 h-3" />
                                        {fmt(post.scheduled_at ?? post.published_at)}
                                    </span>
                                    {post.status !== "published" && (
                                        <button
                                            onClick={() => setEditing(post)}
                                            className="text-muted-foreground hover:text-pink-400 transition-colors"
                                            title={t("editTitle")}
                                        >
                                            <Pencil className="w-3.5 h-3.5" />
                                        </button>
                                    )}
                                    {post.status !== "published" && (
                                        <button
                                            onClick={() => publishNow(post.id)}
                                            disabled={publishing.has(post.id)}
                                            className="text-[11px] px-2.5 py-1 rounded-lg bg-pink-600/20 hover:bg-pink-600/40 text-pink-400 border border-pink-500/20 transition-colors disabled:opacity-50 flex items-center gap-1"
                                        >
                                            {publishing.has(post.id)
                                                ? <Loader2 className="w-3 h-3 animate-spin" />
                                                : <Send className="w-3 h-3" />}
                                            {tc("publishNow")}
                                        </button>
                                    )}
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
            )}

            {editing && (
                <EditPostModal
                    post={editing}
                    onClose={() => setEditing(null)}
                    onSaved={(u) => setPosts((prev) => prev.map((p) => (p.id === u.id ? u : p)))}
                />
            )}
        </div>
    );
}
