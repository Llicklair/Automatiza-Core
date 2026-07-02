"use client";

import { useState } from "react";
import Link from "next/link";
import {
    FileSignature, Loader2, Send, Save, ChevronDown, ChevronUp, CheckCircle2,
} from "lucide-react";
import { documents, type ContractInterviewResult } from "@/lib/api/documents";
import { useToastStore } from "@/stores/toast";
import { logError } from "@/lib/logger";

const CONTRACT_TYPES = [
    { value: "servicios", label: "Prestación de Servicios" },
    { value: "trabajo", label: "Contrato de Trabajo" },
    { value: "nda", label: "Confidencialidad (NDA)" },
    { value: "alquiler", label: "Arrendamiento (Alquiler)" },
];

type Msg = { role: "user" | "assistant"; content: string };

/**
 * Asistente conversacional: la IA entrevista al usuario una pregunta a la vez y
 * al terminar redacta el contrato profesional, que se puede guardar en Documentos.
 */
export default function ContractWizard() {
    const toast = useToastStore();
    const [open, setOpen] = useState(false);
    const [type, setType] = useState("servicios");
    const [started, setStarted] = useState(false);
    const [messages, setMessages] = useState<Msg[]>([]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const [contract, setContract] = useState<string | null>(null);
    const [saving, setSaving] = useState(false);
    const [saved, setSaved] = useState(false);

    const typeLabel = CONTRACT_TYPES.find((t) => t.value === type)?.label ?? type;

    const send = async (history: Msg[]) => {
        setLoading(true);
        try {
            const res: ContractInterviewResult = await documents.contracts.interview(type, history);
            setMessages([...history, { role: "assistant", content: res.message }]);
            if (res.done && res.contract) setContract(res.contract);
        } catch (err) {
            logError("documentos/contract-wizard", err);
            toast.error(err instanceof Error ? err.message : "Error en el asistente");
        } finally {
            setLoading(false);
        }
    };

    const start = async () => {
        setStarted(true);
        setMessages([]);
        setContract(null);
        setSaved(false);
        await send([]);
    };

    const onSend = async () => {
        const text = input.trim();
        if (!text) return;
        const history: Msg[] = [...messages, { role: "user", content: text }];
        setMessages(history);
        setInput("");
        await send(history);
    };

    const save = async () => {
        if (!contract) return;
        setSaving(true);
        try {
            const title = `${typeLabel} ${new Date().toLocaleDateString("es-ES")}`;
            await documents.contracts.save(type, title, contract);
            setSaved(true);
            toast.success("Contrato guardado en Documentos");
        } catch (err) {
            toast.error(err instanceof Error ? err.message : "No se pudo guardar el contrato");
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="bg-card border border-border rounded-2xl overflow-hidden">
            <button
                onClick={() => setOpen((o) => !o)}
                className="w-full flex items-center justify-between px-5 py-4"
            >
                <span className="flex items-center gap-2 text-sm font-semibold text-foreground">
                    <FileSignature className="w-4 h-4 text-primary" /> Asistente de Contratos (IA)
                </span>
                {open ? (
                    <ChevronUp className="w-4 h-4 text-muted-foreground" />
                ) : (
                    <ChevronDown className="w-4 h-4 text-muted-foreground" />
                )}
            </button>

            {open && (
                <div className="px-5 pb-5 space-y-4 border-t border-border pt-4">
                    {type === "trabajo" && (
                        <div className="text-xs text-amber-400/90 bg-amber-500/5 border border-amber-500/20 rounded-lg px-3 py-2">
                            Para contratos laborales de empleados con registro y flujo de aprobación usa la{" "}
                            <Link href="/rrhh/documentos" className="underline hover:text-amber-300">
                                Gestoría Documental de RRHH
                            </Link>
                            . Este asistente guarda el resultado como documento general, sin aprobación.
                        </div>
                    )}
                    <div className="flex items-center gap-2 flex-wrap">
                        <select
                            value={type}
                            onChange={(e) => setType(e.target.value)}
                            disabled={started && !contract}
                            className="text-sm bg-background border border-border rounded-lg px-3 py-1.5 text-foreground focus:outline-none focus:border-primary disabled:opacity-50"
                        >
                            {CONTRACT_TYPES.map((t) => (
                                <option key={t.value} value={t.value}>{t.label}</option>
                            ))}
                        </select>
                        <button
                            onClick={start}
                            disabled={loading}
                            className="inline-flex items-center gap-1.5 bg-primary text-foreground text-sm px-3 py-1.5 rounded-lg font-medium disabled:opacity-50"
                        >
                            {loading && messages.length === 0 ? (
                                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                            ) : null}
                            {started ? "Reiniciar" : "Iniciar asistente"}
                        </button>
                    </div>

                    {started && (
                        <div className="space-y-2 max-h-72 overflow-y-auto">
                            {messages.map((m, i) => (
                                <div
                                    key={i}
                                    className={`text-sm rounded-lg px-3 py-2 whitespace-pre-wrap ${
                                        m.role === "assistant"
                                            ? "bg-muted/50 text-foreground"
                                            : "bg-primary/10 text-foreground ml-8"
                                    }`}
                                >
                                    {m.content}
                                </div>
                            ))}
                            {loading && (
                                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                    <Loader2 className="w-3.5 h-3.5 animate-spin" /> Pensando…
                                </div>
                            )}
                        </div>
                    )}

                    {started && !contract && (
                        <div className="flex items-center gap-2">
                            <input
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                onKeyDown={(e) => { if (e.key === "Enter") onSend(); }}
                                placeholder="Escribe tu respuesta…"
                                disabled={loading}
                                className="flex-1 bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:border-primary"
                            />
                            <button
                                onClick={onSend}
                                disabled={loading || !input.trim()}
                                className="p-2 rounded-lg bg-primary text-foreground disabled:opacity-50"
                            >
                                <Send className="w-4 h-4" />
                            </button>
                        </div>
                    )}

                    {contract && (
                        <div className="space-y-3">
                            <pre className="text-xs text-foreground bg-background border border-border rounded-lg p-3 max-h-80 overflow-auto whitespace-pre-wrap">
                                {contract}
                            </pre>
                            <button
                                onClick={save}
                                disabled={saving || saved}
                                className="inline-flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-500 text-foreground text-sm px-4 py-2 rounded-lg font-medium disabled:opacity-50"
                            >
                                {saved ? (
                                    <CheckCircle2 className="w-4 h-4" />
                                ) : saving ? (
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                ) : (
                                    <Save className="w-4 h-4" />
                                )}
                                {saved ? "Guardado en Documentos" : "Guardar en Documentos"}
                            </button>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
