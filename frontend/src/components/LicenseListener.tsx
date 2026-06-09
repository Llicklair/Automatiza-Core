"use client";

import { useEffect } from "react";
import { useLicenseStore } from "@/stores/license";
import { licenseApi } from "@/lib/api/license";
import LicenseModal from "./LicenseModal";

export function LicenseListener() {
    const show = useLicenseStore((s) => s.show);
    const setPlan = useLicenseStore((s) => s.setPlan);

    useEffect(() => {
        // Comprobar licencia al arrancar — antes del login
        licenseApi.status().then((res) => {
            if (!res.valid) show();
            else setPlan(res.plan);
        }).catch(() => {
            // Si el backend no responde aún, no bloqueamos (puede estar arrancando)
        });

        const handler = () => show();
        window.addEventListener("license-required", handler);
        return () => window.removeEventListener("license-required", handler);
    }, [show]);

    return <LicenseModal />;
}
