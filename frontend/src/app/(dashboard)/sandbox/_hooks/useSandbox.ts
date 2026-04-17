"use client";

import { useEffect, useState, useCallback } from "react";
import { generativeUI } from "@/lib/api/generative_ui";
import type { GenerativeInterface } from "@/lib/api/generative_ui";

export function useSandbox() {
    const [prompt, setPrompt]                 = useState("");
    const [generating, setGenerating]         = useState(false);
    const [error, setError]                   = useState<string | null>(null);
    const [current, setCurrent]               = useState<GenerativeInterface | null>(null);
    const [history, setHistory]               = useState<GenerativeInterface[]>([]);
    const [loadingHistory, setLoadingHistory] = useState(true);
    const [toast, setToast]                   = useState<string | null>(null);

    const showToast = (msg: string) => { setToast(msg); setTimeout(() => setToast(null), 3000); };

    useEffect(() => {
        generativeUI.history().then(setHistory).catch(() => showToast("Error al cargar el historial")).finally(() => setLoadingHistory(false));
    }, []);

    const handleGenerate = async () => {
        if (!prompt.trim()) return;
        setGenerating(true); setError(null);
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), 180_000);
        try {
            const result = await generativeUI.generate(prompt.trim(), controller.signal);
            setCurrent(result); setHistory(prev => [result, ...prev]); setPrompt("");
        } catch (e: any) {
            if (e?.name === "AbortError") {
                setError("La generación tardó demasiado (>3 min). Intenta con un prompt más corto.");
            } else {
                const detail = e?.detail ?? e?.message ?? "Error al generar la interfaz";
                setError(e?.status ? `Error ${e.status}: ${detail}` : detail);
            }
        } finally { clearTimeout(timer); setGenerating(false); }
    };

    const handleRefresh = useCallback(async (followUpPrompt: string) => {
        if (!current) return;
        const result = await generativeUI.generate(followUpPrompt);
        setCurrent({ ...current, content_html: result.content_html });
        setHistory((prev) =>
            prev.map((h) => (h.id === current.id ? { ...h, content_html: result.content_html } : h))
        );
    }, [current]);

    const handleDelete = async (id: string) => {
        try {
            await generativeUI.delete(id);
            setHistory(prev => prev.filter(i => i.id !== id));
            if (current?.id === id) setCurrent(null);
            showToast("Eliminada");
        } catch { showToast("Error al eliminar"); }
    };

    return {
        prompt, setPrompt,
        generating, error,
        current, setCurrent,
        history,
        loadingHistory,
        toast,
        handleGenerate,
        handleRefresh,
        handleDelete,
    };
}
