"use client";

import { useCallback, useRef, useEffect, useState } from "react";
import DOMPurify from "dompurify";
import { api } from "@/lib/api";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";

// ─── Sanitization ─────────────────────────────────────────────────────────────

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
    "data-erp-action", "data-payload", "data-confirm",
];

export function sanitizeHTML(dirty: string): string {
    return DOMPurify.sanitize(dirty, {
        ALLOWED_TAGS,
        ALLOWED_ATTR: ALLOWED_ATTRS,
        ALLOW_DATA_ATTR: true,
    });
}

// ─── Action resolution ────────────────────────────────────────────────────────

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
            return {
                domain: String(payload.domain || "general"),
                intent: payload.intent ? String(payload.intent) : `${action}: ${JSON.stringify(payload)}`,
            };
    }
}

// ─── Task polling ─────────────────────────────────────────────────────────────

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

// ─── Hook ─────────────────────────────────────────────────────────────────────

interface UseGenerativeUIOptions {
    html: string;
    onRefresh?: (prompt: string) => Promise<void>;
}

export function useGenerativeUI({ html, onRefresh }: UseGenerativeUIOptions) {
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

        if (confirmMsg && !(await showConfirm(confirmMsg))) return;

        const normalized = action.replace(/_/g, "-");
        const resolved = resolveAction(normalized, payload);

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
            const task = await api.tasks.create(resolved.domain, resolved.intent);
            const result = await pollTask(task.id);
            if (onRefresh) {
                await onRefresh(`Actualiza el panel con estos datos reales obtenidos del ERP:\n\n${result}`);
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

    return { containerRef, loading, sanitized };
}
