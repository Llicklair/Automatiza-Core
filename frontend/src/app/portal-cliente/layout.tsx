"use client";

import { ToastContainer } from "@/components/ui/ToastContainer";

/**
 * Layout del portal de cliente: vive fuera del dashboard, así que monta
 * su propio ToastContainer (auditoría UIX #4 — sin alert() nativos).
 */
export default function PortalClienteLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <>
            {children}
            <ToastContainer />
        </>
    );
}
