"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { AIEmployee, ActivityEntry } from "@/lib/api/ai_employees";
import { useNotificationSocket } from "@/lib/hooks/useNotificationSocket";

export interface LiveAgentResult {
    employeeId: string | null;
    domain: string;
    summary: string;
    success: boolean;
    taskId: string;
    at: number;
}

export interface LiveTeamData {
    employees: AIEmployee[];
    recentActivity: ActivityEntry[];
    recentResults: LiveAgentResult[];
    loading: boolean;
}

/**
 * Carga lista de AIEmployees + se suscribe vía WebSocket a:
 *  - agent_status_changed → actualiza status (idle/working) en tiempo real.
 *  - activity_new → añade entrada al feed compacto.
 *  - agent_result → recopila un timeline corto de "qué hizo cada agente".
 *
 * No hace polling: estado convergente a partir del snapshot inicial + eventos WS.
 */
export function useLiveTeam(): LiveTeamData {
    const [employees, setEmployees] = useState<AIEmployee[]>([]);
    const [recentActivity, setRecentActivity] = useState<ActivityEntry[]>([]);
    const [recentResults, setRecentResults] = useState<LiveAgentResult[]>([]);
    const [loading, setLoading] = useState(true);

    const load = useCallback(async () => {
        try {
            const [emps, act] = await Promise.all([
                api.aiEmployees.list().catch(() => [] as AIEmployee[]),
                api.aiEmployees.activityFeed({ limit: 10 }).catch(() => [] as ActivityEntry[]),
            ]);
            setEmployees(emps);
            setRecentActivity(act);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { load(); }, [load]);

    useNotificationSocket({
        agent_status_changed: (msg) => {
            const empId = msg.employee_id as string | undefined;
            const status = msg.status as AIEmployee["status"] | undefined;
            if (!empId || !status) return;
            setEmployees((prev) => prev.map((e) => (e.id === empId ? { ...e, status } : e)));
        },
        activity_new: (msg) => {
            const entry = msg.entry as ActivityEntry | undefined;
            if (!entry) return;
            setRecentActivity((prev) => {
                const next = [entry, ...prev.filter((p) => p.id !== entry.id)];
                return next.slice(0, 10);
            });
        },
        agent_result: (msg) => {
            const agentDomain = (msg.agent as string) || "unknown";
            const summary = (msg.summary as string) || "";
            const taskId = (msg.task_id as string) || "";
            const success = Boolean(msg.success);
            // map agent_domain → employeeId (mejor esfuerzo)
            setEmployees((prev) => {
                const match = prev.find((e) => e.domain === agentDomain);
                setRecentResults((r) => [
                    {
                        employeeId: match?.id ?? null,
                        domain: agentDomain,
                        summary,
                        success,
                        taskId,
                        at: Date.now(),
                    },
                    ...r,
                ].slice(0, 12));
                return prev;
            });
        },
    });

    return { employees, recentActivity, recentResults, loading };
}
