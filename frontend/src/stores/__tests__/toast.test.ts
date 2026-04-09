import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { useToastStore, type ToastType } from "../toast";
import { act } from "@testing-library/react";

beforeEach(() => {
    vi.useFakeTimers();
    act(() => {
        useToastStore.setState({ toasts: [] });
    });
});

afterEach(() => {
    vi.useRealTimers();
});

describe("useToastStore", () => {
    it("starts with empty toasts array", () => {
        expect(useToastStore.getState().toasts).toEqual([]);
    });

    it("show() adds a toast with default type 'info'", () => {
        act(() => {
            useToastStore.getState().show("Hello");
        });

        const { toasts } = useToastStore.getState();
        expect(toasts).toHaveLength(1);
        expect(toasts[0].message).toBe("Hello");
        expect(toasts[0].type).toBe("info");
        expect(toasts[0].id).toBeTruthy();
    });

    it("show() adds a toast with a specified type", () => {
        act(() => {
            useToastStore.getState().show("Error occurred", "error");
        });

        const { toasts } = useToastStore.getState();
        expect(toasts).toHaveLength(1);
        expect(toasts[0].type).toBe("error");
    });

    it("success/error/info/warning shortcuts set correct type", () => {
        const types: ToastType[] = ["success", "error", "info", "warning"];

        for (const t of types) {
            act(() => {
                useToastStore.getState()[t](`msg-${t}`);
            });
        }

        const { toasts } = useToastStore.getState();
        expect(toasts).toHaveLength(4);
        types.forEach((t, i) => {
            expect(toasts[i].type).toBe(t);
            expect(toasts[i].message).toBe(`msg-${t}`);
        });
    });

    it("dismiss() removes a toast by id", () => {
        act(() => {
            useToastStore.getState().show("to dismiss");
        });

        const { toasts } = useToastStore.getState();
        const id = toasts[0].id;

        act(() => {
            useToastStore.getState().dismiss(id);
        });

        expect(useToastStore.getState().toasts).toHaveLength(0);
    });

    it("auto-dismisses toasts after 5000ms", () => {
        act(() => {
            useToastStore.getState().show("auto dismiss");
        });

        expect(useToastStore.getState().toasts).toHaveLength(1);

        act(() => {
            vi.advanceTimersByTime(5000);
        });

        expect(useToastStore.getState().toasts).toHaveLength(0);
    });

    it("does not auto-dismiss before 5000ms", () => {
        act(() => {
            useToastStore.getState().show("still here");
        });

        act(() => {
            vi.advanceTimersByTime(4999);
        });

        expect(useToastStore.getState().toasts).toHaveLength(1);
    });

    it("can add multiple toasts", () => {
        act(() => {
            useToastStore.getState().show("first");
            useToastStore.getState().show("second");
            useToastStore.getState().show("third");
        });

        expect(useToastStore.getState().toasts).toHaveLength(3);
    });
});
