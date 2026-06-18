"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, Newspaper, Loader2, RefreshCw, ExternalLink } from "lucide-react";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api";
import { surfaceIfConnectivity } from "@/lib/api/errors";

interface BoeItem {
    identificador?: string;
    titulo: string;
    descripcion?: string;
    url?: string;
    fecha?: string;
    relevante_pyme?: boolean;
    error?: string;
}

type Seccion = "fiscal" | "laboral" | "mercantil";

const SECCION_LABEL_KEYS: Record<Seccion, string> = {
    fiscal: "boe.seccionFiscal",
    laboral: "boe.seccionLaboral",
    mercantil: "boe.seccionMercantil",
};

export function BOETab() {
    const t = useTranslations("compliance");
    const [seccion, setSeccion] = useState<Seccion>("fiscal");
    const [items, setItems] = useState<BoeItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [soloPyme, setSoloPyme] = useState(false);

    async function fetchBOE(s: Seccion) {
        setLoading(true);
        setError(null);
        try {
            const data = (await api.advisory.boe(s, 15)) as BoeItem[];
            // El backend devuelve [{error, seccion}] si falla la descarga del RSS
            if (data.length === 1 && data[0].error) {
                setError(t("boe.boeNotResponding", { error: data[0].error! }));
                setItems([]);
            } else {
                setItems(data);
            }
        } catch (err: unknown) {
            if (surfaceIfConnectivity(err)) { setItems([]); return; }
            setError(err instanceof Error ? err.message : t("boe.unknownError"));
            setItems([]);
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        fetchBOE(seccion);
    }, [seccion]);

    const visibles = soloPyme ? items.filter(i => i.relevante_pyme) : items;
    const totalRelevantes = items.filter(i => i.relevante_pyme).length;

    return (
        <div className="space-y-6">
            {/* Controles */}
            <div className="flex flex-wrap items-center gap-3">
                <div className="flex gap-1 rounded-lg bg-muted border border-border p-1">
                    {(Object.keys(SECCION_LABEL_KEYS) as Seccion[]).map(s => (
                        <button
                            key={s}
                            onClick={() => setSeccion(s)}
                            className={`px-3 py-1.5 text-xs font-medium rounded-md transition ${
                                seccion === s
                                    ? "bg-card text-foreground shadow-sm"
                                    : "text-muted-foreground hover:text-foreground"
                            }`}
                        >
                            {t(SECCION_LABEL_KEYS[s])}
                        </button>
                    ))}
                </div>

                {totalRelevantes > 0 && (
                    <label className="flex items-center gap-2 text-xs text-muted-foreground cursor-pointer">
                        <input
                            type="checkbox"
                            checked={soloPyme}
                            onChange={e => setSoloPyme(e.target.checked)}
                            className="rounded border-border"
                        />
                        {t("boe.soloPyme", { count: totalRelevantes })}
                    </label>
                )}

                <button
                    onClick={() => fetchBOE(seccion)}
                    disabled={loading}
                    className="ml-auto flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground transition disabled:opacity-50"
                    title={t("boe.refresh")}
                >
                    <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
                    {t("boe.refresh")}
                </button>
            </div>

            {/* Resultado */}
            {loading ? (
                <div className="flex flex-col items-center justify-center py-16 gap-3 text-muted-foreground">
                    <Loader2 className="w-7 h-7 animate-spin text-primary" />
                    <p className="text-sm">{t("boe.loading")}</p>
                </div>
            ) : error ? (
                <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-5 space-y-3">
                    <p className="text-red-400 text-sm font-medium flex items-center gap-2">
                        <AlertTriangle className="w-4 h-4" /> {t("boe.errorTitle")}
                    </p>
                    <p className="text-muted-foreground text-sm">{error}</p>
                    <button
                        onClick={() => fetchBOE(seccion)}
                        className="text-xs text-primary hover:underline"
                    >
                        {t("boe.retry")}
                    </button>
                </div>
            ) : visibles.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 text-center text-muted-foreground">
                    <Newspaper className="w-10 h-10 mb-3" />
                    <p className="text-sm">
                        {soloPyme
                            ? t("boe.emptyPyme")
                            : t("boe.empty")}
                    </p>
                </div>
            ) : (
                <ul className="space-y-3">
                    {visibles.map((item, i) => (
                        <li
                            key={item.identificador || i}
                            className={`rounded-xl border p-4 transition ${
                                item.relevante_pyme
                                    ? "border-primary/30 bg-primary/5"
                                    : "border-border bg-card"
                            }`}
                        >
                            <div className="flex items-start justify-between gap-3 mb-2">
                                <div className="flex-1 min-w-0">
                                    <a
                                        href={item.url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="text-sm font-medium text-foreground hover:text-primary hover:underline flex items-start gap-2 group"
                                    >
                                        <span>{item.titulo}</span>
                                        <ExternalLink className="w-3.5 h-3.5 text-muted-foreground group-hover:text-primary shrink-0 mt-0.5" />
                                    </a>
                                </div>
                                {item.relevante_pyme && (
                                    <span className="shrink-0 text-[10px] uppercase tracking-wide font-bold text-primary bg-primary/15 px-2 py-0.5 rounded">
                                        {t("boe.relevantePyme")}
                                    </span>
                                )}
                            </div>
                            {item.descripcion && (
                                <p className="text-xs text-muted-foreground line-clamp-2 mb-2">
                                    {item.descripcion}
                                </p>
                            )}
                            <div className="flex flex-wrap gap-3 text-[10px] text-muted-foreground">
                                {item.identificador && (
                                    <span className="font-mono">{item.identificador}</span>
                                )}
                                {item.fecha && <span>{item.fecha}</span>}
                            </div>
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
}
