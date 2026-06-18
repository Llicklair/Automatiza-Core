"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { X, Loader2, Save, ImageIcon, CalendarClock, Sparkles } from "lucide-react";
import { marketingApi, ScheduledPost, UpdatePostInput } from "@/lib/api/marketing";
import { useToastStore } from "@/stores/toast";

// ISO (UTC) → valor para <input type="datetime-local"> en hora local
function toLocalInput(iso: string | null): string {
    if (!iso) return "";
    const d = new Date(iso);
    if (isNaN(d.getTime())) return "";
    const pad = (n: number) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

const LIMITS: Record<string, number> = { twitter: 280, linkedin: 3000, instagram: 2200, facebook: 63206 };

export function EditPostModal({
    post,
    onClose,
    onSaved,
}: {
    post: ScheduledPost;
    onClose: () => void;
    onSaved: (updated: ScheduledPost) => void;
}) {
    const t = useTranslations("marketing.editPost");
    const tc = useTranslations("marketing.common");
    const toast = useToastStore();
    const [content, setContent] = useState(post.content);
    const [imageUrl, setImageUrl] = useState(post.image_url ?? "");
    const [when, setWhen] = useState(toLocalInput(post.scheduled_at));
    const [saving, setSaving] = useState(false);
    const [genImg, setGenImg] = useState(false);

    const limit = LIMITS[post.platform] ?? 2200;
    const over = content.length > limit;

    const generateImg = async () => {
        const prompt = content.trim();
        if (!prompt) { toast.error(t("imagePromptFirst")); return; }
        setGenImg(true);
        try {
            const { url } = await marketingApi.agent.generateImage(prompt);
            setImageUrl(url);
        } catch (err) {
            toast.error(err instanceof Error ? err.message : t("imageGenFail"));
        } finally {
            setGenImg(false);
        }
    };

    const save = async () => {
        if (over) { toast.error(t("overLimit", { limit, platform: post.platform })); return; }
        setSaving(true);
        try {
            const data: UpdatePostInput = { content, image_url: imageUrl.trim() };
            if (when) data.scheduled_at = new Date(when).toISOString();
            const updated = await marketingApi.posts.update(post.id, data);
            onSaved(updated);
            onClose();
        } catch (err) {
            toast.error(err instanceof Error ? err.message : t("saveError"));
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={onClose}>
            <div
                className="bg-card border border-border rounded-xl w-full max-w-lg p-5 space-y-4 max-h-[90vh] overflow-y-auto"
                onClick={(e) => e.stopPropagation()}
            >
                <div className="flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-foreground">{t("title", { platform: post.platform })}</h3>
                    <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
                        <X className="w-4 h-4" />
                    </button>
                </div>

                {/* Texto */}
                <div>
                    <label className="text-xs text-muted-foreground">{t("textLabel")}</label>
                    <textarea
                        value={content}
                        onChange={(e) => setContent(e.target.value)}
                        rows={6}
                        className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground mt-1 resize-y focus:outline-none focus:ring-1 focus:ring-pink-500/50"
                    />
                    <div className={`text-[10px] text-right mt-0.5 ${over ? "text-red-400" : "text-muted-foreground"}`}>
                        {content.length} / {limit}
                    </div>
                </div>

                {/* Imagen */}
                <div>
                    <label className="text-xs text-muted-foreground flex items-center gap-1">
                        <ImageIcon className="w-3.5 h-3.5" /> {t("imageLabel")}
                    </label>
                    <div className="flex gap-2 mt-1">
                        <input
                            value={imageUrl}
                            onChange={(e) => setImageUrl(e.target.value)}
                            placeholder={tc("imagePlaceholder")}
                            className="flex-1 bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-pink-500/50"
                        />
                        <button
                            type="button"
                            onClick={generateImg}
                            disabled={genImg || !content.trim()}
                            title={t("generateAiTitle")}
                            className="flex items-center gap-1.5 px-3 rounded-lg border border-purple-500/30 text-purple-300 bg-purple-500/10 hover:bg-purple-500/20 disabled:opacity-50 text-xs whitespace-nowrap transition-colors"
                        >
                            {genImg ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
                            {tc("generateAi")}
                        </button>
                    </div>
                    {imageUrl && (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img
                            src={imageUrl}
                            alt={tc("previewAlt")}
                            className="w-full h-32 object-cover rounded-lg mt-2"
                            onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                        />
                    )}
                </div>

                {/* Fecha (calendario) */}
                <div>
                    <label className="text-xs text-muted-foreground flex items-center gap-1">
                        <CalendarClock className="w-3.5 h-3.5" /> {t("dateLabel")}
                    </label>
                    <input
                        type="datetime-local"
                        value={when}
                        onChange={(e) => setWhen(e.target.value)}
                        className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground mt-1 focus:outline-none focus:ring-1 focus:ring-pink-500/50"
                    />
                    <p className="text-[10px] text-muted-foreground mt-0.5">{t("dateNote")}</p>
                    {when && (
                        <p className="text-[10px] text-amber-400/90 mt-0.5">
                            {t("dateWarning")}
                        </p>
                    )}
                </div>

                <div className="flex justify-end gap-2 pt-1">
                    <button onClick={onClose} className="text-sm px-3 py-2 rounded-lg border border-border text-muted-foreground hover:text-foreground transition-colors">
                        {tc("cancel")}
                    </button>
                    <button
                        onClick={save}
                        disabled={saving || over}
                        className="flex items-center gap-1.5 text-sm px-4 py-2 rounded-lg bg-pink-600 hover:bg-pink-500 text-white font-medium disabled:opacity-50 transition-colors"
                    >
                        {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />} {t("save")}
                    </button>
                </div>
            </div>
        </div>
    );
}
