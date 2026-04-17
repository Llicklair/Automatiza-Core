"use client";

import { Megaphone, Loader2, Calendar, Clock, Hash, ImageIcon, Send } from "lucide-react";
import { useMarketingPage, PLATFORM_COLORS } from "./_hooks/useMarketingPage";

export default function MarketingPage() {
    const { plan, loading, error, prompt, setPrompt, generatePlan } = useMarketingPage();

    return (
        <div className="p-6 max-w-5xl mx-auto space-y-6">
            <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-pink-500/10 border border-pink-500/20">
                    <Megaphone className="w-5 h-5 text-pink-400" />
                </div>
                <div>
                    <h1 className="text-lg font-semibold text-foreground">Marketing &amp; Redes Sociales</h1>
                    <p className="text-xs text-muted-foreground">Genera planes de contenidos con IA basados en tu catálogo</p>
                </div>
            </div>

            <div className="bg-card border border-border rounded-xl p-4 space-y-3">
                <label className="text-xs font-medium text-muted-foreground">Instrucciones (opcional)</label>
                <div className="flex gap-2">
                    <input
                        type="text"
                        value={prompt}
                        onChange={(e) => setPrompt(e.target.value)}
                        placeholder="Ej: Plan semanal enfocado en el lanzamiento del producto X..."
                        className="flex-1 bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-pink-500/50"
                        onKeyDown={(e) => e.key === "Enter" && !loading && generatePlan()}
                    />
                    <button
                        onClick={generatePlan}
                        disabled={loading}
                        className="flex items-center gap-2 px-4 py-2 rounded-lg bg-pink-600 hover:bg-pink-500 disabled:opacity-50 text-foreground text-sm font-medium transition-colors"
                    >
                        {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                        {loading ? "Generando..." : "Generar plan"}
                    </button>
                </div>
            </div>

            {error && !plan && (
                <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 text-sm text-red-300">
                    {error}
                </div>
            )}

            {plan && (
                <div className="bg-card border border-border rounded-xl p-4">
                    <div className="flex items-center gap-3 mb-1">
                        <Calendar className="w-4 h-4 text-pink-400" />
                        <span className="text-sm font-medium text-foreground">{plan.period}</span>
                    </div>
                    {plan.focus && (
                        <p className="text-xs text-muted-foreground ml-7">{plan.focus}</p>
                    )}
                </div>
            )}

            {plan && plan.posts.length > 0 && (
                <div className="grid gap-3">
                    {plan.posts.map((post, i) => (
                        <div key={i} className="bg-card border border-border rounded-xl p-4 space-y-3">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <span className="text-xs font-medium text-foreground">{post.day}</span>
                                    <span className={`text-[10px] px-2 py-0.5 rounded-full border font-medium ${PLATFORM_COLORS[post.platform] || "bg-muted text-muted-foreground border-border"}`}>
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

            {plan && plan.posts.length === 0 && error && (
                <div className="bg-card border border-border rounded-xl p-4">
                    <pre className="text-xs text-muted-foreground whitespace-pre-wrap">{error}</pre>
                </div>
            )}

            {!plan && !loading && !error && (
                <div className="flex flex-col items-center justify-center py-16 text-center">
                    <div className="p-4 rounded-2xl bg-pink-500/5 border border-pink-500/10 mb-4">
                        <Megaphone className="w-8 h-8 text-pink-500/40" />
                    </div>
                    <p className="text-sm text-muted-foreground mb-1">Sin planes de marketing generados</p>
                    <p className="text-xs text-muted-foreground">Pulsa «Generar plan» para que la IA analice tu catálogo y cree contenidos</p>
                </div>
            )}
        </div>
    );
}
