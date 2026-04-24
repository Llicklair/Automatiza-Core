"use client";

import { useState, useEffect } from "react";
import { Mail, Send, Bot, AlertCircle, CheckCircle2, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import type { EmailStatus } from "@/lib/api/messaging";

const TABS = [
    { key: "componer", label: "Componer", icon: Send },
    { key: "ia", label: "Instrucción IA", icon: Bot },
] as const;
type TabKey = (typeof TABS)[number]["key"];

export default function CorreosPage() {
    const [activeTab, setActiveTab] = useState<TabKey>("componer");
    const [status, setStatus] = useState<EmailStatus | null>(null);

    // Compose form
    const [to, setTo] = useState("");
    const [subject, setSubject] = useState("");
    const [body, setBody] = useState("");

    // AI instruct form
    const [instruction, setInstruction] = useState("");

    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<{ ok: boolean; message: string } | null>(null);

    useEffect(() => {
        api.messaging.email.status().then(setStatus).catch(() => null);
    }, []);

    async function handleSend(e: React.FormEvent) {
        e.preventDefault();
        setLoading(true);
        setResult(null);
        try {
            const res = await api.messaging.email.send(to, subject, body);
            setResult({ ok: true, message: res.result });
            setTo(""); setSubject(""); setBody("");
        } catch (err: unknown) {
            setResult({ ok: false, message: err instanceof Error ? err.message : "Error al enviar" });
        } finally {
            setLoading(false);
        }
    }

    async function handleInstruct(e: React.FormEvent) {
        e.preventDefault();
        setLoading(true);
        setResult(null);
        try {
            const res = await api.messaging.email.instruct(instruction);
            setResult({ ok: res.success, message: res.action });
            if (res.success) setInstruction("");
        } catch (err: unknown) {
            setResult({ ok: false, message: err instanceof Error ? err.message : "Error al procesar instrucción" });
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="max-w-3xl mx-auto px-4 py-8 space-y-6">
            {/* Header */}
            <div className="flex items-start justify-between">
                <div>
                    <h1 className="text-xl font-semibold text-foreground flex items-center gap-2">
                        <Mail className="w-6 h-6 text-violet-400" /> Correos
                    </h1>
                    <p className="text-xs text-muted-foreground mt-1">Envía correos o instruye al agente de email</p>
                </div>
                {status && (
                    <div className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full border ${
                        status.configured
                            ? "bg-green-500/10 text-green-400 border-green-500/30"
                            : "bg-amber-500/10 text-amber-400 border-amber-500/30"
                    }`}>
                        {status.configured
                            ? <><CheckCircle2 className="w-3.5 h-3.5" /> Conectado</>
                            : <><AlertCircle className="w-3.5 h-3.5" /> Sin credenciales</>
                        }
                    </div>
                )}
            </div>

            {/* Config warning */}
            {status && !status.configured && (
                <div className="flex gap-2 text-sm text-amber-400 bg-amber-500/10 border border-amber-500/20 rounded-lg px-4 py-3">
                    <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
                    <span>No hay credenciales de email configuradas. Configura Gmail, Outlook o SMTP en <strong>Configuración &rsaquo; Integraciones</strong>. Los envíos funcionarán en modo demo.</span>
                </div>
            )}

            {/* Tabs */}
            <div className="flex gap-1 border-b border-border">
                {TABS.map(tab => {
                    const Icon = tab.icon;
                    const isActive = activeTab === tab.key;
                    return (
                        <button
                            key={tab.key}
                            onClick={() => { setActiveTab(tab.key); setResult(null); }}
                            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px ${
                                isActive
                                    ? "border-violet-500 text-foreground"
                                    : "border-transparent text-muted-foreground hover:text-foreground hover:border-border"
                            }`}
                        >
                            <Icon className="w-4 h-4" />
                            {tab.label}
                        </button>
                    );
                })}
            </div>

            {/* Result banner */}
            {result && (
                <div className={`flex gap-2 text-sm rounded-lg px-4 py-3 border ${
                    result.ok
                        ? "bg-green-500/10 text-green-400 border-green-500/20"
                        : "bg-red-500/10 text-red-400 border-red-500/20"
                }`}>
                    {result.ok ? <CheckCircle2 className="w-4 h-4 mt-0.5 shrink-0" /> : <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />}
                    <span>{result.message}</span>
                </div>
            )}

            {/* Compose tab */}
            {activeTab === "componer" && (
                <form onSubmit={handleSend} className="space-y-4">
                    <div className="space-y-1">
                        <label className="text-xs font-medium text-muted-foreground">Para</label>
                        <input
                            type="email"
                            required
                            value={to}
                            onChange={e => setTo(e.target.value)}
                            placeholder="destinatario@ejemplo.com"
                            className="w-full bg-card border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-violet-500"
                        />
                    </div>
                    <div className="space-y-1">
                        <label className="text-xs font-medium text-muted-foreground">Asunto</label>
                        <input
                            type="text"
                            required
                            value={subject}
                            onChange={e => setSubject(e.target.value)}
                            placeholder="Asunto del correo"
                            className="w-full bg-card border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-violet-500"
                        />
                    </div>
                    <div className="space-y-1">
                        <label className="text-xs font-medium text-muted-foreground">Mensaje</label>
                        <textarea
                            required
                            rows={6}
                            value={body}
                            onChange={e => setBody(e.target.value)}
                            placeholder="Escribe el contenido del correo..."
                            className="w-full bg-card border border-border rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-violet-500"
                        />
                    </div>
                    <button
                        type="submit"
                        disabled={loading}
                        className="flex items-center gap-2 px-4 py-2 bg-violet-600 hover:bg-violet-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
                    >
                        {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                        Enviar correo
                    </button>
                </form>
            )}

            {/* AI instruct tab */}
            {activeTab === "ia" && (
                <form onSubmit={handleInstruct} className="space-y-4">
                    <p className="text-sm text-muted-foreground">
                        Dile al agente qué hacer con el correo en lenguaje natural. Ejemplos: &ldquo;Muéstrame los correos no leídos&rdquo;, &ldquo;Envía un resumen de facturas pendientes a contabilidad@empresa.com&rdquo;.
                    </p>
                    <textarea
                        required
                        rows={4}
                        value={instruction}
                        onChange={e => setInstruction(e.target.value)}
                        placeholder="Instrucción para el agente de email..."
                        className="w-full bg-card border border-border rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-violet-500"
                    />
                    <button
                        type="submit"
                        disabled={loading}
                        className="flex items-center gap-2 px-4 py-2 bg-violet-600 hover:bg-violet-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
                    >
                        {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Bot className="w-4 h-4" />}
                        Ejecutar instrucción
                    </button>
                </form>
            )}
        </div>
    );
}
