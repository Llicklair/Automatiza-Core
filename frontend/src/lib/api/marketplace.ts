/**
 * Marketplace de workflows (F3.10) — plantillas curadas + YAML import/export.
 */
import { request } from "./client";

export interface WorkflowTemplate {
    id: string;
    slug: string;
    name: string;
    description: string | null;
    category: string;
    author: string | null;
    trigger_type: string;
    trigger_config: Record<string, unknown>;
    action_type: string;
    action_config: Record<string, unknown>;
    execution_mode: string;
    compiled_steps: unknown[] | null;
    tags: string[];
    is_official: boolean;
    downloads_count: number;
}

export interface InstallResult {
    workflow_id: string;
    name: string;
    is_active: boolean;
    source_template_slug?: string;
}

export const marketplace = {
    templates: {
        list: (category?: string) => {
            const qs = category ? `?category=${encodeURIComponent(category)}` : "";
            return request<{ count: number; templates: WorkflowTemplate[] }>(
                `/api/v1/marketplace/templates${qs}`,
            );
        },
        get: (slug: string) =>
            request<WorkflowTemplate>(
                `/api/v1/marketplace/templates/${encodeURIComponent(slug)}`,
            ),
        install: (slug: string, opts?: { name?: string }) =>
            request<InstallResult>(
                `/api/v1/marketplace/templates/${encodeURIComponent(slug)}/install`,
                { method: "POST", body: JSON.stringify(opts || {}) },
            ),
        seedOfficial: () =>
            request<{ created: number; total_official: number }>(
                "/api/v1/marketplace/templates/seed-official",
                { method: "POST" },
            ),
    },
    workflows: {
        exportYaml: (workflowId: string) =>
            request<{ workflow_id: string; yaml: string }>(
                `/api/v1/marketplace/workflows/${workflowId}/export-yaml`,
            ),
        importYaml: (yamlStr: string) =>
            request<InstallResult>("/api/v1/marketplace/workflows/import-yaml", {
                method: "POST",
                body: JSON.stringify({ yaml: yamlStr }),
            }),
    },
};
