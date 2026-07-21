"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { Download, Loader2 } from "lucide-react";
import { verifactuConfig } from "@/lib/api/verifactuConfig";
import { useToastStore } from "@/stores/toast";

export function DeclaracionResponsablePanel() {
    const t = useTranslations("configuracion");
    const toast = useToastStore();
    const [texto, setTexto] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let cancelled = false;
        (async () => {
            try {
                const blob = await verifactuConfig.declaracionResponsable();
                const text = await blob.text();
                if (!cancelled) setTexto(text);
            } catch {
                if (!cancelled) toast.error(t("verifactu.declaracionError"));
            } finally {
                if (!cancelled) setLoading(false);
            }
        })();
        return () => {
            cancelled = true;
        };
    }, [t, toast]);

    return (
        <div className="space-y-4">
            <div>
                <h2 className="text-base font-semibold text-foreground">{t("verifactu.declaracionTitle")}</h2>
                <p className="text-sm text-muted-foreground mt-1">{t("verifactu.declaracionDesc")}</p>
            </div>

            {loading ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Loader2 className="w-4 h-4 animate-spin" /> {t("verifactu.declaracionLoading")}
                </div>
            ) : (
                <>
                    <pre className="bg-muted border border-border rounded-xl p-4 text-xs text-foreground whitespace-pre-wrap max-h-[50vh] overflow-auto">
                        {texto}
                    </pre>
                    <button
                        onClick={() => verifactuConfig.descargarDeclaracionResponsable()}
                        className="flex items-center gap-2 border border-border hover:bg-muted/60 text-foreground text-sm px-4 py-2 rounded-xl transition-colors"
                    >
                        <Download className="w-4 h-4" /> {t("verifactu.declaracionDownload")}
                    </button>
                </>
            )}
        </div>
    );
}
