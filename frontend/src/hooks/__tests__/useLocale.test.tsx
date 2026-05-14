/**
 * Tests del hook I18N.SEL.
 */
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import {
    SUPPORTED_LOCALES,
    getStoredLocale,
    setStoredLocale,
} from "../useLocale";

function clearLocaleCookie() {
    document.cookie = "locale=; Max-Age=0; Path=/";
}

describe("useLocale helpers", () => {
    beforeEach(() => clearLocaleCookie());
    afterEach(() => clearLocaleCookie());

    it("getStoredLocale devuelve 'es' por defecto", () => {
        expect(getStoredLocale()).toBe("es");
    });

    it("setStoredLocale persiste y getStoredLocale lo lee", () => {
        setStoredLocale("ca");
        expect(getStoredLocale()).toBe("ca");
    });

    it("getStoredLocale ignora valores no soportados (fallback es)", () => {
        document.cookie = "locale=invalid; Path=/";
        expect(getStoredLocale()).toBe("es");
    });

    it("setStoredLocale acepta todos los locales soportados", () => {
        for (const opt of SUPPORTED_LOCALES) {
            setStoredLocale(opt.code);
            expect(getStoredLocale()).toBe(opt.code);
        }
    });

    it("SUPPORTED_LOCALES incluye co-oficiales españolas + en", () => {
        const codes = SUPPORTED_LOCALES.map((l) => l.code);
        expect(codes).toContain("es");
        expect(codes).toContain("ca");
        expect(codes).toContain("eu");
        expect(codes).toContain("gl");
        expect(codes).toContain("en");
    });

    it("cada locale tiene nombre nativo no vacío", () => {
        for (const opt of SUPPORTED_LOCALES) {
            expect(opt.native.length).toBeGreaterThan(0);
            expect(opt.label.length).toBeGreaterThan(0);
        }
    });
});
