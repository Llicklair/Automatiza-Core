"use client";

import { useState } from "react";
import { Download, Loader2, Archive } from "lucide-react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { verifactuConfig } from "@/lib/api/verifactuConfig";
import { useToastStore } from "@/stores/toast";

/** Exportación/volcado de los registros de facturación y eventos por periodo
 * (art. 8.2.c RD 1007/2023, anexo ap. 3). Registra el evento EXPORTACION. */
export function ExportPanel() {
    const t = useTranslations("configuracion");
    const toast = useToastStore();
    const hoy = new Date().toISOString().slice(0, 10);
    const inicioAno = `${new Date().getFullYear()}-01-01`;
    const [desde, setDesde] = useState(inicioAno);
    const [hasta, setHasta] = useState(hoy);
    const [busy, setBusy] = useState<"json" | "xml" | null>(null);

    const descargar = async (formato: "json" | "xml") => {
        if (!desde || !hasta) return;
        setBusy(formato);
        try {
            await verifactuConfig.descargarExport(desde, hasta, formato);
            toast.success(t("verifactu.export.ok"));
        } catch (e: any) {
            toast.error(e?.message || t("verifactu.export.error"));
        } finally {
            setBusy(null);
        }
    };

    return (
        <div className="bg-card border border-border rounded-2xl p-6 space-y-5">
            <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center shrink-0">
                    <Archive className="w-5 h-5 text-cyan-400" aria-hidden="true" />
                </div>
                <div>
                    <h2 className="text-sm font-semibold text-foreground">{t("verifactu.export.title")}</h2>
                    <p className="text-xs text-muted-foreground mt-1">{t("verifactu.export.subtitle")}</p>
                </div>
            </div>

            <div className="flex flex-wrap items-end gap-3">
                <div>
                    <label className="block text-xs font-medium text-muted-foreground mb-1.5">
                        {t("verifactu.export.from")}
                    </label>
                    <Input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} />
                </div>
                <div>
                    <label className="block text-xs font-medium text-muted-foreground mb-1.5">
                        {t("verifactu.export.to")}
                    </label>
                    <Input type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} />
                </div>
            </div>

            <div className="flex flex-wrap gap-2">
                <Button onClick={() => descargar("xml")} disabled={busy !== null}>
                    {busy === "xml" ? (
                        <Loader2 className="mr-2 w-4 h-4 animate-spin" aria-hidden="true" />
                    ) : (
                        <Download className="mr-2 w-4 h-4" aria-hidden="true" />
                    )}
                    {t("verifactu.export.downloadXml")}
                </Button>
                <Button variant="outline" onClick={() => descargar("json")} disabled={busy !== null}>
                    {busy === "json" ? (
                        <Loader2 className="mr-2 w-4 h-4 animate-spin" aria-hidden="true" />
                    ) : (
                        <Download className="mr-2 w-4 h-4" aria-hidden="true" />
                    )}
                    {t("verifactu.export.downloadJson")}
                </Button>
            </div>

            <p className="text-[11px] text-muted-foreground">{t("verifactu.export.hint")}</p>
        </div>
    );
}
