"use client";
import { useState, useEffect } from "react";
import { getToken } from "@/lib/api/client";

export function useUserRole(): string | null {
    const [role, setRole] = useState<string | null>(null);

    useEffect(() => {
        try {
            const token = getToken();
            if (!token) return;
            const payload = JSON.parse(atob(token.split(".")[1]));
            setRole(payload.role ?? null);
        } catch {
            setRole(null);
        }
    }, []);

    return role;
}
