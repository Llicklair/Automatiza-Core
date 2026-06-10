"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useNotificationSocket } from "./useNotificationSocket";

/**
 * Número de aprobaciones pendientes del tenant. Fetch inicial + push WS
 * (`approval_created`) + polling de respaldo cada 60 s (cubre decisiones
 * tomadas en /bandeja, que no emiten WS).
 */
export function usePendingApprovalsCount(): number {
    const [count, setCount] = useState(0);

    const refresh = useCallback(() => {
        api.approvals
            .list()
            .then((items) => setCount(items.filter((a) => a.status === "pending").length))
            .catch(() => {
                /* sin sesión o backend caído: dejamos el último valor */
            });
    }, []);

    useEffect(() => {
        refresh();
        const id = setInterval(refresh, 60_000);
        return () => clearInterval(id);
    }, [refresh]);

    useNotificationSocket({ approval_created: refresh });

    return count;
}
