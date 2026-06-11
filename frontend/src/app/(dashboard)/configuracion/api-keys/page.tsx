"use client";

import { useRouter } from "next/navigation";
import { ArrowLeft, CheckCircle2, Loader2, Save } from "lucide-react";
import InfoBanner from "@/components/InfoBanner";
import { useApiKeys } from "./_hooks/useApiKeys";
import { LlmProvidersCard } from "./_components/LlmProvidersCard";
import { EmbeddingsCard } from "./_components/EmbeddingsCard";
import { ClaudeCodeCard } from "./_components/ClaudeCodeCard";
import { UsageStatsCard } from "./_components/UsageStatsCard";
import { PageContainer } from "@/components/shared/PageContainer";

export default function ApiKeysPage() {
    const router = useRouter();
    const {
        loading, saving, msg, save,
        activeLlm, setActiveLlm,
        activeEmbeddings, setActiveEmbeddings,
        providers, updateProvider,
        claudeSetup, setClaudeSetup,
    } = useApiKeys();

    if (loading) {
        return (
            <div className="p-8 flex items-center justify-center">
                <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
            </div>
        );
    }

    return (
        <PageContainer width="full" className="max-w-2xl mx-auto">
            <button
                onClick={() => router.back()}
                className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition mb-6"
            >
                <ArrowLeft className="w-4 h-4" /> Volver
            </button>

            <InfoBanner id="api-keys-intro" title="¿Qué es una API Key?">
                <p>
                    Las API Keys permiten que los agentes IA se conecten a modelos de lenguaje.
                    Necesitas al menos una para que el sistema funcione.
                    <span className="text-primary">Claude Code</span> es el proveedor recomendado por defecto.
                </p>
            </InfoBanner>

            <LlmProvidersCard
                providers={providers}
                activeLlm={activeLlm}
                setActiveLlm={setActiveLlm}
                updateProvider={updateProvider}
            />

            <EmbeddingsCard
                activeEmbeddings={activeEmbeddings}
                setActiveEmbeddings={setActiveEmbeddings}
            />

            <ClaudeCodeCard
                claudeSetup={claudeSetup}
                setClaudeSetup={setClaudeSetup}
                updateProvider={updateProvider}
            />

            <UsageStatsCard />

            {msg && (
                <p className={`mb-3 text-xs flex items-center gap-1.5 ${msg.startsWith("Error") ? "text-red-400" : "text-emerald-400"}`}>
                    <CheckCircle2 className="w-3.5 h-3.5" /> {msg}
                </p>
            )}
            <div className="flex justify-end">
                <button
                    onClick={save}
                    disabled={saving}
                    className="flex items-center gap-1.5 px-5 py-2.5 rounded-lg bg-primary hover:bg-primary disabled:opacity-50 text-foreground text-sm font-medium transition"
                >
                    {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                    Guardar configuración
                </button>
            </div>
        </PageContainer>
    );
}
