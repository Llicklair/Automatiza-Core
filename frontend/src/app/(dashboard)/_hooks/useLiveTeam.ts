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
    /** Domains con actividad reciente — para iluminar avatares aunque
     *  el backend no haya emitido agent_status_changed (ocurre con prompts
     *  sin addressed_employee_id, como los de la chat bar genérica). */
    activeDomains: Set<string>;
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
const HIGHLIGHT_MS = 4000;

export function useLiveTeam(): LiveTeamData {
    const [employees, setEmployees] = useState<AIEmployee[]>([]);
    const [recentActivity, setRecentActivity] = useState<ActivityEntry[]>([]);
    const [recentResults, setRecentResults] = useState<LiveAgentResult[]>([]);
    const [activeDomains, setActiveDomains] = useState<Set<string>>(new Set());
    const [loading, setLoading] = useState(true);

    const bumpDomain = useCallback((domain: string) => {
        if (!domain) return;
        setActiveDomains((prev) => {
            const next = new Set(prev);
            next.add(domain);
            return next;
        });
        setTimeout(() => {
            setActiveDomains((prev) => {
                if (!prev.has(domain)) return prev;
                const next = new Set(prev);
                next.delete(domain);
                return next;
            });
        }, HIGHLIGHT_MS);
    }, []);

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
            // Highlight temporal del avatar correspondiente, aunque el
            // backend no haya emitido agent_status_changed.
            bumpDomain(agentDomain);
        },
        orchestrator_step: (msg) => {
            // Cuando el orchestrator entra en "dispatch", encendemos el hub
            // central como señal de actividad inminente.
            const node = msg.node as string | undefined;
            if (node === "dispatch") bumpDomain("__hub__");
        },
    });

    return { employees, recentActivity, recentResults, activeDomains, loading };
}
