"use client";

import { useEffect, useState } from "react";
import { generativeUI } from "@/lib/api/generative_ui";
import type { GenerativeInterface } from "@/lib/api/generative_ui";
import GenerativeUI from "@/components/GenerativeUI";
import { Wand2, Trash2, Clock, Loader2, X, ChevronRight } from "lucide-react";

export default function SandboxPage() {
    const [prompt, setPrompt]               = useState("");
    const [generating, setGenerating]       = useState(false);
    const [error, setError]                 = useState<string | null>(null);
    const [current, setCurrent]             = useState<GenerativeInterface | null>(null);
    const [history, setHistory]             = useState<GenerativeInterface[]>([]);
    const [loadingHistory, setLoadingHistory] = useState(true);
    const [toast, setToast]                 = useState<string | null>(null);

    const showToast = (msg: string) => { setToast(msg); setTimeout(() => setToast(null), 3000); };

    useEffect(() => {
        generativeUI.history().then(setHistory).catch(() => {}).finally(() => setLoadingHistory(false));
    }, []);

    const handleGenerate = async () => {
        if (!prompt.trim()) return;
        setGenerating(true); setError(null);
        try {
            const result = await generativeUI.generate(prompt.trim());
            setCurrent(result); setHistory(prev => [result, ...prev]); setPrompt("");
        } catch (e: any) { setError(e?.message ?? "Error al generar la interfaz"); }
        finally { setGenerating(false); }
    };

    const handleDelete = async (id: string) => {
        try {
            await generativeUI.delete(id);
            setHistory(prev => prev.filter(i => i.id !== id));
            if (current?.id === id) setCurrent(null);
            showToast("Eliminada");
        } catch { showToast("Error al eliminar"); }
    };

    return (
        <div className="max-w-7xl mx-auto px-4 py-8 space-y-6">
            {toast && (
                <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 bg-zinc-900 border border-zinc-700 text-white text-sm px-5 py-2.5 rounded-full shadow-lg max-w-sm text-center">{toast}</div>
            )}

            <div>
                <h1 className="text-xl font-semibold text-white flex items-center gap-2">
                    <Wand2 className="w-6 h-6 text-violet-400" /> Sandbox Generativo
                </h1>
                <p className="text-xs text-zinc-500 mt-1">Describe con lenguaje natural la interfaz que necesitas y la IA la construirá al instante</p>
            </div>

            {/* Generador */}
            <div className="bg-[#18181b] border border-[#27272a] rounded-xl p-5 space-y-3">
                <label className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Describe la interfaz</label>
                <textarea value={prompt} onChange={e => setPrompt(e.target.value)}
                    onKeyDown={e => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleGenerate(); }}
                    placeholder="Ej: Crea un panel de resumen de facturación mensual con tabla de facturas pendientes…"
                    rows={3}
                    className="w-full bg-[#09090b] border border-[#27272a] rounded-lg px-3 py-2.5 text-sm text-white placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-violet-500/50 resize-none" />
                {error && <p className="text-xs text-red-400">{error}</p>}
                <div className="flex items-center justify-between">
                    <p className="text-xs text-zinc-600">Ctrl+Enter para generar</p>
                    <button onClick={handleGenerate} disabled={generating || !prompt.trim()}
                        className="flex items-center gap-2 px-4 py-2 bg-violet-600 hover:bg-violet-500 text-white rounded-lg text-sm font-medium disabled:opacity-50 transition-colors">
                        {generating && <Loader2 className="w-4 h-4 animate-spin" />}
                        {generating ? "Generando…" : "Generar interfaz"}
                    </button>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
                {/* Historial */}
                <div className="lg:col-span-1 space-y-2">
                    <p className="text-xs font-semibold text-zinc-600 uppercase tracking-wider">Historial ({history.length})</p>
                    {loadingHistory ? (
                        <div className="flex justify-center py-8"><Loader2 className="w-5 h-5 animate-spin text-zinc-600" /></div>
                    ) : history.length === 0 ? (
                        <div className="text-center py-8 border-2 border-dashed border-[#27272a] rounded-xl">
                            <p className="text-xs text-zinc-600">Sin interfaces generadas</p>
                        </div>
                    ) : history.map(item => (
                        <div key={item.id}
                            className={`group flex items-center gap-2 p-3 rounded-xl border cursor-pointer transition-colors ${
                                current?.id === item.id
                                    ? "bg-violet-600/10 border-violet-500/30"
                                    : "bg-[#18181b] border-[#27272a] hover:border-zinc-600"
                            }`}
                            onClick={() => setCurrent(item)}>
                            <div className="flex-1 min-w-0">
                                <p className="text-xs font-medium text-zinc-300 truncate">{item.title}</p>
                                <p className="text-[10px] text-zinc-600 flex items-center gap-1 mt-0.5">
                                    <Clock className="w-3 h-3" />
                                    {new Date(item.created_at).toLocaleDateString("es-ES", { day: "numeric", month: "short" })}
                                </p>
                            </div>
                            <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                                <button onClick={e => { e.stopPropagation(); handleDelete(item.id); }}
                                    className="p-1 rounded hover:bg-red-500/10 text-red-400 transition-colors">
                                    <Trash2 className="w-3 h-3" />
                                </button>
                                <ChevronRight className="w-3.5 h-3.5 text-zinc-600" />
                            </div>
                        </div>
                    ))}
                </div>

                {/* Preview */}
                <div className="lg:col-span-3">
                    {current ? (
                        <div className="bg-[#18181b] border border-[#27272a] rounded-xl overflow-hidden">
                            <div className="flex items-center justify-between px-5 py-3 border-b border-[#27272a]">
                                <div>
                                    <h3 className="text-sm font-semibold text-white">{current.title}</h3>
                                    {current.description && <p className="text-xs text-zinc-500 mt-0.5">{current.description}</p>}
                                </div>
                                <button onClick={() => setCurrent(null)} className="p-1 hover:bg-zinc-800 rounded-lg text-zinc-600">
                                    <X className="w-4 h-4" />
                                </button>
                            </div>
                            <div className="p-5">
                                <GenerativeUI html={current.content_html} className="min-h-32" />
                            </div>
                        </div>
                    ) : (
                        <div className="flex flex-col items-center justify-center h-64 border-2 border-dashed border-[#27272a] rounded-xl">
                            <Wand2 className="w-10 h-10 text-zinc-700 mb-3" />
                            <p className="text-zinc-500 font-medium text-sm">Sin interfaz activa</p>
                            <p className="text-xs text-zinc-600 mt-1">Genera una nueva o selecciona del historial</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
