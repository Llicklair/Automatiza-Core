/**
 * I18N.FMT — bind del locale activo sobre los helpers de `lib/format.ts`.
 *
 * Usa `useLocale()` de next-intl (el locale realmente servido por
 * `i18n/request.ts`), no la cookie directa, para SSR consistente.
 * En código no-React, usar `lib/format.ts` con `getStoredLocale()`.
 */
"use client";

import { useCallback } from "react";
import { useLocale } from "next-intl";
import type { AppLocale } from "@/hooks/useLocale";
import {
    formatCurrency,
    formatDate,
    formatDateTime,
    formatNumber,
    formatTime,
} from "@/lib/format";

export function useFormat() {
    const locale = useLocale() as AppLocale;

    return {
        locale,
        fmtCurrency: useCallback(
            (value: number, opts?: Intl.NumberFormatOptions) =>
                formatCurrency(value, locale, opts),
            [locale],
        ),
        fmtNumber: useCallback(
            (value: number, opts?: Intl.NumberFormatOptions) =>
                formatNumber(value, locale, opts),
            [locale],
        ),
        fmtDate: useCallback(
            (date: Date | string | number, opts?: Intl.DateTimeFormatOptions) =>
                formatDate(date, locale, opts),
            [locale],
        ),
        fmtDateTime: useCallback(
            (date: Date | string | number, opts?: Intl.DateTimeFormatOptions) =>
                formatDateTime(date, locale, opts),
            [locale],
        ),
        fmtTime: useCallback(
            (date: Date | string | number, opts?: Intl.DateTimeFormatOptions) =>
                formatTime(date, locale, opts),
            [locale],
        ),
    };
}
