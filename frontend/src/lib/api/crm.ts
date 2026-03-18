import { request } from "./client";
import type { Client } from "./erp";

export interface Opportunity {
    id: string;
    tenant_id: string;
    client_id: string;
    title: string;
    expected_value: number;
    stage: 'new' | 'qualified' | 'proposal' | 'won' | 'lost';
    created_at: string;
    updated_at: string;
    client?: Client;
}

export interface Activity {
    id: string;
    tenant_id: string;
    client_id: string | null;
    opportunity_id: string | null;
    type: string; // call | email | note | meeting_log
    description: string;
    metadata_json: Record<string, any>;
    created_at: string;
}

export interface EventItem {
    id: string;
    tenant_id: string;
    title: string;
    description: string | null;
    start_time: string;
    end_time: string;
    type: string;
    location_or_link: string | null;
    client_id: string | null;
    created_at: string;
    updated_at: string;
}

export interface Reservation {
    id: string;
    tenant_id: string;
    client_id: string;
    resource_id: string | null;
    start_time: string;
    end_time: string;
    status: string;
    notes: string | null;
    created_at: string;
    updated_at: string;
}

export const crm = {
    opportunities: {
        list: () => request<Opportunity[]>("/api/v1/crm/opportunities"),
        create: (data: Partial<Opportunity>) =>
            request<Opportunity>("/api/v1/crm/opportunities", {
                method: "POST",
                body: JSON.stringify(data),
            }),
        update: (id: string, data: Partial<Opportunity>) =>
            request<Opportunity>(`/api/v1/crm/opportunities/${id}`, {
                method: "PATCH",
                body: JSON.stringify(data),
            }),
        delete: (id: string) =>
            request<void>(`/api/v1/crm/opportunities/${id}`, { method: "DELETE" }),
    },
    activities: {
        list: (params?: { client_id?: string; opportunity_id?: string }) => {
            const q = new URLSearchParams(params as Record<string, string>).toString();
            return request<Activity[]>(`/api/v1/crm/activities${q ? "?" + q : ""}`);
        },
        create: (data: Partial<Activity>) =>
            request<Activity>("/api/v1/crm/activities", {
                method: "POST",
                body: JSON.stringify(data),
            }),
        delete: (id: string) => request<void>(`/api/v1/crm/activities/${id}`, { method: "DELETE" }),
    },
    events: {
        list: () => request<EventItem[]>("/api/v1/crm/events"),
        create: (data: Partial<EventItem>) =>
            request<EventItem>("/api/v1/crm/events", {
                method: "POST",
                body: JSON.stringify(data),
            }),
        update: (id: string, data: Partial<EventItem>) =>
            request<EventItem>(`/api/v1/crm/events/${id}`, {
                method: "PATCH",
                body: JSON.stringify(data),
            }),
        delete: (id: string) =>
            request<void>(`/api/v1/crm/events/${id}`, { method: "DELETE" }),
    },
    reservations: {
        list: () => request<Reservation[]>("/api/v1/crm/reservations"),
        create: (data: Partial<Reservation>) =>
            request<Reservation>("/api/v1/crm/reservations", {
                method: "POST",
                body: JSON.stringify(data),
            }),
        update: (id: string, data: Partial<Reservation>) =>
            request<Reservation>(`/api/v1/crm/reservations/${id}`, {
                method: "PATCH",
                body: JSON.stringify(data),
            }),
        delete: (id: string) =>
            request<void>(`/api/v1/crm/reservations/${id}`, { method: "DELETE" }),
    }
};
