import { Layers } from "lucide-react";
import { EMBEDDINGS_OPTIONS } from "../_hooks/useApiKeys";

interface EmbeddingsCardProps {
    activeEmbeddings: string;
    setActiveEmbeddings: (v: string) => void;
}

export function EmbeddingsCard({ activeEmbeddings, setActiveEmbeddings }: EmbeddingsCardProps) {
    return (
        <div className="bg-card border border-border rounded-2xl p-6 mb-4">
            <h2 className="text-base font-bold text-foreground flex items-center gap-2 mb-1">
                <Layers className="w-4 h-4 text-purple-400" /> Embeddings (RAG / búsqueda semántica)
            </h2>
            <p className="text-xs text-muted-foreground mb-4">
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
                                : "border-border bg-card hover:border-border"
                        }`}
                    >
                        <span className={`w-3.5 h-3.5 rounded-full border-2 flex-shrink-0 ${
                            activeEmbeddings === opt.key ? "border-purple-400 bg-purple-400" : "border-border"
                        }`} />
                        <div>
                            <div className={`text-sm font-medium ${activeEmbeddings === opt.key ? "text-purple-300" : "text-foreground"}`}>
                                {opt.label}
                            </div>
                            <div className="text-[11px] text-muted-foreground">{opt.desc}</div>
                        </div>
                    </button>
                ))}
            </div>
        </div>
    );
}
