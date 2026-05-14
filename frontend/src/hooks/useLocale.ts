/**
 * I18N.SEL — preferencia de idioma persistida en cookie.
 *
 * Idiomas soportados: es (default), ca, eu, gl, en. Las traducciones
 * CA/EU/GL son stubs hasta I18N.TR (agencia entrega traducciones reales).
 *
 * El cookie se lee server-side en `i18n/request.ts` para SSR consistente.
 * Cambiar el idioma requiere refresh — Next.js no permite cambiar el
 * provider de mensajes en runtime sin reset del tree.
 */
"use client";

export type AppLocale = "es" | "ca" | "eu" | "gl" | "en";

export const SUPPORTED_LOCALES: { code: AppLocale; label: string; native: string }[] = [
    { code: "es", label: "Español", native: "Español" },
    { code: "ca", label: "Catalán", native: "Català" },
    { code: "eu", label: "Euskera", native: "Euskara" },
    { code: "gl", label: "Gallego", native: "Galego" },
    { code: "en", label: "Inglés", native: "English" },
];

const COOKIE = "locale";
const ONE_YEAR_SECONDS = 60 * 60 * 24 * 365;

export function getStoredLocale(): AppLocale {
    if (typeof document === "undefined") return "es";
    const match = document.cookie.match(/(?:^|; )locale=([^;]+)/);
    const raw = match ? decodeURIComponent(match[1]) : "es";
    return (SUPPORTED_LOCALES.some((l) => l.code === raw) ? raw : "es") as AppLocale;
}

export function setStoredLocale(locale: AppLocale): void {
    if (typeof document === "undefined") return;
    document.cookie = `${COOKIE}=${encodeURIComponent(locale)}; Max-Age=${ONE_YEAR_SECONDS}; Path=/; SameSite=Lax`;
}
