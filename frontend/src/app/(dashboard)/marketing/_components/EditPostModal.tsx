"use client";

import { useState } from "react";
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
        if (!prompt) { toast.error("Escribe primero el texto del post para generar una imagen acorde."); return; }
        setGenImg(true);
        try {
            const { url } = await marketingApi.agent.generateImage(prompt);
            setImageUrl(url);
        } catch (err) {
            toast.error(err instanceof Error ? err.message : "No se pudo generar la imagen.");
        } finally {
            setGenImg(false);
        }
    };

    const save = async () => {
        if (over) { toast.error(`El texto supera el límite de ${limit} caracteres para ${post.platform}.`); return; }
        setSaving(true);
        try {
            const data: UpdatePostInput = { content, image_url: imageUrl.trim() };
            if (when) data.scheduled_at = new Date(when).toISOString();
            const updated = await marketingApi.posts.update(post.id, data);
            onSaved(updated);
            onClose();
        } catch (err) {
            toast.error(err instanceof Error ? err.message : "Error al guardar el post");
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
                    <h3 className="text-sm font-semibold text-foreground">Editar post · {post.platform}</h3>
                    <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
                        <X className="w-4 h-4" />
                    </button>
                </div>

                {/* Texto */}
                <div>
                    <label className="text-xs text-muted-foreground">Texto</label>
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
                        <ImageIcon className="w-3.5 h-3.5" /> Imagen
                    </label>
                    <div className="flex gap-2 mt-1">
                        <input
                            value={imageUrl}
                            onChange={(e) => setImageUrl(e.target.value)}
                            placeholder="https://… o genera una con IA"
                            className="flex-1 bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-pink-500/50"
                        />
                        <button
                            type="button"
                            onClick={generateImg}
                            disabled={genImg || !content.trim()}
                            title="Genera una imagen con IA a partir del texto del post"
                            className="flex items-center gap-1.5 px-3 rounded-lg border border-purple-500/30 text-purple-300 bg-purple-500/10 hover:bg-purple-500/20 disabled:opacity-50 text-xs whitespace-nowrap transition-colors"
                        >
                            {genImg ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
                            Generar IA
                        </button>
                    </div>
                    {imageUrl && (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img
                            src={imageUrl}
                            alt="Vista previa"
                            className="w-full h-32 object-cover rounded-lg mt-2"
                            onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                        />
                    )}
                </div>

                {/* Fecha (calendario) */}
                <div>
                    <label className="text-xs text-muted-foreground flex items-center gap-1">
                        <CalendarClock className="w-3.5 h-3.5" /> Fecha de publicación (asignar al calendario)
                    </label>
                    <input
                        type="datetime-local"
                        value={when}
                        onChange={(e) => setWhen(e.target.value)}
                        className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground mt-1 focus:outline-none focus:ring-1 focus:ring-pink-500/50"
                    />
                    <p className="text-[10px] text-muted-foreground mt-0.5">Al poner fecha, el post queda programado y se publica solo.</p>
                    {when && (
                        <p className="text-[10px] text-amber-400/90 mt-0.5">
                            ⚠️ La app debe seguir abierta a esa hora. Las imágenes IA caducan (~2h): para
                            programar a futuro usa una URL de imagen fija.
                        </p>
                    )}
                </div>

                <div className="flex justify-end gap-2 pt-1">
                    <button onClick={onClose} className="text-sm px-3 py-2 rounded-lg border border-border text-muted-foreground hover:text-foreground transition-colors">
                        Cancelar
                    </button>
                    <button
                        onClick={save}
                        disabled={saving || over}
                        className="flex items-center gap-1.5 text-sm px-4 py-2 rounded-lg bg-pink-600 hover:bg-pink-500 text-white font-medium disabled:opacity-50 transition-colors"
                    >
                        {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />} Guardar
                    </button>
                </div>
            </div>
        </div>
    );
}
