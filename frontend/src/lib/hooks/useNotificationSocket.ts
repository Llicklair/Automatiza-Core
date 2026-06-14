"use client";

import { useEffect, useRef } from "react";
import { getToken, BASE } from "@/lib/api/client";

type MessageHandler = (msg: Record<string, unknown>) => void;

/**
 * Connects to /ws/notifications and dispatches messages by type.
 * handlers: { "agent_status_changed": fn, "activity_new": fn, ... }
 * Re-connects automatically on close (unless unmounted).
 *
 * `enabled` (default true) gates the connection: pass `false` until the auth
 * token is hydrated so the layout-level mount doesn't bail out before the token
 * exists. When it flips to true the effect re-runs and connects.
 */
export function useNotificationSocket(
    handlers: Record<string, MessageHandler>,
    enabled: boolean = true,
) {
    const handlersRef = useRef(handlers);
    useEffect(() => {
        handlersRef.current = handlers;
    });

    useEffect(() => {
        if (!enabled) return;
        let ws: WebSocket | null = null;
        let destroyed = false;

        function connect() {
            const token = getToken();
            if (!token || destroyed) return;

            const wsBase = BASE.replace(/^http/, "ws");
            ws = new WebSocket(`${wsBase}/ws/notifications?token=${token}`);

            ws.onmessage = (event) => {
                try {
                    const msg = JSON.parse(event.data) as Record<string, unknown>;
                    const type = msg.type as string | undefined;
                    if (type && handlersRef.current[type]) {
                        handlersRef.current[type](msg);
                    }
                } catch {
                    // ignore malformed frames
                }
            };

            ws.onopen = () => ws?.send("ping");

            ws.onclose = () => {
                if (!destroyed) setTimeout(connect, 3000);
            };

            ws.onerror = () => ws?.close();
        }

        connect();

        return () => {
            destroyed = true;
            ws?.close();
        };
    }, [enabled]);
}
