"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { useToastStore } from "@/stores/toast";
import { FileText, Loader2, Download } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function LibroRegistroExport() {
    const show = useToastStore((s) => s.show);
    const yearNow = new Date().getFullYear();
    const [year, setYear] = useState(yearNow);
    const [busy, setBusy] = useState<"emitidas" | "recibidas" | null>(null);

    const download = async (type: "emitidas" | "recibidas") => {
        setBusy(type);
        try {
            await api.reports.libroRegistro(year, type);
            show(`Libro ${type} ${year} descargado`, "success");
        } catch (e: unknown) {
            const msg = e instanceof Error ? e.message : "No se pudo descargar el CSV";
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
                            Libro registro de facturas (AEAT)
                        </h2>
                        <p className="text-xs text-muted-foreground mt-1 max-w-xl">
                            Exporta CSV con facturas emitidas o recibidas del ejercicio para contabilidad o revisión.
                        </p>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                        <label className="text-xs text-muted-foreground flex items-center gap-2">
                            Año
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
                            Emitidas
                        </Button>
                        <Button
                            variant="outline"
                            size="sm"
                            disabled={busy !== null}
                            onClick={() => void download("recibidas")}
                            className="text-primary border-primary/20 hover:bg-primary/20"
                        >
                            {busy === "recibidas" ? <Loader2 className="mr-1.5 w-3.5 h-3.5 animate-spin" /> : <Download className="mr-1.5 w-3.5 h-3.5" />}
                            Recibidas
                        </Button>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}
