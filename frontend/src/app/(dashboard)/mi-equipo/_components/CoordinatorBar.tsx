"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { surfaceIfConnectivity } from "@/lib/api/errors";
import { Bot, Loader2, Send } from "lucide-react";

export function CoordinatorBar({ onSent }: { onSent: () => void }) {
    const [text, setText] = useState("");
    const [loading, setLoading] = useState(false);
    const [sent, setSent] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleSend = async () => {
        if (!text.trim() || loading) return;
        setLoading(true); setError(null);
        try {
            await api.tasks.create("coordinator", text.trim());
            setText("");
            setSent(true);
            setTimeout(() => setSent(false), 3000);
            onSent();
        } catch (e: any) {
            if (surfaceIfConnectivity(e)) return;
            setError(e?.message ?? "Error al enviar instrucción al coordinador");
            setTimeout(() => setError(null), 5000);
        }
        finally { setLoading(false); }
    };

    return (
        <div className="space-y-1">
            <div className="flex items-center gap-2 bg-card border border-border rounded-xl px-4 py-3">
                <div className="w-7 h-7 rounded-full bg-violet-500/10 border border-violet-500/20 flex items-center justify-center shrink-0">
                    <Bot className="w-3.5 h-3.5 text-violet-400" />
                </div>
                <input
                    value={text}
                    onChange={e => setText(e.target.value)}
                    onKeyDown={e => e.key === "Enter" && handleSend()}
                    placeholder="Dile al coordinador qué necesitas… Ej: necesito un empleado de marketing"
                    className="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground focus:outline-none"
                />
                {sent ? (
                    <span className="text-xs text-emerald-400 shrink-0">✓ Enviado</span>
                ) : (
                    <button onClick={handleSend} disabled={!text.trim() || loading}
                        className="p-1.5 rounded-lg bg-violet-600 hover:bg-violet-500 disabled:opacity-40 text-foreground transition-colors shrink-0" aria-label="Enviar instrucción">
                        {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" aria-hidden="true" /> : <Send className="w-3.5 h-3.5" aria-hidden="true" />}
                    </button>
                )}
            </div>
            {error && <p className="text-xs text-red-400 px-4">{error}</p>}
        </div>
    );
}
