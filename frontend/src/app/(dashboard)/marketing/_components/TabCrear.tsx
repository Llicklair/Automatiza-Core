"use client";

import { useState, useEffect } from "react";
import { Loader2, Send, ImageIcon, CheckCircle2, Sparkles } from "lucide-react";
import { marketingApi, SocialAccount } from "@/lib/api/marketing";
import { useToastStore } from "@/stores/toast";
import { logError } from "@/lib/logger";
import { PLATFORMS } from "./constants";

// ── Tab: Crear post ────────────────────────────────────────────────────────────

export function TabCrear() {
    const toast = useToastStore();
    const [accounts, setAccounts] = useState<SocialAccount[]>([]);
    const [selectedAccount, setSelectedAccount] = useState("");
    const [content, setContent] = useState("");
    const [imageUrl, setImageUrl] = useState("");
    const [scheduleAt, setScheduleAt] = useState("");
    const [publishNow, setPublishNow] = useState(true);
    const [loading, setLoading] = useState(false);
    const [genImg, setGenImg] = useState(false);
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

    const generateImg = async () => {
        const prompt = content.trim();
        if (!prompt) {
            toast.error("Escribe primero el contenido del post para generar una imagen acorde.");
            return;
        }
        setGenImg(true);
        try {
            const { url } = await marketingApi.agent.generateImage(prompt);
            setImageUrl(url);
        } catch (err) {
            logError("marketing/generar-imagen", err);
            toast.error(err instanceof Error ? err.message : "No se pudo generar la imagen.");
        } finally {
            setGenImg(false);
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
                <label className="text-xs font-medium text-muted-foreground">Imagen (opcional)</label>
                <div className="flex gap-2">
                    <ImageIcon className="w-4 h-4 text-muted-foreground mt-2.5 flex-shrink-0" />
                    <input
                        type="url"
                        value={imageUrl}
                        onChange={(e) => setImageUrl(e.target.value)}
                        placeholder="https://… o genera una con IA"
                        className="flex-1 bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-pink-500/50"
                    />
                    <button
                        type="button"
                        onClick={generateImg}
                        disabled={genImg || !content.trim()}
                        title="Genera una imagen con IA a partir del contenido del post"
                        className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-purple-500/30 text-purple-300 bg-purple-500/10 hover:bg-purple-500/20 disabled:opacity-50 text-xs whitespace-nowrap transition-colors"
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
                        onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = "none"; }}
                        className="mt-2 max-h-40 rounded-lg border border-border object-cover"
                    />
                )}
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
                    <div className="space-y-1.5">
                        <input
                            type="datetime-local"
                            value={scheduleAt}
                            onChange={(e) => setScheduleAt(e.target.value)}
                            className="bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-pink-500/50"
                        />
                        <p className="text-[11px] text-amber-400/90">
                            ⚠️ La app debe permanecer abierta a la hora programada para que el post se publique.
                            Las imágenes generadas con IA caducan (~2h): para programar a futuro, usa una URL fija.
                        </p>
                    </div>
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
