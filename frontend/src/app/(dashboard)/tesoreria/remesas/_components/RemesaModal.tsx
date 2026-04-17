import { Loader2, CheckCircle2, AlertCircle, Download, X } from "lucide-react";

const fmt = (v: number) =>
    new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" }).format(v);

interface RemesaModalProps {
    agentStatus: "idle" | "creating" | "polling" | "done" | "failed";
    agentError: string | null;
    selectedCount: number;
    totalSelected: number;
    onClose: () => void;
    onCloseAndReset: () => void;
}

export default function RemesaModal({
    agentStatus, agentError, selectedCount, totalSelected, onClose, onCloseAndReset,
}: RemesaModalProps) {
    const isProcessing = agentStatus === "creating" || agentStatus === "polling";

    return (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4" onClick={() => { if (!isProcessing) onClose(); }}>
            <div className="w-full max-w-md bg-card border border-border rounded-2xl overflow-hidden" onClick={e => e.stopPropagation()}>
                <div className="flex items-center justify-between px-6 py-4 border-b border-border">
                    <h2 className="font-semibold text-foreground">Generando Remesa SEPA</h2>
                    {!isProcessing && (
                        <button onClick={onCloseAndReset} className="text-muted-foreground hover:text-foreground">
                            <X className="w-5 h-5" />
                        </button>
                    )}
                </div>
                <div className="p-8 flex flex-col items-center text-center gap-4">
                    {isProcessing && (
                        <>
                            <Loader2 className="w-12 h-12 text-primary animate-spin" />
                            <div>
                                <p className="text-foreground font-semibold mb-1">El agente esta procesando la remesa</p>
                                <p className="text-xs text-muted-foreground">Agrupando {selectedCount} concepto{selectedCount !== 1 ? "s" : ""} por {fmt(totalSelected)}...</p>
                            </div>
                        </>
                    )}
                    {agentStatus === "done" && (
                        <>
                            <CheckCircle2 className="w-12 h-12 text-emerald-400" />
                            <div>
                                <p className="text-foreground font-semibold mb-1">Remesa generada correctamente</p>
                                <p className="text-xs text-muted-foreground mb-4">El fichero SEPA XML ha sido creado y registrado en Documentos.</p>
                            </div>
                            <div className="flex gap-3 w-full">
                                <button
                                    onClick={onCloseAndReset}
                                    className="flex-1 py-2.5 bg-muted hover:bg-muted border border-border text-foreground rounded-xl text-sm font-medium transition-colors"
                                >
                                    Cerrar
                                </button>
                                <button className="flex-1 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-foreground rounded-xl text-sm font-medium transition-colors flex items-center justify-center gap-2">
                                    <Download className="w-4 h-4" /> Ver en Documentos
                                </button>
                            </div>
                        </>
                    )}
                    {agentStatus === "failed" && (
                        <>
                            <AlertCircle className="w-12 h-12 text-red-400" />
                            <div>
                                <p className="text-foreground font-semibold mb-1">Error al generar la remesa</p>
                                <p className="text-xs text-red-400 mb-4">{agentError || "Error desconocido"}</p>
                            </div>
                            <button onClick={onCloseAndReset} className="w-full py-2.5 bg-muted hover:bg-muted border border-border text-foreground rounded-xl text-sm font-medium transition-colors">
                                Cerrar
                            </button>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}
