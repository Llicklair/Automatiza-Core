"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api, type Task, type AuditEntry } from "@/lib/api";

export function useAuditoria() {
    const searchParams = useSearchParams();
    const preselected = searchParams.get("task");

    const [tasks, setTasks]       = useState<Task[]>([]);
    const [selectedId, setSelected] = useState<string>(preselected ?? "");
    const [entries, setEntries]   = useState<AuditEntry[]>([]);
    const [loadingTasks, setLT]   = useState(true);
    const [loadingLog, setLL]     = useState(false);

    useEffect(() => {
        api.tasks.list({ limit: 50 })
            .then(t => { setTasks(t); if (!preselected && t.length) setSelected(t[0].id); })
            .finally(() => setLT(false));
    }, [preselected]);

    useEffect(() => {
        if (!selectedId) return;
        setLL(true);
        api.tasks.audit(selectedId)
            .then(setEntries)
            .catch(() => setEntries([]))
            .finally(() => setLL(false));
    }, [selectedId]);

    return { tasks, selectedId, setSelected, entries, loadingTasks, loadingLog };
}
