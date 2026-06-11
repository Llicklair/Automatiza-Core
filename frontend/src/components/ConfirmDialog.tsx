"use client";

import { useConfirmStore } from "@/stores/confirm";
import { AlertTriangle, Trash2, X } from "lucide-react";

export default function ConfirmDialog() {
    const { open, options, _confirm, _cancel } = useConfirmStore();

    if (!open || !options) return null;

    const variant = options.confirmVariant ?? "danger";
    const btnCls =
        variant === "danger"
            ? "bg-red-600 hover:bg-red-500 text-foreground"
            : variant === "warning"
            ? "bg-amber-500 hover:bg-amber-400 text-foreground"
            : "bg-indigo-600 hover:bg-indigo-500 text-foreground";

    const icon =
        variant === "danger" ? (
            <Trash2 className="w-5 h-5 text-red-400" />
        ) : (
            <AlertTriangle className="w-5 h-5 text-amber-400" />
        );

    return (
        <div
            className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/70 backdrop-blur-sm"
            onClick={_cancel}
        >
            <div
                role="alertdialog"
                aria-modal="true"
                aria-labelledby="confirm-dialog-title"
                className="w-full max-w-sm rounded-2xl border border-border bg-card shadow-2xl overflow-hidden"
                onClick={(e) => e.stopPropagation()}
            >
                <div className="flex items-center justify-between px-5 py-4 border-b border-border">
                    <div className="flex items-center gap-2">
                        {icon}
                        <span id="confirm-dialog-title" className="font-semibold text-foreground text-sm">
                            {options.title ?? "Confirmar acción"}
                        </span>
                    </div>
                    <button
                        onClick={_cancel}
                        className="text-muted-foreground hover:text-foreground transition-colors"
                     aria-label="Cerrar">
                        <X className="w-4 h-4" aria-hidden="true" />
                    </button>
                </div>

                <div className="px-5 py-4">
                    <p className="text-sm text-foreground leading-relaxed">
                        {options.message}
                    </p>
                </div>

                <div className="flex gap-2 px-5 pb-5">
                    <button
                        onClick={_cancel}
                        className="flex-1 py-2 rounded-xl border border-border text-muted-foreground text-sm hover:text-foreground hover:bg-white/5 transition-colors"
                    >
                        {options.cancelLabel ?? "Cancelar"}
                    </button>
                    <button
                        onClick={_confirm}
                        className={`flex-1 py-2 rounded-xl text-sm font-medium transition-colors ${btnCls}`}
                    >
                        {options.confirmLabel ?? "Confirmar"}
                    </button>
                </div>
            </div>
        </div>
    );
}
