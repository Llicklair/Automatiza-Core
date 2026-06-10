/**
 * Tests del hook compartido `usePolling` (auditoría UIX #10).
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, renderHook } from "@testing-library/react";
import { usePolling } from "../usePolling";

function setVisibility(state: "visible" | "hidden") {
    Object.defineProperty(document, "visibilityState", {
        configurable: true,
        get: () => state,
    });
    document.dispatchEvent(new Event("visibilitychange"));
}

describe("usePolling", () => {
    beforeEach(() => {
        vi.useFakeTimers();
        setVisibility("visible");
    });

    afterEach(() => {
        cleanup();
        vi.useRealTimers();
    });

    it("dispara fn en cada intervalo (sin carga inicial)", () => {
        const fn = vi.fn();
        renderHook(() => usePolling(fn, 1000));
        expect(fn).not.toHaveBeenCalled();
        vi.advanceTimersByTime(3000);
        expect(fn).toHaveBeenCalledTimes(3);
    });

    it("no programa nada con enabled=false", () => {
        const fn = vi.fn();
        renderHook(() => usePolling(fn, 1000, { enabled: false }));
        vi.advanceTimersByTime(5000);
        expect(fn).not.toHaveBeenCalled();
    });

    it("pausa al ocultar la pestaña y hace catch-up al volver", () => {
        const fn = vi.fn();
        renderHook(() => usePolling(fn, 1000));

        setVisibility("hidden");
        vi.advanceTimersByTime(5000);
        expect(fn).not.toHaveBeenCalled();

        setVisibility("visible");
        expect(fn).toHaveBeenCalledTimes(1); // catch-up inmediato
        vi.advanceTimersByTime(2000);
        expect(fn).toHaveBeenCalledTimes(3); // intervalo reanudado
    });

    it("pauseWhenHidden=false sigue sondeando en pestaña oculta", () => {
        const fn = vi.fn();
        renderHook(() => usePolling(fn, 1000, { pauseWhenHidden: false }));
        setVisibility("hidden");
        vi.advanceTimersByTime(3000);
        expect(fn).toHaveBeenCalledTimes(3);
    });

    it("usa siempre la última closure de fn sin reiniciar el intervalo", () => {
        const first = vi.fn();
        const second = vi.fn();
        const { rerender } = renderHook(({ cb }) => usePolling(cb, 1000), {
            initialProps: { cb: first },
        });
        vi.advanceTimersByTime(1000);
        expect(first).toHaveBeenCalledTimes(1);

        rerender({ cb: second });
        vi.advanceTimersByTime(1000);
        expect(first).toHaveBeenCalledTimes(1);
        expect(second).toHaveBeenCalledTimes(1);
    });

    it("cambiar intervalMs reinicia el intervalo con el nuevo valor", () => {
        const fn = vi.fn();
        const { rerender } = renderHook(({ ms }) => usePolling(fn, ms), {
            initialProps: { ms: 1000 },
        });
        rerender({ ms: 5000 });
        vi.advanceTimersByTime(4000);
        expect(fn).not.toHaveBeenCalled();
        vi.advanceTimersByTime(1000);
        expect(fn).toHaveBeenCalledTimes(1);
    });

    it("limpia el intervalo al desmontar", () => {
        const fn = vi.fn();
        const { unmount } = renderHook(() => usePolling(fn, 1000));
        unmount();
        vi.advanceTimersByTime(5000);
        expect(fn).not.toHaveBeenCalled();
    });
});
