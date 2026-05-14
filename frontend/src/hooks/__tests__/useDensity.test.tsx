/**
 * Tests del hook UI.DEN.
 */
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { act, cleanup, renderHook } from "@testing-library/react";
import { applyDensity, getStoredDensity, useDensity } from "../useDensity";

describe("useDensity", () => {
    beforeEach(() => {
        window.localStorage.clear();
        document.documentElement.removeAttribute("data-density");
    });

    afterEach(() => cleanup());

    it("default es comfortable cuando no hay valor en localStorage", () => {
        const { result } = renderHook(() => useDensity());
        expect(result.current.density).toBe("comfortable");
    });

    it("getStoredDensity devuelve comfortable por defecto", () => {
        expect(getStoredDensity()).toBe("comfortable");
    });

    it("getStoredDensity devuelve compact si está guardado", () => {
        window.localStorage.setItem("ui_density_v1", "compact");
        expect(getStoredDensity()).toBe("compact");
    });

    it("setDensity actualiza estado y localStorage", () => {
        const { result } = renderHook(() => useDensity());
        act(() => {
            result.current.setDensity("compact");
        });
        expect(result.current.density).toBe("compact");
        expect(window.localStorage.getItem("ui_density_v1")).toBe("compact");
    });

    it("setDensity aplica el atributo data-density en <html>", () => {
        const { result } = renderHook(() => useDensity());
        act(() => {
            result.current.setDensity("compact");
        });
        expect(document.documentElement.getAttribute("data-density")).toBe("compact");
    });

    it("applyDensity setea el atributo sin tocar localStorage", () => {
        applyDensity("compact");
        expect(document.documentElement.getAttribute("data-density")).toBe("compact");
        expect(window.localStorage.getItem("ui_density_v1")).toBeNull();
    });

    it("hidrata data-density al montar si había valor guardado", () => {
        window.localStorage.setItem("ui_density_v1", "compact");
        renderHook(() => useDensity());
        expect(document.documentElement.getAttribute("data-density")).toBe("compact");
    });
});
