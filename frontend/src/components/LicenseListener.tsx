"use client";

import { useEffect } from "react";
import { useLicenseStore } from "@/stores/license";
import LicenseModal from "./LicenseModal";

export function LicenseListener() {
    const show = useLicenseStore((s) => s.show);

    useEffect(() => {
        const handler = () => show();
        window.addEventListener("license-required", handler);
        return () => window.removeEventListener("license-required", handler);
    }, [show]);

    return <LicenseModal />;
}
