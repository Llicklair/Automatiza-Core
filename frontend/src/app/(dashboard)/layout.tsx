"use client";

import { useEffect, useRef } from "react";
import { useRouter, usePathname } from "next/navigation";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { ErrorBoundary } from "@/components/ui/ErrorBoundary";
import ConfirmDialog from "@/components/ConfirmDialog";
import { useToastStore } from "@/stores/toast";
import { useNotificationStore } from "@/stores/notifications";
import { Toaster } from "@/components/ui/sonner";
import { api } from "@/lib/api";

function decodeJwtName(token: string): string {
    try {
        const payload = JSON.parse(atob(token.split(".")[1]));
        return payload.full_name || payload.name || payload.email?.split("@")[0] || "";
    } catch {
        return "";
    }
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
    const router = useRouter();
    const pathname = usePathname();
    const showToast = useToastStore((s) => s.show);
    const pushNotification = useNotificationStore((s) => s.push);
    const triggerRefresh = useNotificationStore((s) => s.triggerRefresh);
    const lastCheckRef = useRef<number>(Date.now() / 1000);

    // Onboarding guard: redirect if company not configured yet
    useEffect(() => {
        if (pathname === "/primeros-pasos") return;
        const token = localStorage.getItem("access_token");
        if (!token) return;
        try {
            const payload = JSON.parse(atob(token.split(".")[1]));
            // Non-admin users go to their portal when landing on "/"
            if (pathname === "/" && payload.role && payload.role !== "admin") {
                router.push("/portal");
                return;
            }
        } catch { /* ignore */ }
        api.tenant.me().then(t => {
            if (!t.nif) router.push("/primeros-pasos");
        }).catch(() => {});
    }, [pathname, router]);

    // Auth check + WebSocket notifications
    useEffect(() => {
        const token = localStorage.getItem("access_token");
        if (!token) { router.push("/login"); return; }

        const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const wsDomain = process.env.NEXT_PUBLIC_WS_URL || `${wsProtocol}//${window.location.hostname}:8080/ws`;
        const ws = new WebSocket(`${wsDomain}/notifications?token=${token}`);

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.type === "task_progress") {
                    const { step, total_steps, agent, summary, success } = data;
                    const agentLabel = agent ? `[${agent}]` : "";
                    const progressLabel = total_steps > 1 ? ` (${step}/${total_steps})` : "";
                    const msg = summary ? `${agentLabel}${progressLabel} ${summary}` : `${agentLabel}${progressLabel} Paso completado.`;
                    const toastType = success ? "info" : "warning";
                    showToast(msg, toastType);
                    pushNotification(msg, toastType as any);
                    if (step === total_steps) triggerRefresh();
                    return;
                }
                if (data.type === "hr_notification") {
                    const msg = data.message as string || "Notificación RRHH";
                    const nType = (data.notif_type as string) || "info";
                    showToast(msg, nType as any);
                    pushNotification(msg, nType as any);
                    triggerRefresh();
                    return;
                }
                if (data.type === "event" && data.event) {
                    const eventMessages: Record<string, string> = {
                        invoice_created: `Factura ${data.context?.invoice_number || "generada"} creada`,
                        employee_created: `Empleado ${data.context?.employee_name || "nuevo"} registrado`,
                        document_uploaded: "Documento subido. Procesando...",
                        document_processed: `Documento ${data.context?.original_name || ""} procesado.`,
                        task_completed: "Tarea IA finalizada con éxito.",
                        approval_approved: `Aprobación procesada.${data.workflow_count ? ` ${data.workflow_count} automatizaciones disparadas.` : ""}`,
                    };
                    const msg = eventMessages[data.event] || `Nuevo evento: ${data.event.replace(/_/g, " ")}`;
                    showToast(msg, "info");
                    pushNotification(msg, "info");
                    triggerRefresh();
                }
            } catch { /* ignorar mensajes malformados */ }
        };

        return () => ws.close();
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [router]);

    // Polling: workflow completions (30s)
    useEffect(() => {
        const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
        if (!token) return;

        const poll = async () => {
            try {
                const since = lastCheckRef.current;
                lastCheckRef.current = Date.now() / 1000;
                const items = await api.workflows.recentCompletions(since);
                for (const item of items) {
                    const ok = item.status === "completed" || item.status === "success";
                    const msg = `Automatización "${item.workflow_name}" ${ok ? "completada" : "falló"}`;
                    const type = ok ? "success" : "error";
                    showToast(msg, type);
                    pushNotification(msg, type);
                }
                if (items.length > 0) triggerRefresh();
            } catch { /* silencioso */ }
        };

        const interval = setInterval(poll, 30_000);
        return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    return (
        <div className="flex h-screen bg-background overflow-hidden">
            <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:p-4 focus:bg-background focus:text-foreground">Saltar al contenido</a>
            <Sidebar />
            <div className="flex-1 flex flex-col overflow-hidden min-w-0">
                <Header />
                <main id="main-content" className="flex-1 overflow-y-auto relative" style={{ zIndex: 1 }}>
                    <ErrorBoundary section="aplicación">
                        {children}
                    </ErrorBoundary>
                </main>
            </div>
            <Toaster />
            <ConfirmDialog />
        </div>
    );
}
