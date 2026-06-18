"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api";
import { useToastStore } from "@/stores/toast";
import { FileText, Loader2, Download } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function LibroRegistroExport() {
    const t = useTranslations("impuestos");
    const show = useToastStore((s) => s.show);
    const yearNow = new Date().getFullYear();
    const [year, setYear] = useState(yearNow);
    const [busy, setBusy] = useState<"emitidas" | "recibidas" | null>(null);

    const download = async (type: "emitidas" | "recibidas") => {
        setBusy(type);
        try {
            await api.reports.libroRegistro(year, type);
            const typeLabel = type === "emitidas" ? t("libroRegistro.emitidas") : t("libroRegistro.recibidas");
            show(t("libroRegistro.downloaded", { type: typeLabel, year }), "success");
        } catch (e: unknown) {
            const msg = e instanceof Error ? e.message : t("libroRegistro.downloadError");
            show(msg, "error");
        } finally {
            setBusy(null);
        }
    };

    return (
        <Card>
            <CardContent className="p-5">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                    <div>
                        <h2 className="text-sm font-semibold text-foreground flex items-center gap-2">
                            <FileText className="w-4 h-4 text-emerald-400" />
                            {t("libroRegistro.title")}
                        </h2>
                        <p className="text-xs text-muted-foreground mt-1 max-w-xl">
                            {t("libroRegistro.description")}
                        </p>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                        <label className="text-xs text-muted-foreground flex items-center gap-2">
                            {t("libroRegistro.year")}
                            <Input
                                type="number"
                                min={2020}
                                max={yearNow + 1}
                                value={year}
                                onChange={(e) => setYear(Number(e.target.value) || yearNow)}
                                className="w-20 h-8"
                            />
                        </label>
                        <Button
                            variant="outline"
                            size="sm"
                            disabled={busy !== null}
                            onClick={() => void download("emitidas")}
                            className="text-emerald-400 border-emerald-500/30 hover:bg-emerald-600/20"
                        >
                            {busy === "emitidas" ? <Loader2 className="mr-1.5 w-3.5 h-3.5 animate-spin" /> : <Download className="mr-1.5 w-3.5 h-3.5" />}
                            {t("libroRegistro.emitidas")}
                        </Button>
                        <Button
                            variant="outline"
                            size="sm"
                            disabled={busy !== null}
                            onClick={() => void download("recibidas")}
                            className="text-primary border-primary/20 hover:bg-primary/20"
                        >
                            {busy === "recibidas" ? <Loader2 className="mr-1.5 w-3.5 h-3.5 animate-spin" /> : <Download className="mr-1.5 w-3.5 h-3.5" />}
                            {t("libroRegistro.recibidas")}
                        </Button>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}
