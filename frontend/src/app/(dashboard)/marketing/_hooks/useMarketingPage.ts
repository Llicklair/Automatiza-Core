"use client";

import { useState } from "react";
import { api } from "@/lib/api";

export type Post = {
    day: string;
    platform: string;
    product: string | null;
    text: string;
    hashtags: string[];
    best_time: string;
    image_idea: string;
};

export type MarketingPlan = {
    period: string;
    focus: string;
    posts: Post[];
};

export const PLATFORM_COLORS: Record<string, string> = {
    Instagram: "bg-pink-500/10 text-pink-400 border-pink-500/20",
    Facebook: "bg-blue-500/10 text-blue-400 border-blue-500/20",
    LinkedIn: "bg-sky-500/10 text-sky-400 border-sky-500/20",
};

export function useMarketingPage() {
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
            const taskId = res.id;
            let attempts = 0;
            while (attempts < 60) {
                await new Promise((r) => setTimeout(r, 3000));
                const task = await api.tasks.get(taskId);
                if (task.status === "done" || task.status === "completed") {
                    const result =
                        task.output_data ??
                        task.agent_results?.[0]?.output?.response ??
                        task.agent_results?.[0]?.result;
                    if (result) {
                        try {
                            const parsed = typeof result === "string" ? JSON.parse(result) : result;
                            setPlan(parsed);
                        } catch {
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

    return { plan, loading, error, prompt, setPrompt, generatePlan };
}
