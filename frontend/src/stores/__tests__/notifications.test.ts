import { describe, it, expect, beforeEach } from "vitest";
import { useNotificationStore } from "../notifications";
import { act } from "@testing-library/react";

beforeEach(() => {
    act(() => {
        useNotificationStore.setState({ items: [], unreadCount: 0, refreshKey: 0 });
    });
});

describe("useNotificationStore", () => {
    it("starts with empty items and zero unread count", () => {
        const state = useNotificationStore.getState();
        expect(state.items).toEqual([]);
        expect(state.unreadCount).toBe(0);
        expect(state.refreshKey).toBe(0);
    });

    it("push() adds a notification with default type 'info'", () => {
        act(() => {
            useNotificationStore.getState().push("New notification");
        });

        const { items, unreadCount } = useNotificationStore.getState();
        expect(items).toHaveLength(1);
        expect(items[0].message).toBe("New notification");
        expect(items[0].type).toBe("info");
        expect(items[0].read).toBe(false);
        expect(items[0].timestamp).toBeGreaterThan(0);
        expect(unreadCount).toBe(1);
    });

    it("push() adds a notification with custom type", () => {
        act(() => {
            useNotificationStore.getState().push("Error!", "error");
        });

        expect(useNotificationStore.getState().items[0].type).toBe("error");
    });

    it("push() prepends new notifications (newest first)", () => {
        act(() => {
            useNotificationStore.getState().push("first");
            useNotificationStore.getState().push("second");
        });

        const { items } = useNotificationStore.getState();
        expect(items[0].message).toBe("second");
        expect(items[1].message).toBe("first");
    });

    it("push() increments unreadCount for each notification", () => {
        act(() => {
            useNotificationStore.getState().push("a");
            useNotificationStore.getState().push("b");
            useNotificationStore.getState().push("c");
        });

        expect(useNotificationStore.getState().unreadCount).toBe(3);
    });

    it("enforces max 50 notifications", () => {
        act(() => {
            for (let i = 0; i < 55; i++) {
                useNotificationStore.getState().push(`msg-${i}`);
            }
        });

        expect(useNotificationStore.getState().items).toHaveLength(50);
        // Newest should be first
        expect(useNotificationStore.getState().items[0].message).toBe("msg-54");
    });

    it("markAllRead() marks all items as read and resets unreadCount", () => {
        act(() => {
            useNotificationStore.getState().push("a");
            useNotificationStore.getState().push("b");
        });

        expect(useNotificationStore.getState().unreadCount).toBe(2);

        act(() => {
            useNotificationStore.getState().markAllRead();
        });

        const { items, unreadCount } = useNotificationStore.getState();
        expect(unreadCount).toBe(0);
        expect(items.every((n) => n.read === true)).toBe(true);
    });

    it("clear() removes all notifications and resets unreadCount", () => {
        act(() => {
            useNotificationStore.getState().push("a");
            useNotificationStore.getState().push("b");
        });

        act(() => {
            useNotificationStore.getState().clear();
        });

        const { items, unreadCount } = useNotificationStore.getState();
        expect(items).toEqual([]);
        expect(unreadCount).toBe(0);
    });

    it("triggerRefresh() increments refreshKey", () => {
        expect(useNotificationStore.getState().refreshKey).toBe(0);

        act(() => {
            useNotificationStore.getState().triggerRefresh();
        });

        expect(useNotificationStore.getState().refreshKey).toBe(1);

        act(() => {
            useNotificationStore.getState().triggerRefresh();
        });

        expect(useNotificationStore.getState().refreshKey).toBe(2);
    });
});
