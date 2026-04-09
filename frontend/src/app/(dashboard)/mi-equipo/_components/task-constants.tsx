import React from "react";
import { Clock, Bot, Loader2, AlertCircle, CheckCircle2, X } from "lucide-react";
import type { Task } from "@/lib/api";

export const STATUS_COLOR: Record<string, string> = {
    pending: "text-muted-foreground bg-muted border-border",
    planning: "text-blue-400 bg-blue-500/10 border-blue-500/20",
    executing: "text-primary bg-primary/10 border-primary/20",
    awaiting_approval: "text-amber-400 bg-amber-500/10 border-amber-500/20",
    done: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
    failed: "text-red-400 bg-red-500/10 border-red-500/20",
    cancelled: "text-muted-foreground bg-accent border-border",
};

export const STATUS_LABEL: Record<string, string> = {
    pending: "Pendiente",
    planning: "Planificando",
    executing: "Ejecutando",
    awaiting_approval: "Espera aprobación",
    done: "Completada",
    failed: "Fallida",
    cancelled: "Cancelada",
};

export const STATUS_ICON: Record<string, React.ReactNode> = {
    pending: <Clock className="w-3 h-3" />,
    planning: <Bot className="w-3 h-3" />,
    executing: <Loader2 className="w-3 h-3 animate-spin" />,
    awaiting_approval: <AlertCircle className="w-3 h-3" />,
    done: <CheckCircle2 className="w-3 h-3" />,
    failed: <X className="w-3 h-3" />,
    cancelled: <X className="w-3 h-3" />,
};

export const CHAT_OPTION = {
    value: "chat",
    label: "\u{1F4AC} Chat",
    desc: "Preguntas, dudas o consultas de estado",
};

export const COORDINATOR_OPTION = {
    value: "coordinator",
    label: "\u{1F9E0} Coordinador General",
    desc: "Tarea compleja puntual: coordina varios agentes en secuencia para darte un \u00fanico resultado",
};

export const DOMAIN_OPTIONS = [
    { value: "billing", label: "\u{1F4B0} Facturaci\u00f3n", desc: "Facturas, cobros, presupuestos" },
    { value: "documents", label: "\u{1F4C4} Documentos", desc: "OCR, an\u00e1lisis, clasificaci\u00f3n de documentos" },
    { value: "hr", label: "\u{1F465} RRHH", desc: "N\u00f3minas, empleados, gesti\u00f3n de personal" },
    { value: "compliance", label: "\u2696\uFE0F Asesor Fiscal", desc: "Obligaciones tributarias, BOE, alertas" },
    { value: "banking", label: "\u{1F3E6} Banca", desc: "Resumen bancario, movimientos, conciliaci\u00f3n" },
    { value: "crm", label: "\u{1F91D} CRM", desc: "Oportunidades, clientes, seguimiento comercial" },
    { value: "excel", label: "\u{1F4CA} Excel / Datos", desc: "Cruza tablas y elabora hojas de c\u00e1lculo" },
    { value: "email", label: "\u{1F4E7} Correos", desc: "Bandeja de entrada, responde y organiza" },
];

export const ALL_DOMAIN_OPTIONS = [CHAT_OPTION, COORDINATOR_OPTION, ...DOMAIN_OPTIONS];

export function getChatResponse(task: Task): string | null {
    if (!Array.isArray(task.agent_results)) return null;
    const results = task.agent_results as any[];
    // Buscar resumen conversacional o respuesta de chat
    for (let i = results.length - 1; i >= 0; i--) {
        const r = results[i];
        if ((r.agent === "chat" || r.agent === "summary") && r.output?.action === "chat_response" && r.output?.response) {
            return r.output.response;
        }
    }
    return null;
}
