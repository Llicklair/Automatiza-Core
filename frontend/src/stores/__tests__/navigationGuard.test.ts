import { describe, it, expect, beforeEach } from "vitest";
import { useNavigationGuard } from "../navigationGuard";
import { act } from "@testing-library/react";

beforeEach(() => {
    act(() => {
        useNavigationGuard.setState({ blocked: false, message: "" });
    });
});

describe("useNavigationGuard", () => {
    it("starts with blocked=false and empty message", () => {
        const state = useNavigationGuard.getState();
        expect(state.blocked).toBe(false);
        expect(state.message).toBe("");
    });

    it("setGuard(true) activates the guard", () => {
        act(() => {
            useNavigationGuard.getState().setGuard(true, "Unsaved changes");
        });

        const state = useNavigationGuard.getState();
        expect(state.blocked).toBe(true);
        expect(state.message).toBe("Unsaved changes");
    });

    it("setGuard(false) deactivates the guard", () => {
        act(() => {
            useNavigationGuard.getState().setGuard(true, "Editing");
        });

        act(() => {
            useNavigationGuard.getState().setGuard(false);
        });

        const state = useNavigationGuard.getState();
        expect(state.blocked).toBe(false);
        expect(state.message).toBe("");
    });

    it("setGuard(true) without message defaults to empty string", () => {
        act(() => {
            useNavigationGuard.getState().setGuard(true);
        });

        const state = useNavigationGuard.getState();
        expect(state.blocked).toBe(true);
        expect(state.message).toBe("");
    });

    it("can toggle guard on and off multiple times", () => {
        const { setGuard } = useNavigationGuard.getState();

        act(() => { setGuard(true, "Step 1"); });
        expect(useNavigationGuard.getState().blocked).toBe(true);

        act(() => { setGuard(false); });
        expect(useNavigationGuard.getState().blocked).toBe(false);

        act(() => { setGuard(true, "Step 2"); });
        expect(useNavigationGuard.getState().blocked).toBe(true);
        expect(useNavigationGuard.getState().message).toBe("Step 2");
    });
});
