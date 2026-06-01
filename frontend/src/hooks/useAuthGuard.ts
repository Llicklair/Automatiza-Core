"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { getToken } from "@/lib/api/client";

/**
 * Redirige a /login cuando no hay token de auth tras la hidratación.
 *
 * Extraído de DashboardLayout para separar la responsabilidad de guarda de
 * sesión del resto de efectos (WebSocket, polling, onboarding). Espera a
 * `hydrated` porque en Electron el token se hidrata async desde safeStorage.
 */
export function useAuthGuard(hydrated: boolean) {
    const router = useRouter();

    useEffect(() => {
        if (!hydrated) return;
        if (!getToken()) router.push("/login");
    }, [hydrated, router]);
}
