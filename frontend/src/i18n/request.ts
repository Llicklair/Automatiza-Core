import { cookies } from "next/headers";
import { getRequestConfig } from "next-intl/server";

const SUPPORTED_LOCALES = ["es", "ca", "eu", "gl", "en"] as const;
type SupportedLocale = (typeof SUPPORTED_LOCALES)[number];
const DEFAULT_LOCALE: SupportedLocale = "es";

function _resolveLocale(raw: string | undefined): SupportedLocale {
    if (!raw) return DEFAULT_LOCALE;
    return (SUPPORTED_LOCALES as readonly string[]).includes(raw)
        ? (raw as SupportedLocale)
        : DEFAULT_LOCALE;
}

export default getRequestConfig(async () => {
    let locale: SupportedLocale = DEFAULT_LOCALE;
    try {
        const cookieStore = await cookies();
        locale = _resolveLocale(cookieStore.get("locale")?.value);
    } catch {
        // En contexto sin request (build, edge), nos quedamos con default.
    }
    return {
        locale,
        messages: (await import(`../messages/${locale}.json`)).default,
    };
});
