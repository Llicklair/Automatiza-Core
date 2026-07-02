"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { useFormat } from "@/hooks/useFormat";
import { format, startOfMonth, endOfMonth } from "date-fns";
import { api, type Employee, type Payroll, type PayrollCalculation } from "@/lib/api";
import { waitForTask, TaskTimeoutError } from "@/lib/api/tasks";
import { logError } from "@/lib/logger";
import { useNotificationStore } from "@/stores/notifications";

export function usePayrolls() {
    const t = useTranslations("rrhh");
    const { fmtCurrency } = useFormat();
    const [payrolls, setPayrolls]                     = useState<Payroll[]>([]);
    const [isLoading, setIsLoading]                   = useState(true);
    const [generatingPayrolls, setGeneratingPayrolls] = useState(false);
    const [approvingId, setApprovingId]               = useState<string | null>(null);
    const [downloadingId, setDownloadingId]           = useState<string | null>(null);
    const [toast, setToast]                           = useState<{ msg: string; type: "ok" | "err" } | null>(null);
    const [search, setSearch]                         = useState("");
    const [filterMonth, setFilterMonth]               = useState("");
    const [filterEmpId, setFilterEmpId]               = useState("");

    // Auto-payroll modal state
    const [autoOpen, setAutoOpen]                     = useState(false);
    const [autoEmployees, setAutoEmployees]           = useState<Employee[]>([]);
    const [autoEmpLoading, setAutoEmpLoading]         = useState(false);
    const [autoEmpId, setAutoEmpId]                   = useState<string>("");
    const [autoPreview, setAutoPreview]               = useState<PayrollCalculation | null>(null);
    const [autoPreviewLoading, setAutoPreviewLoading] = useState(false);
    const [autoSubmitting, setAutoSubmitting]         = useState(false);

    const refreshKey = useNotificationStore((s) => s.refreshKey);

    const loadData = async () => {
        setIsLoading(true);
        try {
            setPayrolls(await api.hr.payrolls.list());
        } catch (e) { logError("rrhh/nominas/page", e); }
        finally { setIsLoading(false); }
    };

    useEffect(() => { loadData(); }, [refreshKey]);  

    const showToast = (msg: string, type: "ok" | "err") => {
        setToast({ msg, type });
        setTimeout(() => setToast(null), 5000);
    };

    const openAutoModal = () => {
        setAutoOpen(true);
        setAutoPreview(null);
        setAutoEmpId("");
    };

    const loadAutoEmployees = useCallback(async () => {
        setAutoEmpLoading(true);
        try {
            const list = await api.hr.employees.list();
            const active = list.filter((e) => e.status === "active");
            const useList = active.length > 0 ? active : list;
            setAutoEmployees(useList);
            setAutoEmpId(useList[0]?.id ?? "");
        } catch (e) {
            logError("rrhh/nominas/auto-employees", e);
            showToast(t("toasts.employeesLoadError"), "err");
        } finally {
            setAutoEmpLoading(false);
        }
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    useEffect(() => {
        if (!autoOpen) return;
        void loadAutoEmployees();
    }, [autoOpen, loadAutoEmployees]);

    useEffect(() => {
        if (!autoOpen || !autoEmpId) { setAutoPreview(null); return; }
        let cancelled = false;
        setAutoPreviewLoading(true);
        setAutoPreview(null);
        api.hr.payrolls.preview(autoEmpId)
            .then((p) => { if (!cancelled) setAutoPreview(p); })
            .catch((e: unknown) => {
                if (!cancelled) {
                    logError("rrhh/nominas/preview", e);
                    showToast(e instanceof Error ? e.message : t("toasts.previewUnavailable"), "err");
                }
            })
            .finally(() => { if (!cancelled) setAutoPreviewLoading(false); });
        return () => { cancelled = true; };
    }, [autoOpen, autoEmpId]); // eslint-disable-line react-hooks/exhaustive-deps

    const handleAutoCreate = async () => {
        if (!autoEmpId) return;
        const now = new Date();
        setAutoSubmitting(true);
        try {
            await api.hr.payrolls.generateAuto({
                employee_id: autoEmpId,
                period_start: format(startOfMonth(now), "yyyy-MM-dd"),
                period_end:   format(endOfMonth(now),   "yyyy-MM-dd"),
                issue_date:   format(now,                "yyyy-MM-dd"),
                status: "draft",
            });
            showToast(t("toasts.autoDraftCreated"), "ok");
            setAutoOpen(false);
            await loadData();
        } catch (e: unknown) {
            showToast(e instanceof Error ? e.message : t("toasts.autoDraftError"), "err");
        } finally {
            setAutoSubmitting(false);
        }
    };

    const handleGeneratePayrolls = async () => {
        setGeneratingPayrolls(true);
        const now = new Date();
        // La instrucción al agente va SIEMPRE en español (prompt de backend, no UI).
        const promptMonth = now.toLocaleString("es", { month: "long" });
        const year = now.getFullYear();
        try {
            const task = await api.tasks.create(
                "hr",
                `Genera todas las nóminas del mes de ${promptMonth} de ${year} para todos los empleados activos del tenant. Créalas en estado DRAFT para revisión humana.`
            );
            showToast(t("toasts.agentLaunched", { month: promptMonth, year }), "ok");
            const finished = await waitForTask(task.id);
            if (finished.status === "failed") {
                showToast(t("toasts.errorPrefix", { msg: finished.error_message || t("toasts.agentLaunchError") }), "err");
            } else {
                showToast(t("toasts.payrollsGenerated"), "ok");
            }
            await loadData();
        } catch (e: any) {
            if (e instanceof TaskTimeoutError) {
                showToast(t("toasts.payrollsStillRunning"), "ok");
                await loadData();
            } else {
                showToast(t("toasts.errorPrefix", { msg: e.message || t("toasts.agentLaunchError") }), "err");
            }
        } finally {
            setGeneratingPayrolls(false);
        }
    };

    const handleApprove = async (payroll: Payroll) => {
        setApprovingId(payroll.id);
        try {
            const updated = await api.hr.payrolls.approve(payroll.id);
            setPayrolls(prev => prev.map(p => p.id === updated.id ? updated : p));
            showToast(t("toasts.payrollApproved", { name: payroll.employee?.name ?? "" }), "ok");
        } catch (e: any) {
            showToast(t("toasts.approveError", { msg: e.message }), "err");
        } finally {
            setApprovingId(null);
        }
    };

    const handleDownloadPdf = async (payroll: Payroll) => {
        setDownloadingId(payroll.id);
        try {
            const empName = payroll.employee?.name?.replace(/\s+/g, "_") ?? "empleado";
            const period = payroll.period_start ? format(new Date(payroll.period_start), "yyyy-MM") : "periodo";
            await api.hr.payrolls.downloadPdf(payroll.id, `Nomina_${empName}_${period}.pdf`);
        } catch (e: any) {
            showToast(t("toasts.downloadPdfError", { msg: e.message }), "err");
        } finally {
            setDownloadingId(null);
        }
    };

    const kpis = useMemo(() => {
        const now = new Date();
        const currentMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
        const thisMonth = payrolls.filter(p => p.period_start && p.period_start.slice(0, 7) === currentMonth);
        return {
            costeNominas: thisMonth.reduce((s, p) => s + (p.base_salary || 0), 0),
            totalSS:      thisMonth.reduce((s, p) => s + ((p.deductions || 0) - (p.irpf || 0)), 0),
            totalIRPF:    thisMonth.reduce((s, p) => s + (p.irpf || 0), 0),
        };
    }, [payrolls]);

    const uniqueEmployees = useMemo(() => {
        const map = new Map<string, string>();
        payrolls.forEach(p => { if (p.employee_id && p.employee?.name) map.set(p.employee_id, p.employee.name); });
        return Array.from(map.entries()).sort((a, b) => a[1].localeCompare(b[1]));
    }, [payrolls]);

    const filtered = payrolls.filter(p => {
        if (search && !(p.employee?.name ?? "").toLowerCase().includes(search.toLowerCase())) return false;
        if (filterMonth && (!p.period_start || p.period_start.slice(0, 7) !== filterMonth)) return false;
        if (filterEmpId && p.employee_id !== filterEmpId) return false;
        return true;
    });

    const drafts = payrolls.filter(p => p.status === "draft").length;

    const fmt = fmtCurrency;

    return {
        payrolls, filtered, isLoading, drafts, kpis, uniqueEmployees, fmt,
        generatingPayrolls, approvingId, downloadingId, toast, setToast,
        search, setSearch, filterMonth, setFilterMonth, filterEmpId, setFilterEmpId,
        autoOpen, setAutoOpen, autoEmployees, autoEmpLoading,
        autoEmpId, setAutoEmpId, autoPreview, autoPreviewLoading, autoSubmitting,
        openAutoModal, handleAutoCreate, handleGeneratePayrolls, handleApprove, handleDownloadPdf,
    };
}
