"use client";

import React, { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { useFormat } from "@/hooks/useFormat";
import {
    Receipt, Plus, Check, X, Loader2, Download, Upload, Trash2, RefreshCw, Sparkles,
} from "lucide-react";
import { api } from "@/lib/api";
import { useToastStore } from "@/stores/toast";
import type { Expense, Employee } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/shared/PageHeader";
import { KpiCard } from "@/components/shared/KpiCard";
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PageContainer } from "@/components/shared/PageContainer";

// I18N — config estructural + labelKey; el componente traduce en render.
const CATEGORIES = [
    { value: "viaje", labelKey: "gastos.categories.viaje" },
    { value: "dieta", labelKey: "gastos.categories.dieta" },
    { value: "alojamiento", labelKey: "gastos.categories.alojamiento" },
    { value: "material", labelKey: "gastos.categories.material" },
    { value: "formacion", labelKey: "gastos.categories.formacion" },
    { value: "otro", labelKey: "gastos.categories.otro" },
];

const STATUS_TABS = [
    { value: "", labelKey: "gastos.tabs.all" },
    { value: "pending", labelKey: "gastos.tabs.pending" },
    { value: "approved", labelKey: "gastos.tabs.approved" },
    { value: "reimbursed", labelKey: "gastos.tabs.reimbursed" },
    { value: "rejected", labelKey: "gastos.tabs.rejected" },
];

const STATUS_STYLE: Record<string, string> = {
    pending:    "bg-amber-500/10 text-amber-400 border-amber-500/20",
    approved:   "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    rejected:   "bg-red-500/10 text-red-400 border-red-500/20",
    reimbursed: "bg-blue-500/10 text-blue-400 border-blue-500/20",
};
const STATUS_LABEL_KEYS: Record<string, string> = {
    pending: "gastos.status.pending",
    approved: "gastos.status.approved",
    rejected: "gastos.status.rejected",
    reimbursed: "gastos.status.reimbursed",
};

type ExpenseForm = {
    employee_id: string;
    amount: string;
    category: string;
    description: string;
    date: string;
    notes: string;
};

const emptyForm = (): ExpenseForm => ({
    employee_id: "",
    amount: "",
    category: "viaje",
    description: "",
    date: new Date().toISOString().slice(0, 10),
    notes: "",
});

export default function GastosPage() {
    const t = useTranslations("rrhh");
    const tc = useTranslations("common");
    const { fmtCurrency, fmtDate } = useFormat();
    const [expenses, setExpenses] = useState<Expense[]>([]);
    const [employees, setEmployees] = useState<Employee[]>([]);
    const [statusTab, setStatusTab] = useState("");
    const [isLoading, setIsLoading] = useState(true);

    const [showCreate, setShowCreate] = useState(false);
    const [form, setForm] = useState<ExpenseForm>(emptyForm());
    const [saving, setSaving] = useState(false);
    const [formError, setFormError] = useState<string | null>(null);

    const [actionId, setActionId] = useState<string | null>(null);
    const [uploadingId, setUploadingId] = useState<string | null>(null);
    const [scanning, setScanning] = useState(false);
    const [scanConfidence, setScanConfidence] = useState<number | null>(null);
    const [scanMerchant, setScanMerchant] = useState<string | null>(null);
    const toast = useToastStore();

    const fmt = fmtCurrency;
    const formatDate = (d: string) => fmtDate(d, { day: "2-digit", month: "short", year: "numeric" });

    const handleScanTicket = useCallback(async (file: File) => {
        if (!file.type.startsWith("image/")) {
            toast.error(t("gastos.scan.onlyImages"));
            return;
        }
        setScanning(true);
        setScanConfidence(null);
        setScanMerchant(null);
        try {
            const draft = await api.hr.expenses.scanReceipt(file);
            const employeeId = employees.length > 0 ? employees[0].id : "";
            setForm({
                employee_id: employeeId,
                amount: draft.amount.toFixed(2),
                category: draft.category || "otro",
                description: draft.description || t("gastos.scan.ticketDescription", { merchant: draft.merchant }),
                date: draft.date,
                notes: [
                    draft.merchant && t("gastos.scan.merchant", { merchant: draft.merchant }),
                    draft.merchant_nif && t("gastos.scan.nif", { nif: draft.merchant_nif }),
                    draft.vat_amount != null && (draft.vat_rate
                        ? t("gastos.scan.vatWithRate", { amount: draft.vat_amount.toFixed(2), rate: draft.vat_rate })
                        : t("gastos.scan.vat", { amount: draft.vat_amount.toFixed(2) })),
                ].filter(Boolean).join(" · "),
            });
            setScanConfidence(draft.confidence);
            setScanMerchant(draft.merchant);
            setFormError(null);
            setShowCreate(true);
            toast.success(t("gastos.scan.readSuccess", { merchant: draft.merchant, amount: draft.amount.toFixed(2) }));
        } catch (e) {
            const msg = e instanceof Error ? e.message : t("gastos.scan.readError");
            toast.error(msg);
        } finally {
            setScanning(false);
        }
    }, [employees, toast, t]);

    const load = useCallback(async () => {
        setIsLoading(true);
        try {
            const [exp, emp] = await Promise.all([
                api.hr.expenses.list(statusTab || undefined),
                api.hr.employees.list(),
            ]);
            setExpenses(exp);
            setEmployees(emp);
        } catch { /* noop */ }
        finally { setIsLoading(false); }
    }, [statusTab]);

    useEffect(() => { load(); }, [load]);

    const pendingTotal = expenses.filter((e) => e.status === "pending").reduce((s, e) => s + e.amount, 0);
    const pendingCount = expenses.filter((e) => e.status === "pending").length;
    const approvedTotal = expenses.filter((e) => e.status === "approved").reduce((s, e) => s + e.amount, 0);

    const handleCreate = async () => {
        if (!form.employee_id || !form.amount || !form.description || !form.date) {
            setFormError(t("gastos.requiredFieldsError")); return;
        }
        setSaving(true); setFormError(null);
        try {
            await api.hr.expenses.create({
                employee_id: form.employee_id,
                amount: parseFloat(form.amount),
                category: form.category,
                description: form.description,
                date: form.date,
                notes: form.notes || undefined,
            });
            setShowCreate(false);
            setForm(emptyForm());
            await load();
        } catch { setFormError(t("gastos.createError")); }
        finally { setSaving(false); }
    };

    const handleAction = async (id: string, action: "approve" | "reject" | "reimburse" | "delete") => {
        setActionId(id);
        try {
            if (action === "approve") await api.hr.expenses.approve(id);
            else if (action === "reject") await api.hr.expenses.reject(id);
            else if (action === "reimburse") await api.hr.expenses.reimburse(id);
            else await api.hr.expenses.delete(id);
            await load();
        } catch { /* noop */ }
        finally { setActionId(null); }
    };

    const handleUploadReceipt = async (id: string, file: File) => {
        setUploadingId(id);
        try {
            await api.hr.expenses.uploadReceipt(id, file);
            await load();
        } catch { /* noop */ }
        finally { setUploadingId(null); }
    };

    return (
        <PageContainer width="full">
            <PageHeader
                title={t("gastos.title")}
                description={t("gastos.description")}
                icon={Receipt}
                actions={
                    <div className="flex items-center gap-2">
                        <label className={`inline-flex items-center gap-2 rounded-md border border-primary/30 bg-primary/10 text-primary hover:bg-primary/20 px-3 h-9 text-sm font-medium cursor-pointer transition-colors ${scanning ? "opacity-50 pointer-events-none" : ""}`}>
                            {scanning
                                ? <><Loader2 className="h-4 w-4 animate-spin" /> {t("gastos.scanningTicket")}</>
                                : <><Sparkles className="h-4 w-4" /> {t("gastos.scanTicket")}</>}
                            <input
                                type="file"
                                accept="image/png,image/jpeg,image/webp"
                                capture="environment"
                                className="hidden"
                                onChange={(e) => {
                                    const f = e.target.files?.[0];
                                    if (f) handleScanTicket(f);
                                    e.target.value = "";
                                }}
                            />
                        </label>
                        <Button onClick={() => { setShowCreate(true); setFormError(null); setForm(emptyForm()); setScanConfidence(null); setScanMerchant(null); }}>
                            <Plus className="mr-2 h-4 w-4" /> {t("gastos.newExpense")}
                        </Button>
                    </div>
                }
            />

            {/* KPIs */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <KpiCard title={t("gastos.kpi.pendingCount")} value={pendingCount} icon={Receipt} />
                <KpiCard title={t("gastos.kpi.pendingAmount")} value={fmt(pendingTotal)} icon={Receipt} />
                <KpiCard title={t("gastos.kpi.approvedAmount")} value={fmt(approvedTotal)} icon={Receipt} />
            </div>

            {/* Status tabs */}
            <div className="flex gap-1 border-b border-border">
                {STATUS_TABS.map((tab) => (
                    <button
                        key={tab.value}
                        onClick={() => setStatusTab(tab.value)}
                        className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
                            statusTab === tab.value
                                ? "border-primary text-foreground"
                                : "border-transparent text-muted-foreground hover:text-foreground"
                        }`}
                    >
                        {t(tab.labelKey)}
                    </button>
                ))}
            </div>

            {/* Table */}
            {isLoading ? (
                <div className="flex items-center justify-center h-40 text-muted-foreground text-sm gap-2">
                    <Loader2 className="w-4 h-4 animate-spin" /> {tc("loading")}
                </div>
            ) : expenses.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-40 gap-2 text-muted-foreground">
                    <Receipt className="w-8 h-8 opacity-30" />
                    <p className="text-sm">{t("gastos.emptyCategory")}</p>
                </div>
            ) : (
                <div className="rounded-xl border border-border overflow-hidden">
                    <table className="w-full text-sm">
                        <thead className="bg-muted/30 text-muted-foreground">
                            <tr>
                                <th className="text-left px-4 py-3 font-medium">{t("gastos.table.employee")}</th>
                                <th className="text-left px-4 py-3 font-medium">{t("gastos.table.category")}</th>
                                <th className="text-left px-4 py-3 font-medium">{t("gastos.table.description")}</th>
                                <th className="text-left px-4 py-3 font-medium">{t("gastos.table.date")}</th>
                                <th className="text-right px-4 py-3 font-medium">{t("gastos.table.amount")}</th>
                                <th className="text-left px-4 py-3 font-medium">{t("gastos.table.status")}</th>
                                <th className="text-left px-4 py-3 font-medium">{t("gastos.table.receipt")}</th>
                                <th className="text-right px-4 py-3 font-medium">{t("gastos.table.actions")}</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-border">
                            {expenses.map((exp) => (
                                <tr key={exp.id} className="bg-card hover:bg-muted/20 transition-colors">
                                    <td className="px-4 py-3 font-medium text-foreground">{exp.employee_name ?? "—"}</td>
                                    <td className="px-4 py-3 text-muted-foreground capitalize">
                                        {(() => {
                                            const cat = CATEGORIES.find((c) => c.value === exp.category);
                                            return cat ? t(cat.labelKey) : exp.category;
                                        })()}
                                    </td>
                                    <td className="px-4 py-3 text-muted-foreground max-w-[200px] truncate" title={exp.description}>
                                        {exp.description}
                                    </td>
                                    <td className="px-4 py-3 text-muted-foreground">{formatDate(exp.date)}</td>
                                    <td className="px-4 py-3 text-right font-semibold text-foreground tabular-nums">
                                        {fmt(exp.amount)}
                                    </td>
                                    <td className="px-4 py-3">
                                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${STATUS_STYLE[exp.status] ?? ""}`}>
                                            {STATUS_LABEL_KEYS[exp.status] ? t(STATUS_LABEL_KEYS[exp.status]) : exp.status}
                                        </span>
                                    </td>
                                    <td className="px-4 py-3">
                                        {exp.receipt_filename ? (
                                            <button
                                                onClick={() => api.hr.expenses.downloadReceipt(exp.id, exp.receipt_filename!)}
                                                className="flex items-center gap-1 text-xs text-primary hover:underline"
                                                title={exp.receipt_filename}
                                            >
                                                <Download className="w-3 h-3" />
                                                {t("gastos.receiptView")}
                                            </button>
                                        ) : (
                                            <label className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground cursor-pointer">
                                                {uploadingId === exp.id
                                                    ? <Loader2 className="w-3 h-3 animate-spin" />
                                                    : <Upload className="w-3 h-3" />}
                                                <span>{t("gastos.receiptUpload")}</span>
                                                <input
                                                    type="file"
                                                    className="hidden"
                                                    accept=".pdf,.jpg,.jpeg,.png"
                                                    onChange={(e) => {
                                                        const f = e.target.files?.[0];
                                                        if (f) handleUploadReceipt(exp.id, f);
                                                    }}
                                                />
                                            </label>
                                        )}
                                    </td>
                                    <td className="px-4 py-3">
                                        <div className="flex items-center justify-end gap-1">
                                            {exp.status === "pending" && (
                                                <>
                                                    <Button
                                                        variant="ghost" size="icon"
                                                        className="h-7 w-7 text-emerald-500 hover:text-emerald-400"
                                                        title={t("common.approve")}
                                                        disabled={actionId === exp.id}
                                                        onClick={() => handleAction(exp.id, "approve")}
                                                     aria-label={t("common.approve")}>
                                                        {actionId === exp.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" /> : <Check className="h-3.5 w-3.5" aria-hidden="true" />}
                                                    </Button>
                                                    <Button
                                                        variant="ghost" size="icon"
                                                        className="h-7 w-7 text-red-500 hover:text-red-400"
                                                        title={t("gastos.actions.reject")}
                                                        disabled={actionId === exp.id}
                                                        onClick={() => handleAction(exp.id, "reject")}
                                                     aria-label={t("gastos.actions.reject")}>
                                                        <X className="h-3.5 w-3.5" aria-hidden="true" />
                                                    </Button>
                                                </>
                                            )}
                                            {exp.status === "approved" && (
                                                <Button
                                                    variant="ghost" size="icon"
                                                    className="h-7 w-7 text-blue-500 hover:text-blue-400"
                                                    title={t("gastos.actions.reimburse")}
                                                    disabled={actionId === exp.id}
                                                    onClick={() => handleAction(exp.id, "reimburse")}
                                                 aria-label={t("gastos.actions.reimburse")}>
                                                    {actionId === exp.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" /> : <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />}
                                                </Button>
                                            )}
                                            <Button
                                                variant="ghost" size="icon"
                                                className="h-7 w-7 text-destructive hover:text-destructive"
                                                title={tc("delete")}
                                                disabled={actionId === exp.id}
                                                onClick={() => handleAction(exp.id, "delete")}
                                             aria-label={tc("delete")}>
                                                <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                                            </Button>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            {/* Create modal */}
            <Dialog open={showCreate} onOpenChange={setShowCreate}>
                <DialogContent className="max-w-md">
                    <DialogHeader>
                        <DialogTitle>{scanConfidence !== null ? t("gastos.modal.reviewScannedTitle") : t("gastos.newExpense")}</DialogTitle>
                        {scanConfidence !== null && (
                            <div className="flex items-center gap-2 text-xs text-muted-foreground mt-1">
                                <Sparkles className="w-3.5 h-3.5 text-primary" />
                                {scanMerchant ? t("gastos.modal.detected", { merchant: scanMerchant }) : t("gastos.modal.extractedFromTicket")}
                                <span className={`ml-1 font-medium ${scanConfidence >= 0.8 ? "text-emerald-500" : scanConfidence >= 0.5 ? "text-amber-500" : "text-rose-500"}`}>
                                    {t("gastos.modal.confidence", { pct: (scanConfidence * 100).toFixed(0) })}
                                </span>
                                <span className="text-muted-foreground/70">{t("gastos.modal.reviewBeforeSave")}</span>
                            </div>
                        )}
                    </DialogHeader>
                    <div className="space-y-4 py-2">
                        <div className="space-y-1.5">
                            <Label>{t("gastos.modal.employee")}</Label>
                            <Select value={form.employee_id} onValueChange={(v) => setForm((f) => ({ ...f, employee_id: v }))}>
                                <SelectTrigger><SelectValue placeholder={t("gastos.modal.selectEmployee")} /></SelectTrigger>
                                <SelectContent>
                                    {employees.map((e) => (
                                        <SelectItem key={e.id} value={e.id}>{e.name}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <div className="space-y-1.5">
                                <Label>{t("gastos.modal.amount")}</Label>
                                <Input
                                    type="number" step="0.01" min="0"
                                    value={form.amount}
                                    onChange={(e) => setForm((f) => ({ ...f, amount: e.target.value }))}
                                    placeholder="0.00"
                                />
                            </div>
                            <div className="space-y-1.5">
                                <Label>{t("gastos.modal.date")}</Label>
                                <Input
                                    type="date"
                                    value={form.date}
                                    onChange={(e) => setForm((f) => ({ ...f, date: e.target.value }))}
                                />
                            </div>
                        </div>
                        <div className="space-y-1.5">
                            <Label>{t("gastos.modal.category")}</Label>
                            <Select value={form.category} onValueChange={(v) => setForm((f) => ({ ...f, category: v }))}>
                                <SelectTrigger><SelectValue /></SelectTrigger>
                                <SelectContent>
                                    {CATEGORIES.map((c) => (
                                        <SelectItem key={c.value} value={c.value}>{t(c.labelKey)}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="space-y-1.5">
                            <Label>{t("gastos.modal.descriptionLabel")}</Label>
                            <Input
                                value={form.description}
                                onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                                placeholder={t("gastos.modal.descriptionPlaceholder")}
                            />
                        </div>
                        <div className="space-y-1.5">
                            <Label>{t("gastos.modal.notes")}</Label>
                            <textarea
                                value={form.notes}
                                onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setForm((f) => ({ ...f, notes: e.target.value }))}
                                placeholder={t("gastos.modal.notesPlaceholder")}
                                rows={2}
                                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-none"
                            />
                        </div>
                        {formError && <p className="text-xs text-destructive">{formError}</p>}
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setShowCreate(false)} disabled={saving}>{tc("cancel")}</Button>
                        <Button onClick={handleCreate} disabled={saving}>
                            {saving ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" />{t("gastos.modal.saving")}</> : t("gastos.modal.create")}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </PageContainer>
    );
}
