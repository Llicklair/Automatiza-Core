"use client";

import { CheckCircle2, AlertCircle, X } from "lucide-react";

interface QuoteToastProps {
    toast: { msg: string; type: "ok" | "err" };
    onClose: () => void;
}

export default function QuoteToast({ toast, onClose }: QuoteToastProps) {
    return (
        <div className={`fixed bottom-6 right-6 z-50 flex items-center gap-3 px-5 py-3 rounded-2xl shadow-2xl text-sm font-medium max-w-sm ${
            toast.type === "ok"
                ? "bg-emerald-500/10 border border-emerald-500/20 text-emerald-400"
                : "bg-red-500/10 border border-red-500/20 text-red-400"
        }`}>
            {toast.type === "ok" ? <CheckCircle2 className="w-5 h-5 flex-shrink-0" /> : <AlertCircle className="w-5 h-5 flex-shrink-0" />}
            <span className="flex-1">{toast.msg}</span>
            <button onClick={onClose} className="opacity-60 hover:opacity-100" aria-label="Cerrar notificación"><X className="w-4 h-4" aria-hidden="true" /></button>
        </div>
    );
}
