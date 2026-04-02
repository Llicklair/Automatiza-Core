"use client";

import { useCallback, useRef, useEffect } from "react";
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
        ALLOW_DATA_ATTR: false,  // Solo permitir data-erp-action/data-payload/data-confirm
        ADD_ATTR: ["data-erp-action", "data-payload", "data-confirm"],
    });
}

/**
 * Map de acciones ERP permitidas → handlers.
 * Cada acción debe validar su payload antes de ejecutar.
 */
const ERP_ACTIONS: Record<string, (payload: Record<string, unknown>) => Promise<string>> = {
    "create-task": async (payload) => {
        const intent = String(payload.intent || "");
        if (!intent) throw new Error("Falta intent para crear tarea");
        const task = await api.tasks.create({ intent, domain: String(payload.domain || "") });
        return `Tarea creada: ${task.id}`;
    },
    "view-invoice": async (payload) => {
        const id = String(payload.id || "");
        if (!id) throw new Error("Falta ID de factura");
        window.location.href = `/ventas/facturas/${id}`;
        return "Navegando a factura...";
    },
    "view-employee": async (payload) => {
        const id = String(payload.id || "");
        if (!id) throw new Error("Falta ID de empleado");
        window.location.href = `/rrhh/empleados/${id}`;
        return "Navegando a empleado...";
    },
    "navigate": async (payload) => {
        const href = String(payload.href || "");
        if (!href.startsWith("/")) throw new Error("Ruta inválida");
        window.location.href = href;
        return `Navegando a ${href}...`;
    },
};

type GenerativeUIProps = {
    html: string;
    className?: string;
};

/**
 * Componente que renderiza HTML generado por IA de forma segura.
 *
 * - Sanitiza con DOMPurify (whitelist estricta)
 * - Intercepta clicks en elementos con data-erp-action
 * - Valida payload JSON antes de ejecutar
 * - Muestra confirmación si data-confirm está presente
 */
export default function GenerativeUI({ html, className = "" }: GenerativeUIProps) {
    const containerRef = useRef<HTMLDivElement>(null);
    const showToast = useToastStore((s) => s.show);

    const handleAction = useCallback(async (action: string, payloadStr: string, confirmMsg?: string) => {
        // Parse payload
        let payload: Record<string, unknown> = {};
        if (payloadStr) {
            try {
                payload = JSON.parse(payloadStr);
            } catch {
                showToast("Payload inválido en acción ERP", "error");
                return;
            }
        }

        // Confirmation dialog
        if (confirmMsg) {
            const confirmed = window.confirm(confirmMsg);
            if (!confirmed) return;
        }

        // Find and execute handler
        const handler = ERP_ACTIONS[action];
        if (!handler) {
            showToast(`Acción ERP desconocida: ${action}`, "error");
            return;
        }

        try {
            const result = await handler(payload);
            showToast(result, "success");
        } catch (e: any) {
            showToast(e.message || "Error ejecutando acción", "error");
        }
    }, [showToast]);

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
        <div
            ref={containerRef}
            className={`generative-ui prose prose-invert prose-sm max-w-none ${className}`}
            dangerouslySetInnerHTML={{ __html: sanitized }}
        />
    );
}

export { sanitizeHTML, ERP_ACTIONS };
