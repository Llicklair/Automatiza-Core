"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
    KeyRound, ArrowLeft, Save, Loader2, Eye, EyeOff, CheckCircle2,
    ChevronDown, ChevronUp, Cpu, Layers,
} from "lucide-react";
import { api, LlmConfigResponse, LlmProviderConfigUpdate } from "@/lib/api";
import InfoBanner from "@/components/InfoBanner";
import { ExternalLink } from "lucide-react";

const LLM_PROVIDERS = [
    {
        key: "gemini", label: "Gemini", placeholder: "AIzaSy...",
        defaultModel: "gemini-2.5-flash",
        models: ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash", "gemini-1.5-pro"],
        consoleUrl: "https://aistudio.google.com/apikey",
        hint: "Gratuito con límites generosos. Recomendado para empezar.",
    },
    {
        key: "anthropic", label: "Anthropic", placeholder: "sk-ant-...",
        defaultModel: "claude-sonnet-4-6",
        models: ["claude-sonnet-4-6", "claude-opus-4-6", "claude-haiku-4-5-20251001"],
        consoleUrl: "https://console.anthropic.com/settings/keys",
        hint: "Modelos Claude. Alta calidad, de pago.",
    },
    {
        key: "groq", label: "Groq", placeholder: "gsk_...",
        defaultModel: "llama-3.3-70b-versatile",
        models: ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768", "gemma2-9b-it"],
        consoleUrl: "https://console.groq.com/keys",
        hint: "Inferencia ultra-rápida. Modelos open source gratuitos.",
    },
    {
        key: "openai", label: "OpenAI", placeholder: "sk-proj-...",
        defaultModel: "gpt-4o-mini",
        models: ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "o1-mini"],
        consoleUrl: "https://platform.openai.com/api-keys",
        hint: "GPT-4o y familia. De pago.",
    },
    {
        key: "openrouter", label: "OpenRouter", placeholder: "sk-or-...",
        defaultModel: "google/gemini-2.0-flash-exp:free",
        models: ["google/gemini-2.0-flash-exp:free", "google/gemma-3-27b-it:free", "mistralai/mistral-small-3.1-24b-instruct:free", "qwen/qwen3-235b-a22b-thinking-2507"],
        consoleUrl: "https://openrouter.ai/keys",
        hint: "Acceso a múltiples modelos con una sola key.",
    },
];

const EMBEDDINGS_OPTIONS = [
    { key: "local",   label: "Local (BAAI/bge-m3)",        desc: "Sin coste, offline, ~570 MB" },
    { key: "gemini",  label: "Gemini text-embedding-004",  desc: "Requiere Gemini API Key" },
    { key: "openai",  label: "OpenAI text-embedding-3-small", desc: "Requiere OpenAI API Key" },
];

type ProviderState = {
    api_key: string;
    model: string;
    enabled: boolean;
    has_key: boolean;
    showKey: boolean;
    expanded: boolean;
};

export default function ApiKeysPage() {
    const router = useRouter();
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [msg, setMsg] = useState("");
    const [activeLlm, setActiveLlm] = useState("gemini");
    const [activeEmbeddings, setActiveEmbeddings] = useState("local");
    const [providers, setProviders] = useState<Record<string, ProviderState>>({});

    useEffect(() => {
        api.tenant.getLlmConfig()
            .then((cfg: LlmConfigResponse) => {
                setActiveLlm(cfg.active_llm_provider);
                setActiveEmbeddings(cfg.active_embeddings_provider);
                const init: Record<string, ProviderState> = {};
                for (const p of LLM_PROVIDERS) {
                    const entry = cfg.providers[p.key] ?? { model: "", enabled: false, has_key: false };
                    init[p.key] = {
                        api_key: "",
                        model: entry.model || p.defaultModel,
                        enabled: entry.enabled,
                        has_key: entry.has_key,
                        showKey: false,
                        expanded: entry.enabled || entry.has_key,
                    };
                }
                setProviders(init);
            })
            .catch(() => {
                // Sin config guardada: inicializar vacío
                const init: Record<string, ProviderState> = {};
                for (const p of LLM_PROVIDERS) {
                    init[p.key] = { api_key: "", model: p.defaultModel, enabled: false, has_key: false, showKey: false, expanded: false };
                }
                setProviders(init);
            })
            .finally(() => setLoading(false));
    }, []);

    function updateProvider(key: string, patch: Partial<ProviderState>) {
        setProviders(prev => ({ ...prev, [key]: { ...prev[key], ...patch } }));
    }

    async function save() {
        setSaving(true);
        setMsg("");
        const providersPayload: Record<string, LlmProviderConfigUpdate> = {};
        for (const p of LLM_PROVIDERS) {
            const s = providers[p.key];
            if (!s) continue;
            providersPayload[p.key] = {
                enabled: s.enabled,
                model: s.model,
                ...(s.api_key ? { api_key: s.api_key } : {}),
            };
        }
        try {
            await api.tenant.updateLlmConfig({
                active_llm_provider: activeLlm,
                active_embeddings_provider: activeEmbeddings,
                providers: providersPayload,
            });
            setMsg("Configuración guardada");
            // Marcar has_key para los que tenían key nueva
            setProviders(prev => {
                const next = { ...prev };
                for (const p of LLM_PROVIDERS) {
                    if (prev[p.key]?.api_key) {
                        next[p.key] = { ...next[p.key], has_key: true, api_key: "" };
                    }
                }
                return next;
            });
        } catch {
            setMsg("Error al guardar");
        } finally {
            setSaving(false);
        }
    }

    if (loading) {
        return (
            <div className="p-8 flex items-center justify-center">
                <Loader2 className="w-6 h-6 animate-spin text-zinc-500" />
            </div>
        );
    }

    return (
        <div className="p-8 max-w-2xl mx-auto">
            <button
                onClick={() => router.back()}
                className="flex items-center gap-1.5 text-sm text-zinc-500 hover:text-white transition mb-6"
            >
                <ArrowLeft className="w-4 h-4" /> Volver
            </button>

            <InfoBanner id="api-keys-intro" title="¿Qué es una API Key?">
                <p>
                    Las API Keys permiten que los agentes IA se conecten a modelos de lenguaje.
                    Necesitas al menos una para que el sistema funcione.
                    <span className="text-indigo-300">Gemini es gratuito</span> y viene recomendado por defecto.
                </p>
            </InfoBanner>

            {/* LLM Providers */}
            <div className="bg-[#111113] border border-[#27272a] rounded-2xl p-6 mb-4">
                <h1 className="text-xl font-bold text-white flex items-center gap-2 mb-1">
                    <Cpu className="w-5 h-5 text-indigo-400" /> Modelos de lenguaje (LLM)
                </h1>
                <p className="text-xs text-zinc-500 mb-5">
                    Activa los proveedores que quieras usar. El <span className="text-indigo-400">proveedor activo</span> es el que usan los agentes.
                    Las claves se cifran en base de datos.
                </p>

                <div className="space-y-3">
                    {LLM_PROVIDERS.map(p => {
                        const s = providers[p.key];
                        if (!s) return null;
                        const isActive = activeLlm === p.key;

                        return (
                            <div
                                key={p.key}
                                className={`rounded-xl border transition-all ${
                                    isActive
                                        ? "border-indigo-500/50 bg-indigo-500/5"
                                        : s.enabled
                                        ? "border-emerald-500/30 bg-emerald-500/5"
                                        : "border-[#2e2e32] bg-[#18181b]"
                                }`}
                            >
                                {/* Header row */}
                                <div className="flex items-center gap-3 p-3">
                                    {/* Toggle enabled */}
                                    <button
                                        onClick={() => updateProvider(p.key, { enabled: !s.enabled })}
                                        className={`relative w-9 h-5 rounded-full transition-colors flex-shrink-0 ${
                                            s.enabled ? "bg-emerald-500" : "bg-zinc-700"
                                        }`}
                                    >
                                        <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-all ${s.enabled ? "left-4" : "left-0.5"}`} />
                                    </button>

                                    <span className={`text-sm font-medium flex-1 ${isActive ? "text-indigo-300" : s.enabled ? "text-white" : "text-zinc-500"}`}>
                                        {p.label}
                                        {s.has_key && !s.api_key && (
                                            <span className="ml-2 text-[10px] text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded-full">clave guardada</span>
                                        )}
                                    </span>

                                    {/* Botón "Usar como activo" */}
                                    {s.enabled && !isActive && (
                                        <button
                                            onClick={() => setActiveLlm(p.key)}
                                            className="text-[11px] px-2.5 py-1 rounded-lg border border-indigo-500/40 text-indigo-400 hover:bg-indigo-500/10 transition"
                                        >
                                            Usar como activo
                                        </button>
                                    )}
                                    {isActive && (
                                        <span className="text-[10px] font-bold uppercase tracking-wider bg-indigo-500 text-white px-2 py-0.5 rounded-full">
                                            Activo
                                        </span>
                                    )}

                                    {/* Expand */}
                                    <button
                                        onClick={() => updateProvider(p.key, { expanded: !s.expanded })}
                                        className="text-zinc-600 hover:text-zinc-400 transition ml-1"
                                    >
                                        {s.expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                                    </button>
                                </div>

                                {/* Expanded: api key + model */}
                                {s.expanded && (
                                    <div className="px-3 pb-3 space-y-2 border-t border-white/5 pt-3">
                                        <p className="text-[11px] text-zinc-500 mb-1">{p.hint}</p>
                                        <div>
                                            <div className="flex items-center justify-between mb-1">
                                                <label className="text-[11px] text-zinc-500">API Key</label>
                                                <a
                                                    href={p.consoleUrl}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className="text-[11px] text-indigo-400 hover:text-indigo-300 flex items-center gap-1 transition"
                                                >
                                                    Obtener API Key <ExternalLink className="w-3 h-3" />
                                                </a>
                                            </div>
                                            <div className="relative">
                                                <input
                                                    type={s.showKey ? "text" : "password"}
                                                    value={s.api_key}
                                                    onChange={e => updateProvider(p.key, { api_key: e.target.value })}
                                                    placeholder={s.has_key ? "••••••••  (dejar vacío para no cambiar)" : p.placeholder}
                                                    className="w-full pr-9 px-3 py-2 rounded-lg bg-black/40 border border-[#3f3f46] text-xs font-mono text-white placeholder-zinc-600 focus:outline-none focus:border-indigo-500/50 transition"
                                                />
                                                <button
                                                    type="button"
                                                    onClick={() => updateProvider(p.key, { showKey: !s.showKey })}
                                                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300"
                                                >
                                                    {s.showKey ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                                                </button>
                                            </div>
                                        </div>
                                        <div>
                                            <label className="text-[11px] text-zinc-500 mb-1 block">Modelo</label>
                                            <select
                                                value={p.models.includes(s.model) ? s.model : "__custom__"}
                                                onChange={e => {
                                                    if (e.target.value !== "__custom__") updateProvider(p.key, { model: e.target.value });
                                                }}
                                                className="w-full px-3 py-2 rounded-lg bg-black/40 border border-[#3f3f46] text-xs font-mono text-white focus:outline-none focus:border-indigo-500/50 transition mb-1"
                                            >
                                                {p.models.map(m => (
                                                    <option key={m} value={m} className="bg-[#18181b]">{m}</option>
                                                ))}
                                                {!p.models.includes(s.model) && (
                                                    <option value="__custom__" className="bg-[#18181b]">{s.model} (personalizado)</option>
                                                )}
                                            </select>
                                        </div>
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* Embeddings */}
            <div className="bg-[#111113] border border-[#27272a] rounded-2xl p-6 mb-4">
                <h2 className="text-base font-bold text-white flex items-center gap-2 mb-1">
                    <Layers className="w-4 h-4 text-purple-400" /> Embeddings (RAG / búsqueda semántica)
                </h2>
                <p className="text-xs text-zinc-500 mb-4">
                    Modelo vectorial para buscar en documentos. La opción local no requiere API key.
                </p>
                <div className="space-y-2">
                    {EMBEDDINGS_OPTIONS.map(opt => (
                        <button
                            key={opt.key}
                            onClick={() => setActiveEmbeddings(opt.key)}
                            className={`w-full flex items-center gap-3 p-3 rounded-xl border text-left transition ${
                                activeEmbeddings === opt.key
                                    ? "border-purple-500/50 bg-purple-500/5"
                                    : "border-[#2e2e32] bg-[#18181b] hover:border-zinc-600"
                            }`}
                        >
                            <span className={`w-3.5 h-3.5 rounded-full border-2 flex-shrink-0 ${
                                activeEmbeddings === opt.key ? "border-purple-400 bg-purple-400" : "border-zinc-600"
                            }`} />
                            <div>
                                <div className={`text-sm font-medium ${activeEmbeddings === opt.key ? "text-purple-300" : "text-zinc-300"}`}>
                                    {opt.label}
                                </div>
                                <div className="text-[11px] text-zinc-500">{opt.desc}</div>
                            </div>
                        </button>
                    ))}
                </div>
            </div>

            {/* Footer */}
            {msg && (
                <p className={`mb-3 text-xs flex items-center gap-1.5 ${msg.startsWith("Error") ? "text-red-400" : "text-emerald-400"}`}>
                    <CheckCircle2 className="w-3.5 h-3.5" /> {msg}
                </p>
            )}
            <div className="flex justify-end">
                <button
                    onClick={save}
                    disabled={saving}
                    className="flex items-center gap-1.5 px-5 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-medium transition"
                >
                    {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                    Guardar configuración
                </button>
            </div>
        </div>
    );
}
