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
};
