/**
 * PRES.ASS — UI presentación asistida para Modelos 131 y 200.
 *
 * Flow: usuario descarga XML pre-rellenado → abre Sede AEAT en otra
 * pestaña → importa el XML como "Predeclaración" → completa los datos
 * que falten → presenta él mismo.
 *
 * No automatizamos estos modelos porque su complejidad (módulos
 * IRPF en el 131, ajustes fiscales del Impuesto Sociedades en el 200)
 * supera el alcance del MVP y requiere asesoramiento profesional caso
 * a caso.
 */
"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Download, ExternalLink, FileText, Info, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import type { ModeloAsistido } from "@/lib/api/presentacion";
import { useToastStore } from "@/stores/toast";
import { PageHeader } from "@/components/shared/PageHeader";

type ModeloAsistidoMeta = {
    key: ModeloAsistido;
    titulo: string;
    subtitulo: string;
    descripcion: string;
    requiereTrimestre: boolean;
};

const buildModelos = (t: ReturnType<typeof useTranslations>): ModeloAsistidoMeta[] => [
    {
        key: "131",
        titulo: t("asistida.modelo131Titulo"),
        subtitulo: t("asistida.modelo131Subtitulo"),
        descripcion: t("asistida.modelo131Descripcion"),
        requiereTrimestre: true,
    },
    {
        key: "200",
        titulo: t("asistida.modelo200Titulo"),
        subtitulo: t("asistida.modelo200Subtitulo"),
        descripcion: t("asistida.modelo200Descripcion"),
        requiereTrimestre: false,
    },
];

const CURRENT_YEAR = new Date().getFullYear();

export function AsistidaPanel() {
    const t = useTranslations("impuestos");
    const MODELOS = buildModelos(t);
    const toast = useToastStore();
    const [ejercicio, setEjercicio] = useState(CURRENT_YEAR);
    const [trimestre, setTrimestre] = useState(1);
    const [busy, setBusy] = useState<ModeloAsistido | null>(null);

    async function downloadAndOpen(modelo: ModeloAsistido) {
        setBusy(modelo);
        try {
            await api.presentacion.downloadXml(modelo, {
                ejercicio,
                trimestre: modelo === "131" ? trimestre : undefined,
            });
            const info = await api.presentacion.info(modelo);
            toast.show(
                t("asistida.xmlDownloaded"),
                "success",
            );
            // Pequeño delay para que el download inicie antes de abrir tab.
            setTimeout(() => {
                window.open(info.sede_url, "_blank", "noopener,noreferrer");
            }, 400);
        } catch (e: any) {
            toast.show(t("asistida.downloadError", { message: e.message }), "error");
        } finally {
            setBusy(null);
        }
    }

    return (
        <div className="space-y-6">
            <PageHeader
                title={t("asistida.title")}
                description={t("asistida.description")}
            />

            <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-4 flex items-start gap-3">
                <Info className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" aria-hidden="true" />
                <div className="text-xs text-muted-foreground leading-relaxed">
                    <p>
                        <strong className="text-foreground">{t("asistida.modalidadStrong")}</strong>{t("asistida.modalidadRest")}
                    </p>
                    <ul className="mt-2 list-disc list-inside space-y-1">
                        <li>{t("asistida.nota131")}</li>
                        <li>{t("asistida.nota200")}</li>
                    </ul>
                </div>
            </div>

            {/* Selector de período */}
            <section
                aria-labelledby="periodo-heading"
                className="rounded-lg border border-border bg-card p-4 space-y-3"
            >
                <h2 id="periodo-heading" className="text-sm font-medium text-foreground">
                    {t("asistida.periodoFiscal")}
                </h2>
                <div className="flex flex-wrap items-center gap-3">
                    <label className="text-xs text-muted-foreground flex items-center gap-2">
                        {t("asistida.ejercicio")}
                        <input
                            type="number"
                            min={2020}
                            max={2099}
                            value={ejercicio}
                            onChange={(e) => setEjercicio(Number(e.target.value))}
                            className="w-24 px-2 py-1 rounded-md bg-background border border-border text-foreground text-sm"
                        />
                    </label>
                    <label className="text-xs text-muted-foreground flex items-center gap-2">
                        {t("asistida.trimestreSolo131")}
                        <select
                            value={trimestre}
                            onChange={(e) => setTrimestre(Number(e.target.value))}
                            className="px-2 py-1 rounded-md bg-background border border-border text-foreground text-sm"
                        >
                            <option value={1}>1T</option>
                            <option value={2}>2T</option>
                            <option value={3}>3T</option>
                            <option value={4}>4T</option>
                        </select>
                    </label>
                </div>
            </section>

            {/* Tarjetas por modelo */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {MODELOS.map((m) => {
                    const isBusy = busy === m.key;
                    return (
                        <article
                            key={m.key}
                            className="rounded-lg border border-border bg-card p-5 flex flex-col"
                        >
                            <header className="flex items-start gap-2.5 mb-3">
                                <FileText className="w-5 h-5 text-primary flex-shrink-0 mt-0.5" aria-hidden="true" />
                                <div className="min-w-0">
                                    <h3 className="text-base font-semibold text-foreground">{m.titulo}</h3>
                                    <p className="text-xs text-muted-foreground">{m.subtitulo}</p>
                                </div>
                            </header>
                            <p className="text-sm text-muted-foreground leading-relaxed flex-1 mb-4">
                                {m.descripcion}
                            </p>
                            <button
                                type="button"
                                onClick={() => downloadAndOpen(m.key)}
                                disabled={isBusy}
                                className="w-full inline-flex items-center justify-center gap-2 px-4 py-2 rounded-md bg-primary text-foreground text-sm font-medium hover:bg-primary/90 disabled:opacity-50"
                            >
                                {isBusy ? (
                                    <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
                                ) : (
                                    <Download className="w-4 h-4" aria-hidden="true" />
                                )}
                                {t("asistida.descargarXmlSede")}
                                <ExternalLink className="w-3 h-3 opacity-70" aria-hidden="true" />
                            </button>
                        </article>
                    );
                })}
            </div>

            <aside className="text-xs text-muted-foreground space-y-1">
                <p>
                    <strong className="text-foreground">{t("asistida.comoSeUsa")}</strong>
                </p>
                <ol className="list-decimal list-inside space-y-1">
                    <li>{t("asistida.paso1")}</li>
                    <li>{t("asistida.paso2")}</li>
                    <li>{t("asistida.paso3")}</li>
                    <li>{t("asistida.paso4")}</li>
                </ol>
            </aside>
        </div>
    );
}
