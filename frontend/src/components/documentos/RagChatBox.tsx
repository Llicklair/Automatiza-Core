"use client";

import { useState } from "react";
import { Bot, User, FileText, Loader2, Send } from "lucide-react";
import { api } from "@/lib/api";

type ChatMessage = {
    role: "user" | "ai";
    content: string;
    sources?: number;
    sourceNames?: string[];
};

export default function RagChatBox() {
    const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
    const [chatInput, setChatInput] = useState("");
    const [chatLoading, setChatLoading] = useState(false);

    async function handleChat(e: React.FormEvent) {
        e.preventDefault();
        const prompt = chatInput.trim();
        if (!prompt) return;

        setChatInput("");
        setChatMessages(prev => [...prev, { role: "user", content: prompt }]);
        setChatLoading(true);

        try {
            const task = await api.tasks.create("rag", prompt);
            let current = task;

            while (current.status !== "done" && current.status !== "failed" && current.status !== "cancelled") {
                await new Promise(r => setTimeout(r, 2000));
                current = await api.tasks.get(task.id);
            }

            if (current.status === "done" && current.agent_results) {
                const ragResult = current.agent_results.find((r: any) => r.agent === "rag");
                if (ragResult?.success) {
                    setChatMessages(prev => [...prev, {
                        role: "ai",
                        content: ragResult.output.answer,
                        sources: ragResult.output.sources_used,
                        sourceNames: ragResult.output.source_names
                    }]);
                } else {
                    setChatMessages(prev => [...prev, { role: "ai", content: "No pude procesar la respuesta." }]);
                }
            } else {
                setChatMessages(prev => [...prev, { role: "ai", content: current.error_message || "La tarea fallo." }]);
            }

        } catch (err: any) {
            setChatMessages(prev => [...prev, { role: "ai", content: `Error de conexion: ${err.message}` }]);
        } finally {
            setChatLoading(false);
        }
    }

    return (
        <div className="rounded-xl border border-border bg-card overflow-hidden flex flex-col shadow-lg">
            <div className="px-6 py-4 border-b border-border flex items-center gap-3">
                <Bot className="w-5 h-5 text-indigo-400" />
                <h2 className="text-sm font-semibold text-foreground">Busqueda Universal & Consultas IA</h2>
            </div>

            <div className="p-6">
                {chatMessages.length === 0 ? (
                    <div className="text-center py-4">
                        <p className="text-sm text-muted-foreground">Encuentra cualquier archivo o pregunta detalles tecnicos a tus documentos.</p>
                        <p className="text-xs text-muted-foreground mt-1">Ej: &quot;Busca la factura de Amazon&quot; o &quot;Resume el contrato de alquiler&quot;.</p>
                    </div>
                ) : (
                    <div className="space-y-4 max-h-[280px] overflow-y-auto mb-4 pr-2">
                        {chatMessages.map((msg, idx) => (
                            <div key={idx} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                {msg.role === 'ai' && <div className="w-8 h-8 rounded-full bg-indigo-500/20 flex items-center justify-center flex-shrink-0"><Bot className="w-4 h-4 text-indigo-400" /></div>}
                                <div className={`px-4 py-3 rounded-2xl max-w-[80%] text-sm ${msg.role === 'user' ? 'bg-indigo-600 text-foreground rounded-br-none' : 'bg-muted text-foreground rounded-bl-none'}`}>
                                    <div className="whitespace-pre-wrap">{msg.content}</div>
                                    {msg.sourceNames && msg.sourceNames.length > 0 && (
                                        <div className="mt-2 pt-2 border-t border-white/5 space-y-1">
                                            <p className="text-[10px] text-muted-foreground font-medium uppercase tracking-wider">Archivos relacionados:</p>
                                            {msg.sourceNames.map((name, i) => (
                                                <div key={i} className="text-[10px] text-indigo-400 font-mono flex items-center gap-1">
                                                    <FileText className="w-3 h-3" /> {name}
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                                {msg.role === 'user' && <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center flex-shrink-0"><User className="w-4 h-4 text-muted-foreground" /></div>}
                            </div>
                        ))}
                        {chatLoading && (
                            <div className="flex gap-3 justify-start">
                                <div className="w-8 h-8 rounded-full bg-indigo-500/20 flex items-center justify-center flex-shrink-0"><Bot className="w-4 h-4 text-indigo-400" /></div>
                                <div className="px-4 py-3 rounded-2xl bg-muted text-muted-foreground rounded-bl-none text-sm flex items-center gap-2">
                                    <Loader2 className="w-4 h-4 animate-spin" /> Consultando base de datos vectorial...
                                </div>
                            </div>
                        )}
                    </div>
                )}

                <form onSubmit={handleChat} className="flex gap-3">
                    <input
                        type="text"
                        value={chatInput}
                        onChange={(e) => setChatInput(e.target.value)}
                        disabled={chatLoading}
                        placeholder="Ej. Que dice el contrato sobre la rescision anticipada?"
                        className="flex-1 bg-background border border-border text-sm text-foreground rounded-xl px-4 py-3 focus:outline-none focus:border-primary transition disabled:opacity-50"
                    />
                    <button
                        type="submit"
                        disabled={chatLoading || !chatInput.trim()}
                        className="bg-indigo-600 hover:bg-indigo-500 text-foreground px-5 rounded-xl transition flex items-center justify-center disabled:opacity-50"
                    >
                        <Send className="w-4 h-4" />
                    </button>
                </form>
            </div>
        </div>
    );
}
