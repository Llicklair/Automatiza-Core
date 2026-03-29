import { request, BASE, getToken } from "./client";

export interface DocumentTemplate {
    id: string;
    name: string;
    template_type: "invoice" | "payroll" | "excel" | "albaran";
    layout_style: "modern" | "classic" | "minimal" | "bold";
    accent_color: string;
    font_family: "helvetica" | "times" | "courier";
    logo_position: "left" | "center" | "right";
    header_style: "color_band" | "line_only" | "dark_band" | "none";
    table_style: "striped" | "clean" | "bordered" | "accent_header";
    footer_text: string | null;
    is_default: boolean;
}

export type TemplateCreate = Omit<DocumentTemplate, "id">;
export type TemplateUpdate = Partial<Omit<DocumentTemplate, "id" | "template_type">>;

export interface PreviewRequest {
    template_type: "invoice" | "payroll" | "excel" | "albaran";
    layout_style: string;
    accent_color: string;
    font_family: string;
    logo_position: string;
    header_style: string;
    table_style: string;
    footer_text?: string | null;
}

export const templatesApi = {
    list: (template_type?: string): Promise<DocumentTemplate[]> => {
        const q = template_type ? `?template_type=${template_type}` : "";
        return request(`/api/v1/templates${q}`);
    },

    create: (data: TemplateCreate): Promise<DocumentTemplate> =>
        request("/api/v1/templates", { method: "POST", body: JSON.stringify(data) }),

    update: (id: string, data: TemplateUpdate): Promise<DocumentTemplate> =>
        request(`/api/v1/templates/${id}`, { method: "PUT", body: JSON.stringify(data) }),

    delete: (id: string): Promise<void> =>
        request(`/api/v1/templates/${id}`, { method: "DELETE" }),

    setDefault: (id: string): Promise<DocumentTemplate> =>
        request(`/api/v1/templates/${id}/set-default`, { method: "POST", body: JSON.stringify({}) }),

    seedDefaults: (template_type: string): Promise<DocumentTemplate[]> =>
        request(`/api/v1/templates/seed-defaults?template_type=${template_type}`, { method: "POST", body: JSON.stringify({}) }),

    preview: async (data: PreviewRequest): Promise<string> => {
        const token = getToken();
        const res = await fetch(`${BASE}/api/v1/templates/preview`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                ...(token ? { Authorization: `Bearer ${token}` } : {}),
            },
            body: JSON.stringify(data),
        });
        if (!res.ok) throw new Error("Error generando preview");
        const blob = await res.blob();
        return URL.createObjectURL(blob);
    },
};
