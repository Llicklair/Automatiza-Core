"use client";

import { Bot, Loader2, Send, User, Scale } from "lucide-react";

interface AdvisoryChatPanelProps {
    chatMessages: { role: "user" | "ai"; content: string }[];
    chatInput: string;
    setChatInput: (v: string) => void;
    chatLoading: boolean;
    onSubmit: (e: React.FormEvent) => void;
}

export function AdvisoryChatPanel({ chatMessages, chatInput, setChatInput, chatLoading, onSubmit }: AdvisoryChatPanelProps) {
    return (
        <div className="bg-card border border-border rounded-2xl overflow-hidden shadow-lg shadow-black/20 flex flex-col h-[400px]">
            <div className="px-5 py-4 border-b border-border flex items-center justify-between bg-card">
                <div className="flex items-center gap-2">
                    <Bot className="w-5 h-5 text-primary" />
                    <h2 className="text-sm font-semibold text-foreground">Consulta al Asesor IA</h2>
                </div>
            </div>

            <div className="flex-1 overflow-y-auto p-5 space-y-4 custom-scrollbar">
                {chatMessages.length === 0 ? (
                    <div className="text-center py-10 flex flex-col items-center justify-center h-full">
                        <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center mb-3">
                            <Scale className="w-6 h-6 text-primary" />
                        </div>
                        <p className="text-sm text-muted-foreground">¿Tienes dudas fiscales?</p>
                        <p className="text-xs text-muted-foreground mt-1 max-w-[200px] leading-relaxed">Pregunta sobre impuestos, deducciones o vencimientos de tu cuenta.</p>
                    </div>
                ) : (
                    chatMessages.map((msg, idx) => (
                        <div key={idx} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                            {msg.role === 'ai' && <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center flex-shrink-0"><Bot className="w-4 h-4 text-primary" /></div>}
                            <div className={`px-4 py-3 rounded-2xl max-w-[85%] text-sm ${msg.role === 'user' ? 'bg-primary text-foreground rounded-br-none' : 'bg-muted text-foreground rounded-bl-none border border-border'}`}>
                                <div className="whitespace-pre-wrap">{msg.content}</div>
                            </div>
                            {msg.role === 'user' && <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center flex-shrink-0"><User className="w-4 h-4 text-muted-foreground" /></div>}
                        </div>
                    ))
                )}
                {chatLoading && (
                    <div className="flex gap-3 justify-start">
                        <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center flex-shrink-0"><Bot className="w-4 h-4 text-primary" /></div>
                        <div className="px-4 py-3 rounded-2xl bg-muted text-muted-foreground rounded-bl-none text-sm flex items-center gap-2 border border-border">
                            <Loader2 className="w-4 h-4 animate-spin flex-shrink-0" /> Analizando contexto legal...
                        </div>
                    </div>
                )}
            </div>

            <div className="p-3 border-t border-border bg-card">
                <form onSubmit={onSubmit} className="flex gap-2">
                    <input
                        type="text"
                        value={chatInput}
                        onChange={(e) => setChatInput(e.target.value)}
                        disabled={chatLoading}
                        placeholder="Ej. ¿Cuándo presento el IVA?"
                        className="flex-1 bg-background border border-border text-sm text-foreground rounded-xl px-4 py-3 focus:outline-none focus:border-primary transition disabled:opacity-50"
                    />
                    <button
                        type="submit"
                        disabled={chatLoading || !chatInput.trim()}
                        className="bg-primary hover:bg-primary text-foreground px-4 py-3 rounded-xl transition flex items-center justify-center disabled:opacity-50"
                     aria-label="Enviar mensaje">
                        <Send className="w-4 h-4" aria-hidden="true" />
                    </button>
                </form>
            </div>
        </div>
    );
}
