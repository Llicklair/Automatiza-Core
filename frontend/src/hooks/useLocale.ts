/**
 * I18N.SEL — preferencia de idioma persistida en cookie.
 *
 * Se ofrecen "es" y "en" (traducción completa, parity es/en al 100%).
 * ca/eu/gl siguen siendo stubs incompletos → la UI no los lista hasta
 * tener traducción real. Al reactivar un idioma: añadirlo aquí, a
 * AppLocale y a `i18n/request.ts`.
 *
 * El cookie se lee server-side en `i18n/request.ts` para SSR consistente.
 * Cambiar el idioma requiere refresh — Next.js no permite cambiar el
 * provider de mensajes en runtime sin reset del tree.
 */
"use client";

export type AppLocale = "es" | "en";

export const SUPPORTED_LOCALES: { code: AppLocale; label: string; native: string }[] = [
    { code: "es", label: "Español", native: "Español" },
    { code: "en", label: "Inglés", native: "English" },
    // Pendientes de traducción real (I18N.TR) — no ofrecer hasta entonces:
    // { code: "ca", label: "Catalán", native: "Català" },
    // { code: "eu", label: "Euskera", native: "Euskara" },
    // { code: "gl", label: "Gallego", native: "Galego" },
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
