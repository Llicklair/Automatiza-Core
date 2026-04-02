"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { Megaphone, Loader2, Calendar, Clock, Hash, ImageIcon, Send } from "lucide-react";

type Post = {
    day: string;
    platform: string;
    product: string | null;
    text: string;
    hashtags: string[];
    best_time: string;
    image_idea: string;
};

type MarketingPlan = {
    period: string;
    focus: string;
    posts: Post[];
};

const PLATFORM_COLORS: Record<string, string> = {
    Instagram: "bg-pink-500/10 text-pink-400 border-pink-500/20",
    Facebook: "bg-blue-500/10 text-blue-400 border-blue-500/20",
    LinkedIn: "bg-sky-500/10 text-sky-400 border-sky-500/20",
};

export default function MarketingPage() {
    const [plan, setPlan] = useState<MarketingPlan | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [prompt, setPrompt] = useState("");

    const generatePlan = async () => {
        setLoading(true);
        setError(null);
        setPlan(null);
        try {
            const intent = prompt.trim() || "Genera un plan de contenidos para redes sociales este mes";
            const res = await api.tasks.create("marketing", intent);
            // Poll task until done
            const taskId = res.id;
            let attempts = 0;
            while (attempts < 60) {
                await new Promise((r) => setTimeout(r, 3000));
                const task = await api.tasks.get(taskId);
                if (task.status === "done" || task.status === "completed") {
                    // Extract marketing plan from agent_results
                    const result =
                        task.output_data ??
                        task.agent_results?.[0]?.output?.response ??
                        task.agent_results?.[0]?.result;
                    if (result) {
                        try {
                            const parsed = typeof result === "string" ? JSON.parse(result) : result;
                            setPlan(parsed);
                        } catch {
                            // If not valid JSON, show as raw text
                            setPlan({ period: "Plan generado", focus: "", posts: [] });
                            setError(typeof result === "string" ? result : JSON.stringify(result, null, 2));
                        }
                    }
                    break;
                }
                if (task.status === "failed") {
                    setError(task.error_message || "Error generando el plan de marketing.");
                    break;
                }
                attempts++;
            }
            if (attempts >= 60) setError("Timeout: la tarea tardó demasiado.");
        } catch (e: any) {
            setError(e?.message || "Error al crear la tarea de marketing.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="p-6 max-w-5xl mx-auto space-y-6">
            {/* Header */}
            <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-pink-500/10 border border-pink-500/20">
                    <Megaphone className="w-5 h-5 text-pink-400" />
                </div>
                <div>
                    <h1 className="text-lg font-semibold text-white">Marketing &amp; Redes Sociales</h1>
                    <p className="text-xs text-zinc-500">Genera planes de contenidos con IA basados en tu catálogo</p>
                </div>
            </div>

            {/* Prompt */}
            <div className="bg-[#18181b] border border-[#27272a] rounded-xl p-4 space-y-3">
                <label className="text-xs font-medium text-zinc-400">Instrucciones (opcional)</label>
                <div className="flex gap-2">
                    <input
                        type="text"
                        value={prompt}
                        onChange={(e) => setPrompt(e.target.value)}
                        placeholder="Ej: Plan semanal enfocado en el lanzamiento del producto X..."
                        className="flex-1 bg-[#09090b] border border-[#27272a] rounded-lg px-3 py-2 text-sm text-white placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-pink-500/50"
                        onKeyDown={(e) => e.key === "Enter" && !loading && generatePlan()}
                    />
                    <button
                        onClick={generatePlan}
                        disabled={loading}
                        className="flex items-center gap-2 px-4 py-2 rounded-lg bg-pink-600 hover:bg-pink-500 disabled:opacity-50 text-white text-sm font-medium transition-colors"
                    >
                        {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                        {loading ? "Generando..." : "Generar plan"}
                    </button>
                </div>
            </div>

            {/* Error */}
            {error && !plan && (
                <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 text-sm text-red-300">
                    {error}
                </div>
            )}

            {/* Plan header */}
            {plan && (
                <div className="bg-[#18181b] border border-[#27272a] rounded-xl p-4">
                    <div className="flex items-center gap-3 mb-1">
                        <Calendar className="w-4 h-4 text-pink-400" />
                        <span className="text-sm font-medium text-white">{plan.period}</span>
                    </div>
                    {plan.focus && (
                        <p className="text-xs text-zinc-500 ml-7">{plan.focus}</p>
                    )}
                </div>
            )}

            {/* Posts grid */}
            {plan && plan.posts.length > 0 && (
                <div className="grid gap-3">
                    {plan.posts.map((post, i) => (
                        <div key={i} className="bg-[#18181b] border border-[#27272a] rounded-xl p-4 space-y-3">
                            {/* Header row */}
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <span className="text-xs font-medium text-zinc-300">{post.day}</span>
                                    <span className={`text-[10px] px-2 py-0.5 rounded-full border font-medium ${PLATFORM_COLORS[post.platform] || "bg-zinc-800 text-zinc-400 border-zinc-700"}`}>
                                        {post.platform}
                                    </span>
                                    {post.product && (
                                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20">
                                            {post.product}
                                        </span>
                                    )}
                                </div>
                                <div className="flex items-center gap-1 text-zinc-500">
                                    <Clock className="w-3 h-3" />
                                    <span className="text-[10px]">{post.best_time}</span>
                                </div>
                            </div>

                            {/* Post text */}
                            <p className="text-sm text-zinc-300 leading-relaxed whitespace-pre-wrap">{post.text}</p>

                            {/* Hashtags */}
                            {post.hashtags?.length > 0 && (
                                <div className="flex items-center gap-1.5 flex-wrap">
                                    <Hash className="w-3 h-3 text-zinc-600" />
                                    {post.hashtags.map((tag, j) => (
                                        <span key={j} className="text-[10px] text-pink-400/80">{tag}</span>
                                    ))}
                                </div>
                            )}

                            {/* Image idea */}
                            {post.image_idea && (
                                <div className="flex items-start gap-2 bg-[#09090b] rounded-lg p-2.5">
                                    <ImageIcon className="w-3.5 h-3.5 text-zinc-600 mt-0.5 flex-shrink-0" />
                                    <span className="text-[11px] text-zinc-500">{post.image_idea}</span>
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}

            {/* Raw response fallback */}
            {plan && plan.posts.length === 0 && error && (
                <div className="bg-[#18181b] border border-[#27272a] rounded-xl p-4">
                    <pre className="text-xs text-zinc-400 whitespace-pre-wrap">{error}</pre>
                </div>
            )}

            {/* Empty state */}
            {!plan && !loading && !error && (
                <div className="flex flex-col items-center justify-center py-16 text-center">
                    <div className="p-4 rounded-2xl bg-pink-500/5 border border-pink-500/10 mb-4">
                        <Megaphone className="w-8 h-8 text-pink-500/40" />
                    </div>
                    <p className="text-sm text-zinc-500 mb-1">Sin planes de marketing generados</p>
                    <p className="text-xs text-zinc-600">Pulsa «Generar plan» para que la IA analice tu catálogo y cree contenidos</p>
                </div>
            )}
        </div>
    );
}
