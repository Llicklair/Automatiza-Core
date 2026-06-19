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
        setStoredLocale("es");
        expect(getStoredLocale()).toBe("es");
    });

    it("getStoredLocale ignora valores no soportados (fallback es)", () => {
        document.cookie = "locale=invalid; Path=/";
        expect(getStoredLocale()).toBe("es");
    });

    it("getStoredLocale ignora locales retirados del selector (fallback es)", () => {
        // Cookie heredada de cuando ca/eu/gl/en se ofrecían en la UI.
        document.cookie = "locale=ca; Path=/";
        expect(getStoredLocale()).toBe("es");
    });

    it("setStoredLocale acepta todos los locales soportados", () => {
        for (const opt of SUPPORTED_LOCALES) {
            setStoredLocale(opt.code);
            expect(getStoredLocale()).toBe(opt.code);
        }
    });

    it("SUPPORTED_LOCALES ofrece es+en; ca/eu/gl quedan fuera hasta tener traducciones reales", () => {
        const codes = SUPPORTED_LOCALES.map((l) => l.code);
        expect(codes).toEqual(["es", "en"]);
    });

    it("cada locale tiene nombre nativo no vacío", () => {
        for (const opt of SUPPORTED_LOCALES) {
            expect(opt.native.length).toBeGreaterThan(0);
            expect(opt.label.length).toBeGreaterThan(0);
        }
    });
});
