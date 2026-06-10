"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { ErrorBoundary } from "@/components/ui/ErrorBoundary";
import ConfirmDialog from "@/components/ConfirmDialog";
import { ToastContainer } from "@/components/ui/ToastContainer";
import { useToastStore } from "@/stores/toast";
import { useNotificationStore } from "@/stores/notifications";
import { api } from "@/lib/api";
import { getToken } from "@/lib/api/client";
import { hydrateSecureStore } from "@/lib/secureStore";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import { useNotificationSocket } from "@/lib/hooks/useNotificationSocket";
import { usePolling } from "@/lib/hooks/usePolling";

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
    const hydrateNotifications = useNotificationStore((s) => s.hydrate);
    const lastCheckRef = useRef<number>(Date.now() / 1000);
    const [hydrated, setHydrated] = useState(false);

    // SEC.JWT — hidratar tokens desde safeStorage (Electron) o localStorage (dev/web)
    // antes de cualquier check de auth.
    useEffect(() => {
        hydrateSecureStore().finally(() => setHydrated(true));
    }, []);

    // UI.NOT — cargar notificaciones persistidas tras hidratar el token.
    useEffect(() => {
        if (!hydrated) return;
        const token = getToken();
        if (!token) return;
        hydrateNotifications();
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [hydrated]);

    // Onboarding guard: redirect if company not configured yet
    useEffect(() => {
        if (!hydrated) return;
        if (pathname === "/primeros-pasos") return;
        const token = getToken();
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
    }, [pathname, router, hydrated]);

    // Auth guard: redirige a /login si no hay token (extraído a hook propio).
    useAuthGuard(hydrated);

    // WebSocket de notificaciones (extraído a useNotificationSocket, con
    // reconexión automática). Se activa al hidratar el token.
    useNotificationSocket({
        task_progress: (data) => {
            const { step, total_steps, agent, summary, success } = data as any;
            const agentLabel = agent ? `[${agent}]` : "";
            const progressLabel = total_steps > 1 ? ` (${step}/${total_steps})` : "";
            const msg = summary ? `${agentLabel}${progressLabel} ${summary}` : `${agentLabel}${progressLabel} Paso completado.`;
            const toastType = success ? "info" : "warning";
            showToast(msg, toastType as any);
            pushNotification(msg, toastType as any);
            if (step === total_steps) triggerRefresh();
        },
        hr_notification: (data) => {
            const msg = (data.message as string) || "Notificación RRHH";
            const nType = (data.notif_type as string) || "info";
            showToast(msg, nType as any);
            pushNotification(msg, nType as any);
            triggerRefresh();
        },
        event: (data) => {
            if (!data.event) return;
            const ctx = (data.context as Record<string, any>) || {};
            const eventMessages: Record<string, string> = {
                invoice_created: `Factura ${ctx.invoice_number || "generada"} creada`,
                employee_created: `Empleado ${ctx.employee_name || "nuevo"} registrado`,
                document_uploaded: "Documento subido. Procesando...",
                document_processed: `Documento ${ctx.original_name || ""} procesado.`,
                task_completed: "Tarea IA finalizada con éxito.",
                approval_approved: `Aprobación procesada.${data.workflow_count ? ` ${data.workflow_count} automatizaciones disparadas.` : ""}`,
            };
            const ev = data.event as string;
            const msg = eventMessages[ev] || `Nuevo evento: ${ev.replace(/_/g, " ")}`;
            showToast(msg, "info");
            pushNotification(msg, "info");
            triggerRefresh();
        },
        // Aviso blando al 80% del presupuesto mensual de un empleado IA.
        budget_warning: (data) => {
            const name = (data.employee_name as string) || "Un empleado IA";
            const pct = Math.round(((data.ratio as number) || 0) * 100);
            const msg = `${name} ha consumido el ${pct}% de su presupuesto mensual de IA.`;
            showToast(msg, "warning");
            pushNotification(msg, "warning");
        },
        // Hard-stop: presupuesto agotado, el empleado se ha pausado.
        budget_exhausted: (data) => {
            const name = (data.employee_name as string) || "Un empleado IA";
            const msg = `${name} agotó su presupuesto mensual de IA y se ha pausado. Sube su límite en Mi Equipo para reactivarlo.`;
            showToast(msg, "error");
            pushNotification(msg, "error");
            triggerRefresh();
        },
    }, hydrated);

    // Polling: workflow completions (30s)
    const pollCompletions = async () => {
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
    usePolling(pollCompletions, 30_000, { enabled: hydrated && !!getToken() });

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
            <ToastContainer />
            <ConfirmDialog />
        </div>
    );
}
