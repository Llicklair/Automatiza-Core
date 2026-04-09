"use client";

import { useCallback, useRef, useEffect, useState } from "react";
import DOMPurify from "dompurify";
import { api } from "@/lib/api";
import { useToastStore } from "@/stores/toast";

/**
 * Whitelist estricta de tags y atributos permitidos en HTML generado por IA.
 * Solo elementos de presentación — nada ejecutable.
 */
const ALLOWED_TAGS = [
    "div", "span", "p", "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li", "table", "thead", "tbody", "tr", "th", "td",
    "strong", "em", "b", "i", "u", "br", "hr", "a", "img",
    "code", "pre", "blockquote", "small", "sup", "sub",
    "button", "input", "label", "select", "option",
];

const ALLOWED_ATTRS = [
    "class", "style", "href", "src", "alt", "title", "width", "height",
    "colspan", "rowspan", "type", "value", "placeholder", "disabled", "readonly",
    // ERP action attributes — intercepted by our handler
    "data-erp-action", "data-payload", "data-confirm",
];

/**
 * Sanitiza HTML generado por IA con DOMPurify.
 * Elimina scripts, event handlers, iframes, etc.
 */
function sanitizeHTML(dirty: string): string {
    return DOMPurify.sanitize(dirty, {
        ALLOWED_TAGS,
        ALLOWED_ATTR: ALLOWED_ATTRS,
        ALLOW_DATA_ATTR: true,
    });
}

/**
 * Resolve domain + intent from an ERP action + payload.
 */
function resolveAction(action: string, payload: Record<string, unknown>): { domain: string; intent: string } | { navigate: string } {
    switch (action) {
        case "create-task":
            return {
                domain: String(payload.domain || "general").trim(),
                intent: String(payload.intent || ""),
            };
        case "view-invoice":
            return {
                domain: "billing",
                intent: payload.id ? `Mostrar detalle de la factura ${payload.id}` : "Listar facturas recientes",
            };
        case "view-employee":
            return {
                domain: "hr",
                intent: payload.id ? `Mostrar detalle del empleado ${payload.id}` : "Listar empleados",
            };
        case "navigate": {
            const href = String(payload.href || "");
            if (href.startsWith("/")) return { navigate: href };
            return { domain: "general", intent: `Navegar a ${href}` };
        }
        default:
            // Generic: send action description as task
            return {
                domain: String(payload.domain || "general"),
                intent: payload.intent ? String(payload.intent) : `${action}: ${JSON.stringify(payload)}`,
            };
    }
}

/** Poll a task until it completes or fails. */
async function pollTask(taskId: string, maxAttempts = 30): Promise<string> {
    for (let i = 0; i < maxAttempts; i++) {
        await new Promise((r) => setTimeout(r, 1000));
        const task = await api.tasks.get(taskId);
        if (task.status === "done" || task.status === "completed") {
            if (task.output_data) {
                return typeof task.output_data === "string"
                    ? task.output_data
                    : JSON.stringify(task.output_data, null, 2);
            }
            // Fallback: check last agent result
            const lastResult = task.agent_results?.at(-1);
            if (lastResult?.output_data) {
                return typeof lastResult.output_data === "string"
                    ? lastResult.output_data
                    : JSON.stringify(lastResult.output_data, null, 2);
            }
            return "Tarea completada.";
        }
        if (task.status === "error" || task.status === "failed") {
            throw new Error(task.error_message || "La tarea falló.");
        }
    }
    throw new Error("Timeout: la tarea tardó demasiado.");
}

type GenerativeUIProps = {
    html: string;
    className?: string;
    /** Called with a follow-up prompt to regenerate the UI with fresh data. */
    onRefresh?: (prompt: string) => Promise<void>;
};

/**
 * Componente que renderiza HTML generado por IA de forma segura.
 *
 * - Sanitiza con DOMPurify (whitelist estricta)
 * - Intercepta clicks en elementos con data-erp-action
 * - Valida payload JSON antes de ejecutar
 * - Muestra confirmación si data-confirm está presente
 */
export default function GenerativeUI({ html, className = "", onRefresh }: GenerativeUIProps) {
    const containerRef = useRef<HTMLDivElement>(null);
    const showToast = useToastStore((s) => s.show);
    const [loading, setLoading] = useState(false);

    const handleAction = useCallback(async (action: string, payloadStr: string, confirmMsg?: string) => {
        let payload: Record<string, unknown> = {};
        if (payloadStr) {
            try {
                payload = JSON.parse(payloadStr);
            } catch {
                showToast("Payload inválido en acción ERP", "error");
                return;
            }
        }

        if (confirmMsg && !window.confirm(confirmMsg)) return;

        const normalized = action.replace(/_/g, "-");
        const resolved = resolveAction(normalized, payload);

        // Navigate actions go directly
        if ("navigate" in resolved) {
            window.location.href = resolved.navigate;
            return;
        }

        if (!resolved.intent) {
            showToast("Falta descripción para la acción", "error");
            return;
        }

        setLoading(true);
        try {
            // Create task and wait for result
            const task = await api.tasks.create(resolved.domain, resolved.intent);
            const result = await pollTask(task.id);

            // If we have an onRefresh callback, regenerate the UI with the new data
            if (onRefresh) {
                await onRefresh(
                    `Actualiza el panel con estos datos reales obtenidos del ERP:\n\n${result}`
                );
            } else {
                showToast("Datos obtenidos correctamente", "success");
            }
        } catch (e: any) {
            showToast(e.message || "Error ejecutando acción", "error");
        } finally {
            setLoading(false);
        }
    }, [showToast, onRefresh]);

    // Attach click interceptor
    useEffect(() => {
        const container = containerRef.current;
        if (!container) return;

        const onClick = (e: MouseEvent) => {
            const target = (e.target as HTMLElement).closest("[data-erp-action]") as HTMLElement | null;
            if (!target) return;

            e.preventDefault();
            e.stopPropagation();

            const action = target.getAttribute("data-erp-action") || "";
            const payload = target.getAttribute("data-payload") || "{}";
            const confirm = target.getAttribute("data-confirm") || undefined;

            handleAction(action, payload, confirm);
        };

        container.addEventListener("click", onClick);
        return () => container.removeEventListener("click", onClick);
    }, [handleAction]);

    const sanitized = sanitizeHTML(html);

    return (
        <div className={`generative-ui ${className} relative`}>
            {loading && (
                <div className="absolute inset-0 z-10 flex items-center justify-center bg-background/70 rounded-lg backdrop-blur-sm">
                    <div className="flex items-center gap-3 text-sm text-muted-foreground">
                        <span className="inline-block w-4 h-4 border-2 border-violet-400 border-t-transparent rounded-full animate-spin" />
                        Actualizando panel con datos reales…
                    </div>
                </div>
            )}
            <div
                ref={containerRef}
                className="prose prose-invert prose-sm max-w-none"
                dangerouslySetInnerHTML={{ __html: sanitized }}
            />
        </div>
    );
}

export { sanitizeHTML };
