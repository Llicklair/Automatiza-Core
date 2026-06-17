"use client";

import { useEffect } from "react";
import { useLicenseStore } from "@/stores/license";
import { licenseApi } from "@/lib/api/license";
import LicenseModal from "./LicenseModal";

export function LicenseListener() {
    const show = useLicenseStore((s) => s.show);
    const setPlan = useLicenseStore((s) => s.setPlan);

    useEffect(() => {
        let cancelled = false;
        let attempt = 0;

        // Comprobar licencia al arrancar, con reintentos: el backend puede estar
        // arrancando o el servidor de licencias en cold start (~30-60s). Antes un
        // único fallo se tragaba en silencio y el modal "dejaba de salir".
        const check = () => {
            licenseApi.status().then((res) => {
                if (cancelled) return;
                if (!res.valid) show();
                else setPlan(res.plan);
            }).catch((e) => {
                if (cancelled) return;
                attempt += 1;
                if (attempt <= 5) {
                    setTimeout(check, Math.min(2000 * attempt, 8000)); // backoff
                } else {
                    console.error("[LICENSE] No se pudo verificar la licencia tras varios intentos", e);
                    // No abrimos el modal por un fallo de red transitorio; si el
                    // backend bloquea de verdad, cualquier 402 dispara el evento de abajo.
                }
            });
        };
        check();

        const handler = () => show();
        window.addEventListener("license-required", handler);
        return () => {
            cancelled = true;
            window.removeEventListener("license-required", handler);
        };
    }, [show, setPlan]);

    return <LicenseModal />;
}
