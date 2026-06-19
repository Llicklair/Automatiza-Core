"use client";

import { useEffect, useState } from "react";
import { api, LlmConfigResponse, LlmProviderConfigUpdate } from "@/lib/api";

export const LLM_PROVIDERS = [
    {
        key: "anthropic", label: "Anthropic", placeholder: "sk-ant-...",
        defaultModel: "claude-sonnet-4-6",
        models: ["claude-sonnet-4-6", "claude-opus-4-6", "claude-haiku-4-5-20251001"],
        consoleUrl: "https://console.anthropic.com/settings/keys",
        hintKey: "apiKeys.hintAnthropic",
    },
    {
        key: "groq", label: "Groq", placeholder: "gsk_...",
        defaultModel: "llama-3.3-70b-versatile",
        models: ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768", "gemma2-9b-it"],
        consoleUrl: "https://console.groq.com/keys",
        hintKey: "apiKeys.hintGroq",
    },
    {
        key: "openai", label: "OpenAI", placeholder: "sk-proj-...",
        defaultModel: "gpt-4o-mini",
        models: ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "o1-mini"],
        consoleUrl: "https://platform.openai.com/api-keys",
        hintKey: "apiKeys.hintOpenai",
    },
    {
        key: "openrouter", label: "OpenRouter", placeholder: "sk-or-...",
        defaultModel: "anthropic/claude-sonnet-4-6",
        models: ["anthropic/claude-sonnet-4-6", "google/gemma-3-27b-it:free", "mistralai/mistral-small-3.1-24b-instruct:free", "qwen/qwen3-235b-a22b-thinking-2507"],
        consoleUrl: "https://openrouter.ai/keys",
        hintKey: "apiKeys.hintOpenrouter",
    },
];

export const EMBEDDINGS_OPTIONS = [
    { key: "local",   labelKey: "apiKeys.embeddingsLocalLabel",  descKey: "apiKeys.embeddingsLocalDesc" },
    { key: "openai",  labelKey: "apiKeys.embeddingsOpenaiLabel", descKey: "apiKeys.embeddingsOpenaiDesc" },
];

export type ProviderState = {
    api_key: string;
    model: string;
    enabled: boolean;
    has_key: boolean;
    showKey: boolean;
    expanded: boolean;
};

export type ClaudeSetupState = {
    phase: "idle" | "checking" | "ready" | "needs_auth" | "error";
    version?: string;
    message?: string;
};

export function useApiKeys() {
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [saveStatus, setSaveStatus] = useState<"" | "ok" | "error">("");
    const [activeLlm, setActiveLlm] = useState("claude_code");
    const [activeEmbeddings, setActiveEmbeddings] = useState("local");
    const [providers, setProviders] = useState<Record<string, ProviderState>>({});
    const [claudeSetup, setClaudeSetup] = useState<ClaudeSetupState>({ phase: "idle" });

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
                const init: Record<string, ProviderState> = {};
                for (const p of LLM_PROVIDERS) {
                    init[p.key] = { api_key: "", model: p.defaultModel, enabled: false, has_key: false, showKey: false, expanded: false };
                }
                setProviders(init);
            })
            .finally(() => setLoading(false));

        api.tenant.setupClaudeCode()
            .then(res => {
                if (res.status === "ready") setClaudeSetup({ phase: "ready", version: res.version, message: res.message });
                else if (res.status === "needs_auth") setClaudeSetup({ phase: "needs_auth", version: res.version, message: res.message });
            })
            .catch(() => {});
    }, []);

    function updateProvider(key: string, patch: Partial<ProviderState>) {
        setProviders(prev => ({ ...prev, [key]: { ...prev[key], ...patch } }));
    }

    async function save() {
        setSaving(true);
        setSaveStatus("");
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
            setSaveStatus("ok");
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
            setSaveStatus("error");
        } finally {
            setSaving(false);
        }
    }

    return {
        loading, saving, saveStatus, save,
        activeLlm, setActiveLlm,
        activeEmbeddings, setActiveEmbeddings,
        providers, updateProvider,
        claudeSetup, setClaudeSetup,
    };
}
