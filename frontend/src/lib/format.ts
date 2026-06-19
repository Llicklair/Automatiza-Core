/**
 * I18N.FMT — helpers de formato locale-aware (migración i18n real, #1 fase 2).
 *
 * Funciones puras con locale explícito para servir tanto en React (vía
 * `hooks/useFormat.ts`) como fuera (con `getStoredLocale()`). Sustituyen a
 * los `Intl.NumberFormat("es-ES")` / `toLocaleDateString("es-ES")` inline.
 *
 * - La moneda es SIEMPRE EUR (clientes españoles); solo cambia la
 *   representación según el idioma de la UI.
 * - "en" mapea a en-GB deliberadamente: convenciones europeas
 *   (dd/mm/yyyy) coherentes con una pyme española, no en-US.
 */
import type { AppLocale } from "@/hooks/useLocale";

const INTL_LOCALE: Record<AppLocale, string> = {
    es: "es-ES",
    en: "en-GB",
};

function intlLocale(locale: AppLocale): string {
    return INTL_LOCALE[locale] ?? "es-ES";
}

export function formatCurrency(
    value: number,
    locale: AppLocale,
    opts?: Intl.NumberFormatOptions,
): string {
    return new Intl.NumberFormat(intlLocale(locale), {
        style: "currency",
        currency: "EUR",
        ...opts,
    }).format(value);
}

export function formatNumber(
    value: number,
    locale: AppLocale,
    opts?: Intl.NumberFormatOptions,
): string {
    return new Intl.NumberFormat(intlLocale(locale), opts).format(value);
}

export function formatDate(
    date: Date | string | number,
    locale: AppLocale,
    opts?: Intl.DateTimeFormatOptions,
): string {
    const d = date instanceof Date ? date : new Date(date);
    return d.toLocaleDateString(intlLocale(locale), opts);
}

export function formatDateTime(
    date: Date | string | number,
    locale: AppLocale,
    opts?: Intl.DateTimeFormatOptions,
): string {
    const d = date instanceof Date ? date : new Date(date);
    return d.toLocaleString(intlLocale(locale), opts);
}

export function formatTime(
    date: Date | string | number,
    locale: AppLocale,
    opts?: Intl.DateTimeFormatOptions,
): string {
    const d = date instanceof Date ? date : new Date(date);
    return d.toLocaleTimeString(intlLocale(locale), opts);
}
