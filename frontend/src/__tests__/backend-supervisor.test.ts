/**
 * Tests del supervisor de backend (DIS.SVC).
 *
 * El módulo vive en `desktop/lib/backend-supervisor.js` y es Node puro
 * (sin dependencias de Electron), por lo que lo importamos vía path
 * relativo al monorepo para testearlo con la suite de Vitest del frontend.
 */
import { EventEmitter } from "node:events";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// eslint-disable-next-line @typescript-eslint/no-var-requires
const { createBackendSupervisor } = require("../../../desktop/lib/backend-supervisor.js") as {
    createBackendSupervisor: (opts: any) => any;
};

function fakeChild() {
    const ee: any = new EventEmitter();
    ee.kill = vi.fn(() => { ee.killed = true; });
    ee.killed = false;
    ee.pid = 42;
    return ee;
}

describe("backend-supervisor", () => {
    beforeEach(() => vi.useFakeTimers());
    afterEach(() => vi.useRealTimers());

    it("start invoca spawn una vez", () => {
        const spawn = vi.fn(fakeChild);
        const s = createBackendSupervisor({ spawn });
        s.start();
        expect(spawn).toHaveBeenCalledTimes(1);
    });

    it("inspect refleja estado tras start", () => {
        const spawn = vi.fn(fakeChild);
        const s = createBackendSupervisor({ spawn });
        s.start();
        const state = s.inspect();
        expect(state.running).toBe(true);
        expect(state.shouldRun).toBe(true);
        expect(state.pid).toBe(42);
    });

    it("reinicia tras crash con backoff", () => {
        const procs = [fakeChild(), fakeChild(), fakeChild()];
        let idx = 0;
        const spawn = vi.fn(() => procs[idx++]);
        const onRestart = vi.fn();
        const s = createBackendSupervisor({
            spawn, onRestart, backoffMs: [100, 200, 400], maxAttempts: 5,
        });
        s.start();
        expect(spawn).toHaveBeenCalledTimes(1);

        procs[0].emit("exit", 1, null);
        expect(onRestart).toHaveBeenCalledWith(
            expect.objectContaining({ attempt: 1, exitCode: 1, delayMs: 100 }),
        );

        vi.advanceTimersByTime(100);
        expect(spawn).toHaveBeenCalledTimes(2);
    });

    it("backoff es exponencial creciente", () => {
        const procs = Array.from({ length: 5 }, () => fakeChild());
        let idx = 0;
        const spawn = vi.fn(() => procs[idx++]);
        const onRestart = vi.fn();
        const backoffMs = [50, 100, 200];
        const s = createBackendSupervisor({ spawn, onRestart, backoffMs, maxAttempts: 5 });
        s.start();

        procs[0].emit("exit", 1);
        vi.advanceTimersByTime(50);
        procs[1].emit("exit", 1);
        vi.advanceTimersByTime(100);
        procs[2].emit("exit", 1);
        vi.advanceTimersByTime(200);

        const delays = onRestart.mock.calls.map((c) => c[0].delayMs);
        expect(delays).toEqual([50, 100, 200]);
    });

    it("se rinde tras maxAttempts y dispara onGiveUp", () => {
        const procs = Array.from({ length: 10 }, () => fakeChild());
        let idx = 0;
        const spawn = vi.fn(() => procs[idx++]);
        const onGiveUp = vi.fn();
        const s = createBackendSupervisor({
            spawn, onGiveUp, backoffMs: [10], maxAttempts: 2,
        });
        s.start();

        procs[0].emit("exit", 1);
        vi.advanceTimersByTime(10);
        procs[1].emit("exit", 1);
        vi.advanceTimersByTime(10);
        procs[2].emit("exit", 1);

        expect(onGiveUp).toHaveBeenCalledWith({ name: "backend", attempts: 3 });
        expect(s.inspect().shouldRun).toBe(false);
    });

    it("stop() no dispara restart aunque el child emita exit después", () => {
        const proc = fakeChild();
        const spawn = vi.fn(() => proc);
        const onRestart = vi.fn();
        const s = createBackendSupervisor({ spawn, onRestart });
        s.start();
        s.stop();

        proc.emit("exit", 1);
        vi.advanceTimersByTime(60_000);

        expect(spawn).toHaveBeenCalledTimes(1);
        expect(onRestart).not.toHaveBeenCalled();
    });

    it("stop() mata el child process", () => {
        const proc = fakeChild();
        const s = createBackendSupervisor({ spawn: () => proc });
        s.start();
        s.stop();
        expect(proc.kill).toHaveBeenCalled();
    });

    it("resetAttempts limpia el contador", () => {
        const procs = [fakeChild(), fakeChild()];
        let idx = 0;
        const s = createBackendSupervisor({
            spawn: () => procs[idx++], backoffMs: [10], maxAttempts: 5,
        });
        s.start();
        procs[0].emit("exit", 1);
        expect(s.inspect().currentAttempt).toBe(1);
        s.resetAttempts();
        expect(s.inspect().currentAttempt).toBe(0);
    });

    it("start es idempotente (no spawn dobles)", () => {
        const spawn = vi.fn(fakeChild);
        const s = createBackendSupervisor({ spawn });
        s.start();
        s.start();
        expect(spawn).toHaveBeenCalledTimes(1);
    });

    it("throw si spawn no es función", () => {
        expect(() => createBackendSupervisor({ spawn: null })).toThrow(/función/);
    });
});
