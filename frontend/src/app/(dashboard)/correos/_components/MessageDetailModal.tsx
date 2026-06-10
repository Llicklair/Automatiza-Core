"use client";

import type { Dispatch, SetStateAction } from "react";
import { Loader2, X, Sparkles } from "lucide-react";
import type { EmailDetail } from "@/lib/api/messaging";
import { formatDate } from "../format";

interface MessageDetailModalProps {
    selectedMsg: EmailDetail | null;
    bodyLoading: boolean;
    setSelectedMsg: Dispatch<SetStateAction<EmailDetail | null>>;
    setBodyLoading: Dispatch<SetStateAction<boolean>>;
    draftLoading: boolean;
    draftError: string | null;
    handleDraftReply: () => void;
}

export function MessageDetailModal({
    selectedMsg,
    bodyLoading,
    setSelectedMsg,
    setBodyLoading,
    draftLoading,
    draftError,
    handleDraftReply,
}: MessageDetailModalProps) {
    return (
        <div
            className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4"
            onClick={() => { setSelectedMsg(null); setBodyLoading(false); }}
        >
            <div
                className="bg-background border border-border rounded-xl max-w-2xl w-full max-h-[85vh] overflow-hidden flex flex-col"
                onClick={(e) => e.stopPropagation()}
            >
                <div className="flex items-start justify-between gap-4 p-5 border-b border-border">
                    {bodyLoading || !selectedMsg ? (
                        <div className="flex items-center gap-2 text-muted-foreground text-sm">
                            <Loader2 className="w-4 h-4 animate-spin" /> Cargando…
                        </div>
                    ) : (
                        <div className="min-w-0 flex-1">
                            <h3 className="text-base font-semibold text-foreground truncate">{selectedMsg.subject || "(sin asunto)"}</h3>
                            <p className="text-xs text-muted-foreground mt-1">
                                <strong className="text-foreground/80">De:</strong> {selectedMsg.from}
                            </p>
                            <p className="text-xs text-muted-foreground">
                                <strong className="text-foreground/80">Para:</strong> {selectedMsg.to || "—"}
                            </p>
                            <p className="text-[11px] text-muted-foreground mt-1">{formatDate(selectedMsg.date)}</p>
                        </div>
                    )}
                    <button
                        onClick={() => { setSelectedMsg(null); setBodyLoading(false); }}
                        className="text-muted-foreground hover:text-foreground"
                        aria-label="Cerrar"
                    >
                        <X className="w-4 h-4" />
                    </button>
                </div>
                <div className="p-5 overflow-auto flex-1">
                    {selectedMsg && (
                        selectedMsg.provider === "outlook" && /<[a-z][^>]*>/i.test(selectedMsg.body)
                            ? <div className="prose prose-sm dark:prose-invert max-w-none" dangerouslySetInnerHTML={{ __html: selectedMsg.body }} />
                            : <pre className="whitespace-pre-wrap text-sm text-foreground font-sans">{selectedMsg.body}</pre>
                    )}
                </div>
                {selectedMsg && (
                    <div className="p-4 border-t border-border bg-muted/20 flex items-center justify-between gap-3">
                        <div className="text-xs text-muted-foreground">
                            {draftError ? <span className="text-rose-400">{draftError}</span> : "Genera un borrador y revísalo antes de enviar."}
                        </div>
                        <button
                            onClick={handleDraftReply}
                            disabled={draftLoading}
                            className="inline-flex items-center gap-2 h-9 px-3 rounded-md bg-primary text-primary-foreground text-sm font-medium hover:brightness-110 transition disabled:opacity-50"
                        >
                            {draftLoading
                                ? <><Loader2 className="w-4 h-4 animate-spin" /> Redactando…</>
                                : <><Sparkles className="w-4 h-4" /> Borrador IA</>}
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}
