"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { api, type CompanySnapshot, type FiscalSnapshot, type ReportDoc } from "@/lib/api";
import { logError } from "@/lib/logger";
import { showConfirm } from "@/stores/confirm";

type Translator = (key: string, values?: Record<string, any>) => string;

// ─── Pure helpers (no React) ──────────────────────────────────────────────────

export function fmt(n: number) {
    return n.toLocaleString("es-ES", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function fmtMonth(t: Translator, m: string) {
    const [y, mo] = m.split("-");
    const months = t("hooks.months").split(",");
    return `${months[parseInt(mo) - 1]} ${y}`;
}

export function prevMonth(m: string) {
    const [y, mo] = m.split("-").map(Number);
    const d = new Date(y, mo - 2, 1);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

export function nextMonth(m: string) {
    const [y, mo] = m.split("-").map(Number);
    const d = new Date(y, mo, 1);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

export function currentMonthStr() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

export function currentQuarterStr() {
    const d = new Date();
    const q = Math.ceil((d.getMonth() + 1) / 3);
    return `${d.getFullYear()}-Q${q}`;
}

export function fmtQuarter(t: Translator, q: string) {
    const [y, qn] = q.split("-Q");
    return t("hooks.quarterLabel", { q: qn, year: y });
}

export function prevQuarter(q: string) {
    const [y, qn] = q.split("-Q").map(Number);
    if (qn === 1) return `${y - 1}-Q4`;
    return `${y}-Q${qn - 1}`;
}

export function nextQuarter(q: string) {
    const [y, qn] = q.split("-Q").map(Number);
    if (qn === 4) return `${y + 1}-Q1`;
    return `${y}-Q${qn + 1}`;
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

export function useInformes() {
    const t = useTranslations("informes");
    const [tab, setTab] = useState<"gestion" | "fiscal">("gestion");

    // ── Gestión state ──
    const [month, setMonth] = useState(currentMonthStr());
    const [snap, setSnap] = useState<CompanySnapshot | null>(null);
    const [loading, setLoading] = useState(false);
    const [generating, setGenerating] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [genOk, setGenOk] = useState(false);

    // ── Fiscal state ──
    const [fiscalMode, setFiscalMode] = useState<"mensual" | "trimestral">("trimestral");
    const [fiscalMonth, setFiscalMonth] = useState(currentMonthStr());
    const [fiscalQuarter, setFiscalQuarter] = useState(currentQuarterStr());
    const [fiscalSnap, setFiscalSnap] = useState<FiscalSnapshot | null>(null);
    const [fiscalLoading, setFiscalLoading] = useState(false);
    const [fiscalGenerating, setFiscalGenerating] = useState(false);
    const [fiscalError, setFiscalError] = useState<string | null>(null);
    const [fiscalGenOk, setFiscalGenOk] = useState(false);

    // ── Shared state ──
    const [reports, setReports] = useState<ReportDoc[]>([]);

    const fiscalPeriod = fiscalMode === "trimestral" ? fiscalQuarter : fiscalMonth;
    const isCurrentOrPast = month <= currentMonthStr();

    // ── Gestión loaders ──
    async function loadSnapshot() {
        setLoading(true);
        setError(null);
        try {
            const data = await api.reports.snapshot(month);
            setSnap(data);
        } catch (e: any) {
            setError(e.message || t("hooks.errorLoadingData"));
        } finally {
            setLoading(false);
        }
    }

    async function loadReports() {
        try {
            const data = await api.reports.list();
            setReports(data);
        } catch (e) {
            logError("informes/list", e);
        }
    }

    async function handleGenerate() {
        setGenerating(true);
        setGenOk(false);
        setError("");
        try {
            await api.reports.generate(month);
            setGenOk(true);
            await loadReports();
        } catch (e: any) {
            const msg = e?.message || t("hooks.errorUnknown");
            setError(t("hooks.errorGenerating", { msg }));
            console.error("[informes] generate error:", e);
        } finally {
            setGenerating(false);
        }
    }

    // ── Fiscal loaders ──
    async function loadFiscalSnapshot() {
        setFiscalLoading(true);
        setFiscalError(null);
        try {
            const data = await api.reports.fiscalSnapshot(fiscalPeriod);
            setFiscalSnap(data);
        } catch (e: any) {
            setFiscalError(e.message || t("hooks.errorLoadingFiscalData"));
        } finally {
            setFiscalLoading(false);
        }
    }

    async function handleGenerateFiscal() {
        setFiscalGenerating(true);
        setFiscalGenOk(false);
        setFiscalError("");
        try {
            await api.reports.generateFiscal(fiscalPeriod);
            setFiscalGenOk(true);
            await loadReports();
        } catch (e: any) {
            const msg = e?.message || t("hooks.errorUnknown");
            setFiscalError(t("hooks.errorGeneratingFiscal", { msg }));
            console.error("[informes] fiscal generate error:", e);
        } finally {
            setFiscalGenerating(false);
        }
    }

    // ── Download / Delete ──
    async function handleDownload(id: string, fileName: string) {
        setError("");
        setFiscalError("");
        try {
            await api.reports.download(id, fileName);
        } catch (e: any) {
            const msg = e?.message || t("hooks.errorUnknown");
            const setErr = tab === "fiscal" ? setFiscalError : setError;
            setErr(t("hooks.errorDownloading", { msg }));
        }
    }

    async function handleDeleteReport(id: string) {
        if (!(await showConfirm({
            message: t("hooks.confirmDelete"),
            confirmLabel: t("hooks.confirmLabel"),
            confirmVariant: "danger",
        }))) return;
        try {
            await api.reports.delete(id);
            setReports(prev => prev.filter(r => r.id !== id));
        } catch (e: any) {
            const setErr = tab === "fiscal" ? setFiscalError : setError;
            setErr(t("hooks.errorDeleting", { msg: e?.message || t("hooks.errorUnknown") }));
        }
    }

    // ── Effects ──
    // eslint-disable-next-line react-hooks/exhaustive-deps
    useEffect(() => { if (tab === "gestion") loadSnapshot(); }, [month, tab]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
    useEffect(() => { if (tab === "fiscal") loadFiscalSnapshot(); }, [fiscalPeriod, tab]);
    useEffect(() => { loadReports(); }, []);

    return {
        // tab
        tab, setTab,
        // gestión
        month, setMonth,
        snap, loading, generating, error, genOk,
        isCurrentOrPast,
        loadSnapshot, handleGenerate,
        // fiscal
        fiscalMode, setFiscalMode,
        fiscalMonth, setFiscalMonth,
        fiscalQuarter, setFiscalQuarter,
        fiscalSnap, fiscalLoading, fiscalGenerating, fiscalError, fiscalGenOk,
        fiscalPeriod,
        loadFiscalSnapshot, handleGenerateFiscal,
        // shared
        reports, handleDownload, handleDeleteReport,
    };
}
