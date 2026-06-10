"use client";

import { useEffect, useState } from "react";
import { api, type CompanySnapshot, type FiscalSnapshot, type ReportDoc } from "@/lib/api";
import { logError } from "@/lib/logger";

// ─── Pure helpers (no React) ──────────────────────────────────────────────────

export function fmt(n: number) {
    return n.toLocaleString("es-ES", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function fmtMonth(m: string) {
    const [y, mo] = m.split("-");
    const months = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"];
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

export function fmtQuarter(q: string) {
    const [y, qn] = q.split("-Q");
    return `T${qn} ${y}`;
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
            setError(e.message || "Error cargando datos");
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
            const msg = e?.message || "Error desconocido";
            setError(`Error generando informe: ${msg}`);
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
            setFiscalError(e.message || "Error cargando datos fiscales");
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
            const msg = e?.message || "Error desconocido";
            setFiscalError(`Error generando informe fiscal: ${msg}`);
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
            const msg = e?.message || "Error desconocido";
            const setErr = tab === "fiscal" ? setFiscalError : setError;
            setErr(`Error descargando: ${msg}`);
        }
    }

    async function handleDeleteReport(id: string) {
        if (!confirm("¿Eliminar este informe? Esta acción no se puede deshacer.")) return;
        try {
            await api.reports.delete(id);
            setReports(prev => prev.filter(r => r.id !== id));
        } catch (e: any) {
            const setErr = tab === "fiscal" ? setFiscalError : setError;
            setErr(`Error eliminando: ${e?.message || "Error desconocido"}`);
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
