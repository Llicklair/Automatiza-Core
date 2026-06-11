/**
 * I18N.STATIC — traductor síncrono para código no-React.
 *
 * `useTranslations` solo funciona en componentes; sitios como
 * `lib/api/errors.ts` (toasts emitidos desde el interceptor HTTP) necesitan
 * resolver mensajes sin hooks. Importa los mensajes estáticamente y resuelve
 * con la cookie de locale.
 *
 * Usar SOLO fuera de React; en componentes, siempre `useTranslations`.
 */
import es from "@/messages/es.json";
import en from "@/messages/en.json";
import { getStoredLocale } from "@/hooks/useLocale";

const MESSAGES: Record<string, unknown> = { es, en };

/** Resuelve una clave con puntos ("errors.aiDegraded"). Devuelve la clave si falta. */
export function tStatic(key: string): string {
    const tree = MESSAGES[getStoredLocale()] ?? es;
    let node: unknown = tree;
    for (const part of key.split(".")) {
        if (node && typeof node === "object" && part in (node as object)) {
            node = (node as Record<string, unknown>)[part];
        } else {
            return key;
        }
    }
    return typeof node === "string" ? node : key;
}
