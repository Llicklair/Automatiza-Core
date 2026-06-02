import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock del store de toast: surfaceIfConnectivity hace un import dinámico de
// "@/stores/toast" y llama useToastStore.getState().show(...). El spy es estable
// entre vi.resetModules() porque vive fuera del grafo de módulos reseteado.
const showSpy = vi.fn();
vi.mock("@/stores/toast", () => ({
  useToastStore: { getState: () => ({ show: showSpy }) },
}));

// Cada test reimporta errors.ts en limpio para resetear el throttle de 30s
// (variable de módulo _lastDegradationToast).
async function freshErrors() {
  vi.resetModules();
  return import("@/lib/api/errors");
}

describe("surfaceIfConnectivity", () => {
  beforeEach(() => {
    showSpy.mockClear();
  });

  it("devuelve false y no muestra toast para errores no de conectividad", async () => {
    const { surfaceIfConnectivity, ApiError } = await freshErrors();
    expect(surfaceIfConnectivity(new ApiError(400, "bad request"))).toBe(false);
    expect(surfaceIfConnectivity(new Error("boom"))).toBe(false);
    expect(surfaceIfConnectivity(null)).toBe(false);
    await Promise.resolve();
    expect(showSpy).not.toHaveBeenCalled();
  });

  it("devuelve true y muestra el aviso de degradación ante un error de conectividad", async () => {
    const { surfaceIfConnectivity, ApiError, AI_DEGRADATION_MESSAGE } = await freshErrors();
    expect(surfaceIfConnectivity(new ApiError(503, "service unavailable"))).toBe(true);
    await vi.waitFor(() =>
      expect(showSpy).toHaveBeenCalledWith(AI_DEGRADATION_MESSAGE, "warning"),
    );
    expect(showSpy).toHaveBeenCalledTimes(1);
  });

  it("detecta network_error y los status 0/502/504", async () => {
    const { surfaceIfConnectivity, ApiError } = await freshErrors();
    expect(surfaceIfConnectivity(new ApiError(0, "x", undefined, "network_error"))).toBe(true);
    expect(surfaceIfConnectivity(new ApiError(502, "bad gateway"))).toBe(true);
    expect(surfaceIfConnectivity(new ApiError(504, "gateway timeout"))).toBe(true);
  });

  it("throttle: varios errores de conectividad seguidos muestran un solo toast", async () => {
    const { surfaceIfConnectivity, ApiError } = await freshErrors();
    surfaceIfConnectivity(new ApiError(503, "down"));
    surfaceIfConnectivity(new ApiError(503, "down otra vez"));
    surfaceIfConnectivity(new ApiError(504, "y otra"));
    await vi.waitFor(() => expect(showSpy).toHaveBeenCalled());
    expect(showSpy).toHaveBeenCalledTimes(1);
  });
});
