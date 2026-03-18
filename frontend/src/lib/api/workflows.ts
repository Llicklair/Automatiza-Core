import { request } from "./client";

export interface Workflow {
    id: string;
    tenant_id: string;
    name: string;
    description: string | null;
    is_active: boolean;
    trigger_type: string;
    trigger_config: any;
    action_type: string;
    action_config: any;
    ui_nodes?: any[];
    ui_edges?: any[];
    execution_mode: "reasoning" | "deterministic";
    compiled_steps?: Array<{ agent: string; action: string; params: { intent: string } }> | null;
    created_at: string;
}

export interface WorkflowExecution {
    id: string;
    workflow_id: string;
    tenant_id: string;
    status: string; // running | completed | success | failed | paused
    started_at: string;
    completed_at: string | null;
    trigger_payload: any;
    result_log: string | null;
    task_id: string | null;
    node_states: Record<string, { status: string; output?: any; started_at?: string; completed_at?: string }> | null;
    current_node_id: string | null;
    paused_at: string | null;
}

export const workflows = {
    list: () => request<Workflow[]>("/api/v1/workflows"),
    create: (data: Partial<Workflow>) => request<Workflow>("/api/v1/workflows", { method: "POST", body: JSON.stringify(data) }),
    parse: (text: string) => request<any>("/api/v1/workflows/parse-nl", { method: "POST", body: JSON.stringify({ text }) }),
    update: (id: string, data: Partial<Workflow>) => request<Workflow>(`/api/v1/workflows/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
    delete: (id: string) => request(`/api/v1/workflows/${id}`, { method: "DELETE" }),
    run: (id: string) => request<WorkflowExecution>(`/api/v1/workflows/${id}/run`, { method: "POST" }),
    executions: (id: string) => request<WorkflowExecution[]>(`/api/v1/workflows/${id}/executions`),
    resumeExecution: (workflowId: string, executionId: string) =>
        request<WorkflowExecution>(`/api/v1/workflows/${workflowId}/executions/${executionId}/resume`, { method: "POST" }),
    cancelExecution: (workflowId: string, executionId: string) =>
        request<WorkflowExecution>(`/api/v1/workflows/${workflowId}/executions/${executionId}/cancel`, { method: "POST" }),
    runWithContext: (workflowId: string, context: string) =>
        request<WorkflowExecution>(`/api/v1/workflows/${workflowId}/run-with-context`, { method: "POST", body: JSON.stringify({ context }) }),
    executionLogs: (workflowId: string, executionId: string) =>
        request<{ lines: string[]; status: string }>(`/api/v1/workflows/${workflowId}/executions/${executionId}/logs`),
    recentCompletions: (since: number) =>
        request<{ id: string; status: string; completed_at: string | null; workflow_name: string }[]>(
            `/api/v1/workflows/recent-completions?since=${since}`
        ),
};
