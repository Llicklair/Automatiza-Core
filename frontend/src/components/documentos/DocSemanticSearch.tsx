"use client";

import { useState } from "react";
import { Search, Loader2, FileText } from "lucide-react";
import { documents, type SemanticHit } from "@/lib/api/documents";
import { logError } from "@/lib/logger";

/**
 * Búsqueda semántica (RAG) sobre los documentos del tenant: devuelve los
 * fragmentos más relevantes con su similitud. Complementa a RagChatBox (chat
 * conversacional) con una búsqueda directa y rankeada, sin síntesis LLM.
 */
export default function DocSemanticSearch() {
    const [q, setQ] = useState("");
    const [hits, setHits] = useState<SemanticHit[] | null>(null);
    const [loading, setLoading] = useState(false);

    const run = async () => {
        const query = q.trim();
        if (!query) return;
        setLoading(true);
        try {
            setHits(await documents.search(query, 8));
        } catch (err) {
            logError("documentos/search", err);
            setHits([]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="bg-card border border-border rounded-2xl p-4 space-y-3">
            <div className="flex items-center gap-2">
                <Search className="w-4 h-4 text-muted-foreground shrink-0" />
                <input
                    value={q}
                    onChange={(e) => setQ(e.target.value)}
                    onKeyDown={(e) => { if (e.key === "Enter") run(); }}
                    placeholder="Buscar en tus documentos por significado (ej. cláusula de penalización)"
                    className="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground focus:outline-none"
                />
                <button
                    onClick={run}
                    disabled={loading || !q.trim()}
                    className="inline-flex items-center gap-1.5 bg-primary hover:bg-primary disabled:opacity-50 disabled:cursor-not-allowed text-foreground text-sm px-3 py-1.5 rounded-lg font-medium"
                >
                    {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Search className="w-3.5 h-3.5" />}
                    Buscar
                </button>
            </div>

            {hits !== null && !loading && (
                hits.length === 0 ? (
                    <p className="text-xs text-muted-foreground px-1">Sin resultados relevantes.</p>
                ) : (
                    <ul className="space-y-2">
                        {hits.map((h, i) => (
                            <li
                                key={`${h.document_id}-${h.chunk_index}-${i}`}
                                className="rounded-lg border border-border/60 bg-background/40 p-3"
                            >
                                <div className="flex items-center justify-between gap-2 mb-1">
                                    <span className="flex items-center gap-1.5 text-xs font-medium text-foreground truncate">
                                        <FileText className="w-3.5 h-3.5 text-primary shrink-0" />
                                        {h.file_name ?? "Documento"}
                                        {h.page_number != null && (
                                            <span className="text-muted-foreground">· p.{h.page_number}</span>
                                        )}
                                    </span>
                                    <span className="text-[10px] text-muted-foreground shrink-0">
                                        {Math.round(h.similarity * 100)}%
                                    </span>
                                </div>
                                <p className="text-xs text-muted-foreground line-clamp-3">{h.text}</p>
                            </li>
                        ))}
                    </ul>
                )
            )}
        </div>
    );
}
