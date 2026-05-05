import { request } from "./client";

export interface User {
    id: string;
    email: string;
    full_name: string | null;
    role: string;
    is_active: boolean;
}

export interface UserCreate {
    email: string;
    password: string;
    first_name?: string;
    last_name?: string;
    role?: string;
}

export interface UserUpdate {
    first_name?: string;
    last_name?: string;
    role?: string;
    is_active?: boolean;
}

export interface Invitation {
    id: string;
    email: string;
    role: string;
    expires_at: string;
    used_at: string | null;
    used_by_id: string | null;
    created_at: string;
    status: "pending" | "used" | "expired";
}

export interface InvitationCreated extends Invitation {
    token: string;
}

export interface InvitationCreate {
    email: string;
    role?: string;
    ttl_days?: number;
}

export interface InvitationPublic {
    email: string;
    role: string;
    expires_at: string;
}

export interface InvitationAccept {
    password: string;
    first_name?: string;
    last_name?: string;
}

export interface InvitationAcceptResponse {
    access_token: string;
    refresh_token: string;
    user: User;
}

export const users = {
    list: () => request<User[]>("/api/v1/users"),
    me: () => request<User>("/api/v1/users/me"),
    get: (id: string) => request<User>(`/api/v1/users/${id}`),
    create: (data: UserCreate) =>
        request<User>("/api/v1/users", {
            method: "POST",
            body: JSON.stringify(data),
        }),
    update: (id: string, data: UserUpdate) =>
        request<User>(`/api/v1/users/${id}`, {
            method: "PATCH",
            body: JSON.stringify(data),
        }),
    delete: (id: string) =>
        request<void>(`/api/v1/users/${id}`, {
            method: "DELETE",
        }),

    invitations: {
        list: () => request<Invitation[]>("/api/v1/users/invitations"),
        create: (data: InvitationCreate) =>
            request<InvitationCreated>("/api/v1/users/invitations", {
                method: "POST",
                body: JSON.stringify(data),
            }),
        revoke: (id: string) =>
            request<void>(`/api/v1/users/invitations/${id}`, { method: "DELETE" }),
        getByToken: (token: string) =>
            request<InvitationPublic>(`/api/v1/users/invitations/by-token/${token}`),
        accept: (token: string, data: InvitationAccept) =>
            request<InvitationAcceptResponse>(
                `/api/v1/users/invitations/by-token/${token}/accept`,
                { method: "POST", body: JSON.stringify(data) }
            ),
    },
};
