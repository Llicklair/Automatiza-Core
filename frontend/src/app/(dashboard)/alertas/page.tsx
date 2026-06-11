"use client";

import { useCallback, useEffect, useState } from "react";
import {
    AlertTriangle, Bell, CheckCircle2, Info, Loader2, PackageX,
    RefreshCw, ReceiptText, Sparkles, Wallet,
} from "lucide-react";
import { api } from "@/lib/api";
import type { AlertEntry } from "@/lib/api";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/ui/button";
import { KpiCard } from "@/components/shared/KpiCard";
import { useToastStore } from "@/stores/toast";
import { PageContainer } from "@/components/shared/PageContainer";

const TYPE_META: Record<string, { label: string; icon: React.ElementType; href: string }> = {
    overdue_invoice:  { label: "Factura vencida",           icon: ReceiptText, href: "/ventas/facturas" },
    due_soon_invoice: { label: "Factura próxima a vencer",  icon: ReceiptText, href: "/ventas/facturas" },
    low_stock:        { label: "Stock bajo",                icon: PackageX,    href: "/inventario/stock" },
    pending_payroll:  { label: "Nómina pendiente de pago",  icon: Wallet,      href: "/rrhh/nominas" },
};

const SEVERITY_CLS: Record<string, string> = {
    error:   "border-red-500/30 bg-red-500/5",
    warning: "border-amber-500/30 bg-amber-500/5",
    info:    "border-blue-500/30 bg-blue-500/5",
};

const SEVERITY_ICON: Record<string, React.ElementType> = {
    error:   AlertTriangle,
    warning: AlertTriangle,
    info:    Info,
};

const SEVERITY_ICON_CLS: Record<string, string> = {
    error:   "text-red-400",
    warning: "text-amber-400",
    info:    "text-blue-400",
};

const fmtDate = (d: string) =>
    new Date(d).toLocaleString("es-ES", {
        day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit",
    });

export default function AlertasPage() {
    const toast = useToastStore();
    const [alerts, setAlerts] = useState<AlertEntry[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isChecking, setIsChecking] = useState(false);
    const [hours, setHours] = useState(48);

    const load = useCallback(async () => {
        setIsLoading(true);
        try {
            setAlerts(await api.alerts.list(hours));
        } catch {
            toast.error("Error al cargar alertas");
        } finally {
            setIsLoading(false);
        }
    }, [hours]); // eslint-disable-line react-hooks/exhaustive-deps

    useEffect(() => { load(); }, [load]);

    const handleCheck = async () => {
        setIsChecking(true);
        try {
            const res = await api.alerts.check();
            toast.success(res.message);
            await load();
        } catch {
            toast.error("Error al ejecutar comprobación");
        } finally {
            setIsChecking(false);
        }
    };

    const errors   = alerts.filter((a) => a.severity === "error").length;
    const warnings = alerts.filter((a) => a.severity === "warning").length;
    const infos    = alerts.filter((a) => a.severity === "info").length;

    return (
        <PageContainer width="full">
            <PageHeader
                title="Alertas automáticas"
                description="Condiciones de negocio detectadas por el sistema (facturas, stock, nóminas)"
                icon={Bell}
                actions={
                    <div className="flex items-center gap-2">
                        <select
                            value={hours}
                            onChange={(e) => setHours(Number(e.target.value))}
                            className="bg-muted border border-border rounded-lg px-3 py-1.5 text-xs text-foreground focus:outline-none"
                        >
                            <option value={24}>Últimas 24h</option>
                            <option value={48}>Últimas 48h</option>
                            <option value={168}>Última semana</option>
                        </select>
                        <Button size="sm" variant="outline" onClick={load} disabled={isLoading} aria-label="Recargar alertas">
                            <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
                        </Button>
                        <Button size="sm" onClick={handleCheck} disabled={isChecking}>
                            {isChecking
                                ? <><Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />Comprobando…</>
                                : <><Sparkles className="mr-2 h-3.5 w-3.5" />Comprobar ahora</>}
                        </Button>
                    </div>
                }
            />

            {/* KPIs */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <KpiCard title="Total alertas" value={alerts.length} icon={Bell} />
                <KpiCard title="Críticas" value={errors} icon={AlertTriangle} />
                <KpiCard title="Avisos" value={warnings} icon={AlertTriangle} />
                <KpiCard title="Informativas" value={infos} icon={Info} />
            </div>

            {/* Alert list */}
            {isLoading ? (
                <div className="flex items-center justify-center h-48 text-muted-foreground text-sm gap-2">
                    <Loader2 className="w-4 h-4 animate-spin" /> Cargando alertas…
                </div>
            ) : alerts.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-40 gap-2 text-muted-foreground rounded-xl border border-border bg-card">
                    <CheckCircle2 className="w-7 h-7 text-emerald-400 opacity-60" />
                    <p className="text-sm">Sin alertas en el periodo seleccionado</p>
                </div>
            ) : (
                <div className="space-y-2">
                    {alerts.map((alert) => {
                        const meta = TYPE_META[alert.alert_type];
                        const SevIcon = SEVERITY_ICON[alert.severity] ?? Info;
                        const TypeIcon = meta?.icon ?? Bell;
                        return (
                            <div
                                key={alert.id}
                                className={`flex items-start gap-4 rounded-xl border px-4 py-3 ${SEVERITY_CLS[alert.severity] ?? "border-border bg-card"}`}
                            >
                                <SevIcon className={`w-4 h-4 mt-0.5 shrink-0 ${SEVERITY_ICON_CLS[alert.severity]}`} />
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2 flex-wrap">
                                        <span className="text-xs font-medium text-muted-foreground flex items-center gap-1">
                                            <TypeIcon className="w-3 h-3" />
                                            {meta?.label ?? alert.alert_type}
                                        </span>
                                        <span className="text-xs text-muted-foreground/60">{fmtDate(alert.sent_at)}</span>
                                    </div>
                                    <p className="text-sm text-foreground mt-0.5">{alert.entity_label}</p>
                                </div>
                                {meta?.href && (
                                    <a
                                        href={meta.href}
                                        className="text-xs text-primary hover:underline shrink-0 mt-0.5"
                                    >
                                        Ver →
                                    </a>
                                )}
                            </div>
                        );
                    })}
                </div>
            )}

            <p className="text-xs text-muted-foreground">
                Las alertas se comprueban automáticamente cada día a las 08:30. Las mismas alertas no se repiten antes de 24h.
            </p>
        </PageContainer>
    );
}
