"use client";

import { useEffect, useState } from "react";
import { api, type Task, type Approval, type Invoice, type GmailMessage, type DriveFile, type OutlookMessage, type OneDriveFile, type Employee, type AttendanceRecord } from "@/lib/api";
import { useNotificationStore } from "@/stores/notifications";

function decodeJwtName(token: string): string {
    try {
        const payload = JSON.parse(atob(token.split(".")[1]));
        return payload.full_name || payload.name || payload.sub?.split("@")[0] || "";
    } catch { return ""; }
}

export interface DashboardIntegrationsState {
    gmailConnected: boolean;
    gdriveConnected: boolean;
    outlookConnected: boolean;
    onedriveConnected: boolean;
    gmailMessages: GmailMessage[];
    driveFiles: DriveFile[];
    outlookMessages: OutlookMessage[];
    onedriveFiles: OneDriveFile[];
    activeTab: "gmail" | "outlook" | "drive" | "onedrive";
    setActiveTab: (tab: "gmail" | "outlook" | "drive" | "onedrive") => void;
}

export interface DashboardData {
    tasks: Task[];
    approvals: Approval[];
    invoices: Invoice[];
    summary: { ingresos: number; gastos: number; neto: number; margen: number };
    analytics: { cashflow: any[]; insights: any[] };
    loading: boolean;
    userName: string;
    integrations: DashboardIntegrationsState;
    employees: Employee[];
    workingNow: AttendanceRecord[];
}

export function useDashboard(): DashboardData {
    const [tasks, setTasks] = useState<Task[]>([]);
    const [approvals, setApprovals] = useState<Approval[]>([]);
    const [invoices, setInvoices] = useState<Invoice[]>([]);
    const [summary, setSummary] = useState({ ingresos: 0, gastos: 0, neto: 0, margen: 0 });
    const [analytics, setAnalytics] = useState<{ cashflow: any[]; insights: any[] }>({ cashflow: [], insights: [] });
    const [employees, setEmployees] = useState<Employee[]>([]);
    const [workingNow, setWorkingNow] = useState<AttendanceRecord[]>([]);
    const [loading, setLoading] = useState(true);
    const [userName, setUserName] = useState("");
    const [gmailConnected, setGmailConnected] = useState(false);
    const [gdriveConnected, setGdriveConnected] = useState(false);
    const [outlookConnected, setOutlookConnected] = useState(false);
    const [onedriveConnected, setOnedriveConnected] = useState(false);
    const [gmailMessages, setGmailMessages] = useState<GmailMessage[]>([]);
    const [driveFiles, setDriveFiles] = useState<DriveFile[]>([]);
    const [outlookMessages, setOutlookMessages] = useState<OutlookMessage[]>([]);
    const [onedriveFiles, setOnedriveFiles] = useState<OneDriveFile[]>([]);
    const [activeTab, setActiveTab] = useState<"gmail" | "outlook" | "drive" | "onedrive">("gmail");
    const refreshKey = useNotificationStore((s) => s.refreshKey);

    useEffect(() => {
        const token = localStorage.getItem("access_token");
        if (token) setUserName(decodeJwtName(token));
    }, []);

    useEffect(() => {
        Promise.all([
            api.banking.summary().catch(() => ({ ingresos: 0, gastos: 0, neto: 0, margen: 0, is_demo: true })),
            api.erp.invoices.list({ limit: 5 }).catch(() => []),
            api.tasks.list({ limit: 6 }).catch(() => []),
            api.approvals.list().catch(() => []),
            api.banking.analytics().catch(() => ({ cashflow: [], insights: [] })),
            api.integrations.gmailStatus().catch(() => ({ connected: false })),
            api.integrations.gdriveStatus().catch(() => ({ connected: false })),
            api.integrations.outlookStatus().catch(() => ({ connected: false })),
            api.integrations.onedriveStatus().catch(() => ({ connected: false })),
            api.hr.employees.list().catch(() => []),
            api.hr.attendance.now().catch(() => []),
        ])
            .then(([sum, inv, t, a, an, gs, ds, os, ods, emps, working]) => {
                setSummary(sum);
                setInvoices(inv);
                setTasks(t);
                setApprovals(a);
                setAnalytics(an);
                setEmployees(emps);
                setWorkingNow(working);
                setGmailConnected(gs.connected);
                setGdriveConnected(ds.connected);
                setOutlookConnected(os.connected);
                setOnedriveConnected(ods.connected);
                // Auto-select first connected tab
                if (gs.connected) setActiveTab("gmail");
                else if (os.connected) setActiveTab("outlook");
                else if (ds.connected) setActiveTab("drive");
                else if (ods.connected) setActiveTab("onedrive");
                // Load recent data only if connected
                if (gs.connected) api.integrations.gmailRecent().then(setGmailMessages).catch(() => {});
                if (ds.connected) api.integrations.gdriveRecent().then(setDriveFiles).catch(() => {});
                if (os.connected) api.integrations.outlookRecent().then(setOutlookMessages).catch(() => {});
                if (ods.connected) api.integrations.onedriveRecent().then(setOnedriveFiles).catch(() => {});
            })
            .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [refreshKey]);

    return {
        tasks,
        approvals,
        invoices,
        summary,
        analytics,
        loading,
        userName,
        employees,
        workingNow,
        integrations: {
            gmailConnected,
            gdriveConnected,
            outlookConnected,
            onedriveConnected,
            gmailMessages,
            driveFiles,
            outlookMessages,
            onedriveFiles,
            activeTab,
            setActiveTab,
        },
    };
}
