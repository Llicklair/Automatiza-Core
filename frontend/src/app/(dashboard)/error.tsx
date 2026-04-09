"use client";

import { useEffect } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { logError } from "@/lib/logger";
import { reportError } from "@/lib/error-reporter";

export default function DashboardError({
    error,
    reset,
}: {
    error: Error & { digest?: string };
    reset: () => void;
}) {
    useEffect(() => {
        logError("dashboard", error);
        reportError(error, "DashboardError");
    }, [error]);

    return (
        <div className="flex-1 flex flex-col items-center justify-center min-h-[60vh] gap-6 px-6">
            <div className="bg-red-500/10 w-16 h-16 rounded-full flex items-center justify-center">
                <AlertTriangle className="w-8 h-8 text-red-400" />
            </div>
            <div className="text-center max-w-md">
                <h2 className="text-lg font-semibold text-foreground mb-2">Algo salió mal</h2>
                <p className="text-muted-foreground text-sm">
                    {error.message || "Se ha producido un error inesperado. Inténtalo de nuevo."}
                </p>
            </div>
            <button
                onClick={reset}
                className="flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary text-foreground text-sm font-medium rounded-lg transition-colors"
            >
                <RefreshCw className="w-4 h-4" />
                Reintentar
            </button>
        </div>
    );
}
