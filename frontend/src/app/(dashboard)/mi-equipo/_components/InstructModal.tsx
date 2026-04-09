"use client";

import { useState } from "react";
import type { AIEmployee } from "@/lib/api/ai_employees";
import { api } from "@/lib/api";
import { X, Loader2 } from "lucide-react";

export function InstructModal({ employee, onClose, onSent }: {
    employee: AIEmployee; onClose: () => void; onSent: () => void;
}) {
    const [message, setMessage] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleSend = async () => {
        if (!message.trim()) return;
        setLoading(true); setError(null);
        try {
            await api.aiEmployees.instruct(employee.id, message.trim());
            onSent(); onClose();
        } catch (e: any) { setError(e?.message ?? "Error al enviar instrucción"); }
        finally { setLoading(false); }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
            <div className="bg-card border border-border rounded-2xl shadow-xl w-full max-w-md p-6 space-y-4">
                <div className="flex items-center justify-between">
                    <h2 className="font-semibold text-foreground text-sm">Instrucción → {employee.name}</h2>
                    <button onClick={onClose} className="p-1 hover:bg-muted rounded-lg"><X className="w-4 h-4 text-muted-foreground" /></button>
                </div>
                <p className="text-xs text-muted-foreground">La instrucción pasará por el coordinador, que decidirá cómo ejecutarla.</p>
                <textarea
                    autoFocus value={message} onChange={e => setMessage(e.target.value)}
                    placeholder="Ej: Genera la nómina de enero para todos los empleados activos…"
                    rows={4}
                    className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-violet-500/50 resize-none"
                />
                {error && <p className="text-xs text-red-400">{error}</p>}
                <div className="flex justify-end gap-2">
                    <button onClick={onClose} className="px-4 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg">Cancelar</button>
                    <button onClick={handleSend} disabled={!message.trim() || loading}
                        className="flex items-center gap-2 px-4 py-2 bg-violet-600 hover:bg-violet-500 text-foreground rounded-lg text-sm font-medium disabled:opacity-50 transition-colors">
                        {loading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                        Enviar
                    </button>
                </div>
            </div>
        </div>
    );
}
