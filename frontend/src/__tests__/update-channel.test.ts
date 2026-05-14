/**
 * Tests del gestor de canal de actualización (DIS.UPD).
 *
 * Módulo en `desktop/lib/update-channel.js` (Node puro). Se testea desde
 * el frontend reusando vitest. Mock de electron-store + autoUpdater.
 */
import { describe, expect, it, vi } from "vitest";

// eslint-disable-next-line @typescript-eslint/no-var-requires
const {
    createUpdateChannelManager,
    SUPPORTED_CHANNELS,
    DEFAULT_CHANNEL,
    normalize,
} = require("../../../desktop/lib/update-channel.js");

function makeStore(initial: Record<string, unknown> = {}) {
    const data: Record<string, unknown> = { ...initial };
    return {
        get: (k: string) => data[k],
        set: (k: string, v: unknown) => { data[k] = v; },
        _data: data,
    };
}

function makeAutoUpdater() {
    return { channel: "latest", allowPrerelease: false };
}

describe("update-channel", () => {
    describe("normalize", () => {
        it("acepta stable / beta", () => {
            expect(normalize("stable")).toBe("stable");
            expect(normalize("beta")).toBe("beta");
        });

        it("normaliza case y whitespace", () => {
            expect(normalize("BETA")).toBe("beta");
            expect(normalize("  Stable  ")).toBe("stable");
        });

        it("fallback a stable con input inválido", () => {
            expect(normalize("alpha")).toBe(DEFAULT_CHANNEL);
            expect(normalize("")).toBe(DEFAULT_CHANNEL);
            expect(normalize(undefined as any)).toBe(DEFAULT_CHANNEL);
            expect(normalize(null as any)).toBe(DEFAULT_CHANNEL);
        });
    });

    describe("constantes", () => {
        it("exporta los canales esperados", () => {
            expect(SUPPORTED_CHANNELS).toEqual(["stable", "beta"]);
            expect(DEFAULT_CHANNEL).toBe("stable");
        });
    });

    describe("createUpdateChannelManager", () => {
        it("rechaza store sin get/set", () => {
            expect(() =>
                createUpdateChannelManager({ store: {}, autoUpdater: {} }),
            ).toThrow(/get\(\)/);
        });

        it("rechaza autoUpdater ausente", () => {
            expect(() =>
                createUpdateChannelManager({ store: makeStore(), autoUpdater: null }),
            ).toThrow(/autoUpdater/);
        });

        it("getChannel devuelve stable por defecto", () => {
            const mgr = createUpdateChannelManager({
                store: makeStore(), autoUpdater: makeAutoUpdater(),
            });
            expect(mgr.getChannel()).toBe("stable");
        });

        it("setChannel persiste en store y aplica al autoUpdater", () => {
            const store = makeStore();
            const au = makeAutoUpdater();
            const mgr = createUpdateChannelManager({ store, autoUpdater: au });

            mgr.setChannel("beta");
            expect(store.get("update.channel")).toBe("beta");
            expect(au.channel).toBe("beta");
            expect(au.allowPrerelease).toBe(true);
        });

        it("setChannel stable resetea allowPrerelease", () => {
            const au = makeAutoUpdater();
            au.channel = "beta";
            au.allowPrerelease = true;
            const mgr = createUpdateChannelManager({ store: makeStore(), autoUpdater: au });

            mgr.setChannel("stable");
            expect(au.channel).toBe("latest");
            expect(au.allowPrerelease).toBe(false);
        });

        it("setChannel sanea inputs raros a stable", () => {
            const au = makeAutoUpdater();
            const mgr = createUpdateChannelManager({ store: makeStore(), autoUpdater: au });
            const result = mgr.setChannel("alpha");
            expect(result).toBe("stable");
            expect(au.channel).toBe("latest");
        });

        it("apply() sin argumento usa el canal persistido", () => {
            const store = makeStore({ "update.channel": "beta" });
            const au = makeAutoUpdater();
            const mgr = createUpdateChannelManager({ store, autoUpdater: au });

            mgr.apply();
            expect(au.channel).toBe("beta");
            expect(au.allowPrerelease).toBe(true);
        });

        it("logger callback recibe el nuevo canal", () => {
            const logger = vi.fn();
            const mgr = createUpdateChannelManager({
                store: makeStore(), autoUpdater: makeAutoUpdater(), logger,
            });
            mgr.setChannel("beta");
            expect(logger).toHaveBeenCalledWith("update-channel: beta");
        });

        it("supported() devuelve copia inmutable", () => {
            const mgr = createUpdateChannelManager({
                store: makeStore(), autoUpdater: makeAutoUpdater(),
            });
            const list = mgr.supported();
            list.push("hacked");
            expect(mgr.supported()).toEqual(["stable", "beta"]);
        });
    });
});
