"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { api, type Task, type AuditEntry } from "@/lib/api";
import { ChevronDown, ChevronUp } from "lucide-react";

const STATUS_COLOR: Record<string, string> = {
    success: "text-emerald-400 bg-emerald-500/10",
    failed: "text-red-400 bg-red-500/10",
    rejected: "text-amber-400 bg-amber-500/10",
    pending_approval: "text-blue-400 bg-blue-500/10",
    skipped: "text-muted-foreground bg-accent",
};

function EntryRow({ entry }: { entry: AuditEntry }) {
    const [open, setOpen] = useState(false);
    const hasDetail = entry.input_data || entry.output_data || entry.error_detail;

    return (
        <div className="border-b border-border last:border-0">
            <div
                className={`grid grid-cols-12 gap-4 px-6 py-3.5 items-center ${hasDetail ? "cursor-pointer hover:bg-accent/50" : ""} transition`}
                onClick={() => hasDetail && setOpen(o => !o)}
            >
                <div className="col-span-2 text-xs text-muted-foreground font-mono">
                    {new Date(entry.executed_at).toLocaleString("es-ES", {
                        hour: "2-digit", minute: "2-digit", second: "2-digit",
                    })}
                </div>
                <div className="col-span-2 text-xs text-foreground font-medium">{entry.agent_name}</div>
                <div className="col-span-4 text-xs text-muted-foreground">{entry.action_type}</div>
                <div className="col-span-2">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_COLOR[entry.status] ?? "text-muted-foreground bg-accent"}`}>
                        {entry.status}
                    </span>
                </div>
                <div className="col-span-2 flex justify-end">
                    {hasDetail && (
                        open
                            ? <ChevronUp className="w-4 h-4 text-muted-foreground" />
                            : <ChevronDown className="w-4 h-4 text-muted-foreground" />
                    )}
                </div>
            </div>

            {Boolean(hasDetail) && (
                <div className={`grid transition-[grid-template-rows,opacity] duration-300 ease-in-out ${open ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0"}`}>
                    <div className="overflow-hidden">
                        <div className="px-6 pb-4 space-y-3">
                            {entry.error_detail && (
                                <div className="px-4 py-3 rounded-lg bg-red-500/5 border border-red-500/20 text-xs text-red-300">
                                    {entry.error_detail}
                                </div>
                            )}
                            {Boolean(entry.input_data) && (
                                <div>
                                    <p className="text-xs text-muted-foreground mb-1">Input</p>
                                    <pre className="px-4 py-3 rounded-lg bg-background text-xs text-foreground border border-border overflow-x-auto">
                                        {JSON.stringify(entry.input_data, null, 2)}
                                    </pre>
                                </div>
                            )}
                            {Boolean(entry.output_data) && (
                                <div>
                                    <p className="text-xs text-muted-foreground mb-1">Output</p>
                                    <pre className="px-4 py-3 rounded-lg bg-background text-xs text-foreground border border-border overflow-x-auto">
                                        {JSON.stringify(entry.output_data, null, 2)}
                                    </pre>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

function AuditoriaContent() {
    const searchParams = useSearchParams();
    const preselected = searchParams.get("task");

    const [tasks, setTasks] = useState<Task[]>([]);
    const [selectedId, setSelected] = useState<string>(preselected ?? "");
    const [entries, setEntries] = useState<AuditEntry[]>([]);
    const [loadingTasks, setLT] = useState(true);
    const [loadingLog, setLL] = useState(false);

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

    return (
        <div className="p-8 max-w-6xl mx-auto">
            <div className="mb-8">
                <h1 className="text-2xl font-bold text-foreground">Auditoría</h1>
                <p className="text-sm text-muted-foreground mt-1">Registro completo de todas las acciones ejecutadas por los agentes</p>
            </div>

            <div className="grid lg:grid-cols-4 gap-6">
                {/* Selector de tarea */}
                <div className="lg:col-span-1 rounded-xl border border-border bg-card overflow-hidden">
                    <div className="px-4 py-3 border-b border-border text-xs font-medium text-muted-foreground uppercase tracking-wide">
                        Tarea
                    </div>
                    <div className="divide-y divide-border max-h-[60vh] overflow-y-auto">
                        {loadingTasks ? (
                            <div className="p-4 text-xs text-muted-foreground">Cargando…</div>
                        ) : tasks.map(t => (
                            <button
                                key={t.id}
                                onClick={() => setSelected(t.id)}
                                className={`w-full text-left px-4 py-3 transition ${selectedId === t.id
                                    ? "bg-primary/20 text-primary"
                                    : "text-muted-foreground hover:bg-accent/50 hover:text-foreground"
                                    }`}
                            >
                                <p className="text-xs font-medium truncate">{t.user_intent}</p>
                                <p className="text-xs text-muted-foreground/60 mt-0.5 font-mono">{t.id.slice(0, 8)}…</p>
                            </button>
                        ))}
                    </div>
                </div>

                {/* Log de la tarea seleccionada */}
                <div className="lg:col-span-3 rounded-xl border border-border bg-card overflow-hidden">
                    <div className="grid grid-cols-12 gap-4 px-6 py-3 border-b border-border
                          text-xs font-medium text-muted-foreground uppercase tracking-wide">
                        <div className="col-span-2">Hora</div>
                        <div className="col-span-2">Agente</div>
                        <div className="col-span-4">Acción</div>
                        <div className="col-span-2">Estado</div>
                        <div className="col-span-2"></div>
                    </div>
                    {loadingLog ? (
                        <div className="py-16 text-center text-muted-foreground text-sm">Cargando…</div>
                    ) : entries.length === 0 ? (
                        <div className="py-16 text-center text-muted-foreground text-sm">
                            {selectedId ? "Sin registros para esta tarea" : "Selecciona una tarea"}
                        </div>
                    ) : (
                        entries.map(e => <EntryRow key={e.id} entry={e} />)
                    )}
                </div>
            </div>
        </div>
    );
}

export default function AuditoriaPage() {
    return (
        <Suspense fallback={<div className="p-8 text-muted-foreground">Cargando auditoría...</div>}>
            <AuditoriaContent />
        </Suspense>
    );
}
